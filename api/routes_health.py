"""
Health Report API Routes
POST /report/generate  — Trigger weekly health report
GET  /report/latest    — Get latest health report
GET  /report/history   — Past reports
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional

import os

from db.database import get_db
from db.models import HealthReport

router = APIRouter()

DEMO_MERCHANT_ID = "11111111-1111-1111-1111-111111111111"
_MERCHANT_PHONE  = os.getenv("DEMO_MERCHANT_PHONE", "917291944074")


class ReportRequest(BaseModel):
    merchant_id:    str = DEMO_MERCHANT_ID
    merchant_phone: str = _MERCHANT_PHONE
    merchant_name:  str = "Ramesh"
    merchant_city:  str = "Delhi"


@router.post("/generate")
async def generate_report(req: ReportRequest):
    """
    Scenario 3: Manually trigger the weekly health report.
    In production this is called by N8N every Sunday at 7 PM.
    """
    from agents.weekly_report import run_weekly_report

    result = await run_weekly_report(
        merchant_id=req.merchant_id,
        merchant_phone=req.merchant_phone,
        merchant_name=req.merchant_name,
        merchant_city=req.merchant_city,
    )

    return {
        "status":         "completed",
        "health_score":   result.get("health_score"),
        "revenue_trend":  result.get("revenue_trend"),
        "week_revenue":   result.get("week_revenue"),
        "khata_recovered":result.get("khata_recovered"),
        "recommendation": result.get("recommendation"),
        "market_pulse":   result.get("market_pulse", []),
        "score_breakdown":result.get("score_breakdown", {}),
        "report_preview": result.get("report_text", "")[:500],
        "pdf_url":        result.get("pdf_url"),
        "trace":          result.get("trace_log", []),
    }


@router.get("/latest")
async def get_latest_report(
    merchant_id: str = DEMO_MERCHANT_ID,
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(HealthReport)
        .where(HealthReport.merchant_id == merchant_id)
        .order_by(desc(HealthReport.created_at))
        .limit(1)
    )
    report = r.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="No reports found. Run /report/generate first.")

    return {
        "id":               str(report.id),
        "health_score":     report.health_score,
        "week_revenue":     report.total_revenue,
        "revenue_trend":    report.revenue_trend,
        "khata_recovered":  report.khata_recovered,
        "top_products":     report.top_products,
        "anomalies_count":  report.anomalies_count,
        "recommendation":   report.ai_recommendation,
        "pdf_url":          report.pdf_url,
        "week_start":       report.week_start.isoformat() if report.week_start else None,
        "week_end":         report.week_end.isoformat() if report.week_end else None,
        "created_at":       report.created_at.isoformat(),
    }


@router.get("/history")
async def get_report_history(
    merchant_id: str = DEMO_MERCHANT_ID,
    limit: int = 8,
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(HealthReport)
        .where(HealthReport.merchant_id == merchant_id)
        .order_by(desc(HealthReport.created_at))
        .limit(limit)
    )
    reports = r.scalars().all()

    return {
        "reports": [
            {
                "id":           str(rp.id),
                "health_score": rp.health_score,
                "week_revenue": rp.total_revenue,
                "revenue_trend":rp.revenue_trend,
                "week_start":   rp.week_start.isoformat() if rp.week_start else None,
                "created_at":   rp.created_at.isoformat(),
            }
            for rp in reports
        ],
        "count": len(reports),
    }
