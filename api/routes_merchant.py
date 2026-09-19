"""
Merchant API Routes
GET  /merchant/dashboard     — Dashboard stats for UI
GET  /merchant/transactions  — Recent transactions
GET  /merchant/anomalies     — Active anomalies
GET  /merchant/khata         — Khata entries
POST /merchant/khata/remind  — Send reminder manually
GET  /merchant/inventory     — Inventory with expiry status
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

from db.database import get_db
from db.models import (
    Merchant, Transaction, KhataEntry, Customer,
    InventoryItem, Anomaly, Campaign
)
from core.whatsapp_client import whatsapp_client

router = APIRouter()

DEMO_MERCHANT_ID = "11111111-1111-1111-1111-111111111111"


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def get_dashboard(
    merchant_id: str = DEMO_MERCHANT_ID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns everything the UI needs for the main dashboard in one call.
    Includes: revenue stats, category breakdown, anomalies, recent activity.
    """
    now         = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start  = now - timedelta(days=7)
    yesterday   = today_start - timedelta(days=1)

    # Today's revenue
    r = await db.execute(
        select(func.sum(Transaction.amount), func.count(Transaction.id))
        .where(
            Transaction.merchant_id == merchant_id,
            Transaction.txn_time >= today_start,
        )
    )
    today_rev, today_count = r.one()
    today_rev   = float(today_rev or 0)
    today_count = int(today_count or 0)

    # Yesterday's revenue (for delta)
    r = await db.execute(
        select(func.sum(Transaction.amount))
        .where(
            Transaction.merchant_id == merchant_id,
            Transaction.txn_time >= yesterday,
            Transaction.txn_time < today_start,
        )
    )
    yest_rev = float(r.scalar() or 0)

    # AOV today
    aov = round(today_rev / today_count, 2) if today_count > 0 else 0

    # Category breakdown today
    r = await db.execute(
        select(Transaction.category, func.sum(Transaction.amount).label("revenue"))
        .where(
            Transaction.merchant_id == merchant_id,
            Transaction.txn_time >= today_start,
        )
        .group_by(Transaction.category)
        .order_by(desc("revenue"))
    )
    categories = [
        {"category": row.category, "revenue": float(row.revenue)}
        for row in r.fetchall()
    ]

    # Weekly revenue (last 7 days by day)
    day_func = func.date(Transaction.txn_time) if db.bind and db.bind.dialect.name == "sqlite" else func.date_trunc("day", Transaction.txn_time)
    r = await db.execute(
        select(
            day_func.label("day"),
            func.sum(Transaction.amount).label("revenue"),
        )
        .where(
            Transaction.merchant_id == merchant_id,
            Transaction.txn_time >= week_start,
        )
        .group_by("day")
        .order_by("day")
    )
    weekly = [
        {"date": str(row.day)[:10], "revenue": float(row.revenue)}
        for row in r.fetchall()
    ]

    # Active anomalies
    r = await db.execute(
        select(Anomaly)
        .where(
            Anomaly.merchant_id == merchant_id,
            Anomaly.status == "open",
        )
        .order_by(desc(Anomaly.detected_at))
        .limit(5)
    )
    anomalies = [
        {
            "id":            str(a.id),
            "category":      a.category,
            "severity":      a.severity,
            "deviation_pct": a.deviation_pct,
            "expected_rev":  a.expected_rev,
            "actual_rev":    a.actual_rev,
            "description":   a.description,
            "detected_at":   a.detected_at.isoformat(),
        }
        for a in r.scalars().all()
    ]

    # Pending khata total
    r = await db.execute(
        select(func.count(KhataEntry.id), func.sum(KhataEntry.amount))
        .where(
            KhataEntry.merchant_id == merchant_id,
            KhataEntry.status == "pending",
        )
    )
    khata_count, khata_total = r.one()

    # Recent campaigns
    r = await db.execute(
        select(Campaign)
        .where(Campaign.merchant_id == merchant_id)
        .order_by(desc(Campaign.created_at))
        .limit(3)
    )
    campaigns = [
        {
            "id":       str(c.id),
            "goal":     c.goal,
            "status":   c.status,
            "category": c.category,
            "created":  c.created_at.isoformat(),
        }
        for c in r.scalars().all()
    ]

    # Revenue delta %
    rev_delta = round(((today_rev - yest_rev) / yest_rev * 100), 1) if yest_rev > 0 else 0

    return {
        "merchant_id":    merchant_id,
        "timestamp":      now.isoformat(),
        "revenue": {
            "today":          today_rev,
            "yesterday":      yest_rev,
            "delta_pct":      rev_delta,
            "transactions":   today_count,
            "aov":            aov,
        },
        "categories":     categories,
        "weekly_revenue": weekly,
        "anomalies":      anomalies,
        "khata": {
            "pending_count": int(khata_count or 0),
            "pending_total": float(khata_total or 0),
        },
        "recent_campaigns": campaigns,
    }


# ── TRANSACTIONS ──────────────────────────────────────────────────────────────

@router.get("/transactions")
async def get_transactions(
    merchant_id: str = DEMO_MERCHANT_ID,
    limit: int = Query(50, le=200),
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Transaction)
        .where(Transaction.merchant_id == merchant_id)
        .order_by(desc(Transaction.txn_time))
        .limit(limit)
    )
    if category:
        query = query.where(Transaction.category == category)

    r = await db.execute(query)
    txns = r.scalars().all()

    return {
        "transactions": [
            {
                "id":       str(t.id),
                "txn_id":   t.txn_id,
                "amount":   t.amount,
                "category": t.category,
                "mode":     t.payment_mode,
                "time":     t.txn_time.isoformat(),
            }
            for t in txns
        ],
        "count": len(txns),
    }


# ── ANOMALIES ─────────────────────────────────────────────────────────────────

@router.get("/anomalies")
async def get_anomalies(
    merchant_id: str = DEMO_MERCHANT_ID,
    status: str = "open",
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(Anomaly)
        .where(
            Anomaly.merchant_id == merchant_id,
            Anomaly.status == status,
        )
        .order_by(desc(Anomaly.detected_at))
    )
    anomalies = r.scalars().all()

    return {
        "anomalies": [
            {
                "id":            str(a.id),
                "category":      a.category,
                "severity":      a.severity,
                "deviation_pct": a.deviation_pct,
                "expected_rev":  a.expected_rev,
                "actual_rev":    a.actual_rev,
                "gap":           round((a.expected_rev or 0) - (a.actual_rev or 0), 2),
                "description":   a.description,
                "alert_sent":    a.alert_sent,
                "detected_at":   a.detected_at.isoformat(),
            }
            for a in anomalies
        ],
        "count": len(anomalies),
    }


@router.post("/anomalies/{anomaly_id}/resolve")
async def resolve_anomaly(
    anomaly_id: str,
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
    anomaly = r.scalar_one_or_none()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    anomaly.status      = "resolved"
    anomaly.resolved_at = datetime.utcnow()
    await db.commit()

    return {"status": "resolved", "anomaly_id": anomaly_id}


# ── KHATA ─────────────────────────────────────────────────────────────────────

@router.get("/khata")
async def get_khata(
    merchant_id: str = DEMO_MERCHANT_ID,
    status: str = "pending",
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(KhataEntry, Customer)
        .join(Customer, KhataEntry.customer_id == Customer.id)
        .where(
            KhataEntry.merchant_id == merchant_id,
            KhataEntry.status == status,
        )
        .order_by(desc(KhataEntry.amount))
    )
    rows = r.fetchall()

    entries = []
    for row in rows:
        k, c = row.KhataEntry, row.Customer
        days_overdue = (datetime.utcnow() - k.created_at).days
        entries.append({
            "id":             str(k.id),
            "customer_name":  c.name,
            "customer_phone": c.phone,
            "customer_warmth":c.warmth_score,
            "amount":         k.amount,
            "description":    k.description,
            "days_overdue":   days_overdue,
            "reminder_count": k.reminder_count,
            "status":         k.status,
            "created_at":     k.created_at.isoformat(),
        })

    total = sum(e["amount"] for e in entries)

    return {
        "entries":       entries,
        "count":         len(entries),
        "total_pending": total,
    }


class KhataRemindRequest(BaseModel):
    khata_id:    str
    merchant_id: str = DEMO_MERCHANT_ID


@router.post("/khata/remind")
async def send_khata_reminder(
    req: KhataRemindRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a polite WhatsApp reminder for a khata entry"""
    r = await db.execute(
        select(KhataEntry, Customer)
        .join(Customer, KhataEntry.customer_id == Customer.id)
        .where(KhataEntry.id == req.khata_id)
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Khata entry not found")

    khata, customer = row.KhataEntry, row.Customer

    # Pick tone based on warmth score
    warmth = customer.warmth_score or 0.5
    tone   = "warm" if warmth > 0.7 else "formal" if warmth < 0.4 else "neutral"

    result = await whatsapp_client.send_khata_reminder(
        to=customer.phone,
        customer_name=customer.name,
        amount=khata.amount,
        invoice_ref=khata.description or f"Invoice #{str(khata.id)[:8]}",
        merchant_upi="sharma.store@paytm",
        tone=tone,
    )

    if result.get("success"):
        khata.reminder_count    += 1
        khata.last_reminder_at  = datetime.utcnow()
        await db.commit()

    return {
        "status":   "sent" if result.get("success") else "failed",
        "to":       customer.phone,
        "customer": customer.name,
        "amount":   khata.amount,
        "tone":     tone,
    }


@router.post("/khata/{khata_id}/mark-paid")
async def mark_khata_paid(
    khata_id: str,
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(KhataEntry).where(KhataEntry.id == khata_id))
    khata = r.scalar_one_or_none()
    if not khata:
        raise HTTPException(status_code=404, detail="Not found")

    khata.status  = "paid"
    khata.paid_at = datetime.utcnow()
    await db.commit()

    return {"status": "marked_paid", "khata_id": khata_id, "amount": khata.amount}


# ── INVENTORY ─────────────────────────────────────────────────────────────────

@router.get("/inventory")
async def get_inventory(
    merchant_id: str = DEMO_MERCHANT_ID,
    filter: Optional[str] = Query(None, description="all | expiring | slow"),
    db: AsyncSession = Depends(get_db),
):
    now    = datetime.utcnow()
    query  = select(InventoryItem).where(InventoryItem.merchant_id == merchant_id)

    if filter == "expiring":
        cutoff = now + timedelta(days=7)
        query  = query.where(InventoryItem.expiry_date <= cutoff)
    elif filter == "slow":
        query  = query.where(InventoryItem.quantity > 20)

    query = query.order_by(InventoryItem.expiry_date.asc().nullslast())
    r     = await db.execute(query)
    items = r.scalars().all()

    def expiry_status(item):
        if not item.expiry_date:
            return "unknown"
        days = (item.expiry_date - now).days
        if days <= 3:  return "critical"
        if days <= 7:  return "warning"
        return "ok"

    return {
        "items": [
            {
                "id":            str(i.id),
                "sku_id":        i.sku_id,
                "name":          i.name,
                "category":      i.category,
                "quantity":      i.quantity,
                "selling_price": i.selling_price,
                "unit_cost":     i.unit_cost,
                "margin_pct":    i.margin_pct,
                "expiry_date":   i.expiry_date.isoformat() if i.expiry_date else None,
                "days_to_expiry":(i.expiry_date - now).days if i.expiry_date else None,
                "expiry_status": expiry_status(i),
            }
            for i in items
        ],
        "count":              len(items),
        "critical_count":     sum(1 for i in items if expiry_status(i) == "critical"),
        "total_stock_value":  sum((i.selling_price or 0) * i.quantity for i in items),
    }
