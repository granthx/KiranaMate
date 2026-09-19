"""
Statistical Anomaly Detector
Compares current sales against 4-week rolling baseline from the DB.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Transaction, SalesBaseline, Anomaly


SEVERITY_THRESHOLDS = {
    "CRITICAL": 30,   # >30% drop → immediate WhatsApp alert
    "WARNING":  15,   # 15-30% drop → scheduled alert
    "INFO":      5,   # 5-15% drop → log only
}


async def get_todays_revenue_by_category(
    db: AsyncSession,
    merchant_id: str,
) -> dict[str, float]:
    """Aggregate today's revenue per category from the transactions table"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
        )
        .where(
            Transaction.merchant_id == merchant_id,
            Transaction.txn_time >= today_start,
        )
        .group_by(Transaction.category)
    )
    return {row.category: float(row.total) for row in result.fetchall()}


async def get_baseline_for_today(
    db: AsyncSession,
    merchant_id: str,
    category: str,
) -> Optional[dict]:
    """Fetch the 4-week rolling baseline for this category on today's day-of-week"""
    dow = datetime.utcnow().weekday()

    result = await db.execute(
        select(SalesBaseline).where(
            SalesBaseline.merchant_id == merchant_id,
            SalesBaseline.category == category,
            SalesBaseline.day_of_week == dow,
        )
    )
    baselines = result.scalars().all()

    if not baselines:
        return None

    total_avg = sum(b.avg_revenue for b in baselines)
    total_std = sum(b.stddev for b in baselines) / len(baselines)

    return {
        "category": category,
        "day_of_week": dow,
        "expected_revenue": round(total_avg, 2),
        "stddev": round(total_std, 2),
    }


async def detect_anomalies(
    db: AsyncSession,
    merchant_id: str,
) -> list[dict]:
    """
    Core anomaly detection loop.
    Runs hourly via N8N cron.

    Returns a list of detected anomalies sorted by severity.
    """
    actual_by_cat = await get_todays_revenue_by_category(db, merchant_id)
    anomalies = []

    categories = list(actual_by_cat.keys()) or ["dairy", "snacks", "staples", "beverages", "personal_care"]

    for category in categories:
        baseline = await get_baseline_for_today(db, merchant_id, category)
        if not baseline:
            continue

        actual    = actual_by_cat.get(category, 0.0)
        expected  = baseline["expected_revenue"]

        if expected == 0:
            continue

        deviation_pct = ((actual - expected) / expected) * 100

        # Only flag drops (not spikes, which are handled separately)
        if deviation_pct >= -SEVERITY_THRESHOLDS["INFO"]:
            continue

        # Determine severity
        abs_dev = abs(deviation_pct)
        if abs_dev >= SEVERITY_THRESHOLDS["CRITICAL"]:
            severity = "CRITICAL"
        elif abs_dev >= SEVERITY_THRESHOLDS["WARNING"]:
            severity = "WARNING"
        else:
            severity = "INFO"

        anomaly = {
            "merchant_id": str(merchant_id),
            "category": category,
            "severity": severity,
            "deviation_pct": round(deviation_pct, 2),
            "expected_revenue": expected,
            "actual_revenue": actual,
            "gap": round(expected - actual, 2),
            "description": (
                f"{category.title()} sales are {abs_dev:.1f}% below "
                f"the 4-week {_day_name()} average "
                f"(expected ₹{expected:,.0f}, actual ₹{actual:,.0f})."
            ),
            "detected_at": datetime.utcnow().isoformat(),
        }
        anomalies.append(anomaly)

        # Persist to DB
        db_anomaly = Anomaly(
            merchant_id=merchant_id,
            category=category,
            severity=severity,
            deviation_pct=round(deviation_pct, 2),
            expected_rev=expected,
            actual_rev=actual,
            description=anomaly["description"],
            status="open",
            alert_sent=False,
        )
        db.add(db_anomaly)

    await db.commit()

    # Sort: CRITICAL first
    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    anomalies.sort(key=lambda a: severity_order.get(a["severity"], 3))

    return anomalies


def _day_name() -> str:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days[datetime.utcnow().weekday()]


def is_first_occurrence(anomaly_history: list) -> bool:
    """
    Used by Cognee context query.
    If a category drop has happened 3+ of last 5 same-day occurrences,
    it's a pattern, not an emergency → reduce severity.
    """
    return len(anomaly_history) == 0
