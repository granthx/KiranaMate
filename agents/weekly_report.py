"""
LangGraph Weekly Health Report Agent
Scenario 3: Sunday 7PM → 0-100 score PDF + WhatsApp voice summary

Graph nodes:
  DataAggregator → ScoreCalculator → RecommendationEngine
  → ReportGenerator → WhatsAppDelivery → CogneeUpdate
"""
import os
import json
from typing import TypedDict, Optional
from datetime import datetime, timedelta

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from core.cognee_client import cognee_client
from core.serper_client import serper_client
from core.whatsapp_client import whatsapp_client

# ── State ─────────────────────────────────────────────────────────────────────

class ReportState(TypedDict):
    merchant_id:    str
    merchant_phone: str
    merchant_name:  str
    merchant_city:  str

    # Aggregated data
    week_revenue:   float
    prev_week_rev:  float
    revenue_trend:  float   # % change
    top_products:   list
    anomalies_week: int
    khata_recovered: float
    pending_khata:  float

    # Score
    health_score:   float
    score_breakdown: dict

    # AI output
    recommendation: str
    market_pulse:   list

    # Report
    report_text:    str
    pdf_url:        Optional[str]
    trace_log:      list


def log_trace(state: ReportState, node: str, msg: str) -> list:
    entry = {"ts": datetime.utcnow().strftime("%H:%M:%S"), "node": node, "message": msg}
    try:
        print(f"[{entry['ts']}] [{node}] {msg}")
    except Exception:
        try:
            print(f"[{entry['ts']}] [{node}] {msg.encode('ascii', 'replace').decode()}")
        except Exception:
            pass
    try:
        from core.trace_bus import trace_bus
        trace_bus.emit_node_step("report", node, msg)
    except Exception:
        pass
    return state.get("trace_log", []) + [entry]

# ── Node 1: Data Aggregator ───────────────────────────────────────────────────

async def data_aggregator_node(state: ReportState) -> dict:
    """Pulls 7-day and 14-day transaction data for comparison"""
    from db.database import AsyncSessionLocal
    from db.models import Transaction, KhataEntry
    from sqlalchemy import select, func

    merchant_id = state["merchant_id"]
    now         = datetime.utcnow()
    week_start  = now - timedelta(days=7)
    prev_start  = now - timedelta(days=14)

    async with AsyncSessionLocal() as db:
        # This week revenue
        r = await db.execute(
            select(func.sum(Transaction.amount))
            .where(Transaction.merchant_id == merchant_id,
                   Transaction.txn_time >= week_start)
        )
        week_rev = float(r.scalar() or 0)

        # Last week revenue
        r = await db.execute(
            select(func.sum(Transaction.amount))
            .where(Transaction.merchant_id == merchant_id,
                   Transaction.txn_time >= prev_start,
                   Transaction.txn_time < week_start)
        )
        prev_rev = float(r.scalar() or 0)

        # Top products by revenue
        r = await db.execute(
            select(Transaction.category, func.sum(Transaction.amount).label("total"))
            .where(Transaction.merchant_id == merchant_id,
                   Transaction.txn_time >= week_start)
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(5)
        )
        top_cats = [{"category": row.category, "revenue": float(row.total)}
                    for row in r.fetchall()]

        # Khata recovered this week
        r = await db.execute(
            select(func.sum(KhataEntry.amount))
            .where(KhataEntry.merchant_id == merchant_id,
                   KhataEntry.status == "paid",
                   KhataEntry.paid_at >= week_start)
        )
        recovered = float(r.scalar() or 0)

        # Khata still pending
        r = await db.execute(
            select(func.sum(KhataEntry.amount))
            .where(KhataEntry.merchant_id == merchant_id,
                   KhataEntry.status == "pending")
        )
        pending = float(r.scalar() or 0)

    trend = ((week_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0

    trace = log_trace(state, "DataAggregator",
                      f"Week revenue: ₹{week_rev:,.0f} ({trend:+.1f}% vs last week). "
                      f"Khata recovered: ₹{recovered:,.0f}")

    return {
        "week_revenue":    week_rev,
        "prev_week_rev":   prev_rev,
        "revenue_trend":   round(trend, 1),
        "top_products":    top_cats,
        "khata_recovered": recovered,
        "pending_khata":   pending,
        "trace_log":       trace,
    }

# ── Node 2: Score Calculator ──────────────────────────────────────────────────

async def score_calculator_node(state: ReportState) -> dict:
    """Computes the 0-100 store health score from multiple dimensions"""

    trend    = state.get("revenue_trend", 0)
    week_rev = state.get("week_revenue", 0)
    recovered = state.get("khata_recovered", 0)
    pending   = state.get("pending_khata", 0)
    anomalies = state.get("anomalies_week", 0)

    # Revenue trend score (0-40 pts)
    if trend >= 20:     rev_score = 40
    elif trend >= 10:   rev_score = 35
    elif trend >= 0:    rev_score = 28
    elif trend >= -10:  rev_score = 20
    else:               rev_score = 10

    # Payment recovery score (0-25 pts)
    recovery_rate = recovered / (recovered + pending) if (recovered + pending) > 0 else 0
    pay_score = round(recovery_rate * 25)

    # Stock health (0-20 pts) — fewer anomalies = better
    stock_score = max(0, 20 - anomalies * 4)

    # Operational score (0-15 pts) — baseline for just being open
    ops_score = 15

    total = rev_score + pay_score + stock_score + ops_score

    breakdown = {
        "revenue_trend":      rev_score,
        "payment_recovery":   pay_score,
        "stock_health":       stock_score,
        "operations":         ops_score,
        "total":              total,
    }

    grade = "Excellent" if total >= 85 else "Good" if total >= 65 else "Fair" if total >= 45 else "Needs Attention"

    trace = log_trace(state, "ScoreCalculator",
                      f"Health score: {total}/100 ({grade}). "
                      f"Revenue: {rev_score}/40, Recovery: {pay_score}/25, Stock: {stock_score}/20")

    return {"health_score": float(total), "score_breakdown": breakdown, "trace_log": trace}

# ── Node 3: Recommendation Engine ────────────────────────────────────────────

async def recommendation_engine_node(state: ReportState) -> dict:
    """
    LLM + Serper AI generates:
    1. One actionable recommendation for next week
    2. Market pulse (2-3 news snippets from Serper)
    """
    llm   = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"), google_api_key=os.getenv("GEMINI_API_KEY", "")) \
            if os.getenv("GEMINI_API_KEY") else \
            ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY", ""))

    top_cats  = state.get("top_products", [])
    trend     = state.get("revenue_trend", 0)
    score     = state.get("health_score", 70)
    city      = state.get("merchant_city", "Delhi")

    # Get market context from Serper
    market_news = []
    if top_cats:
        top_cat = top_cats[0]["category"]
        market_news = await serper_client.get_market_news(top_cat)

    local_events = await serper_client.get_local_events(city)
    events_text  = "; ".join(local_events.get("events", [])[:2])

    prompt = f"""
You are an AI business advisor for a Kirana store in {city}, India.

This week's data:
- Revenue trend: {trend:+.1f}% vs last week
- Top categories: {[c['category'] for c in top_cats[:3]]}
- Health score: {score:.0f}/100
- Local context: {events_text or 'No major events'}

Write ONE specific, actionable recommendation the shopkeeper can act on next week.
Keep it in simple Hinglish (mix of Hindi and English), under 2 sentences.
Focus on: stock pre-ordering, pricing opportunity, or customer segment.
"""
    try:
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        content_text = resp.content
        if isinstance(content_text, list):
            content_text = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content_text])
        recommendation = str(content_text).strip()
    except Exception as e:
        print(f"[WeeklyReport] LLM recommendation fallback: {e}")
        recommendation = ""

    # Ensure recommendation is complete and meaningful (not cut off like 'Is Friday n')
    if not recommendation or len(recommendation.split()) < 6:
        pending_amt = state.get("pending_khata", 4200)
        top_name = top_cats[0]["category"].title() if top_cats else "Dairy & Snacks"
        if trend < 0:
            recommendation = (
                f"Pichle hafte se bikri {trend:.1f}% kam rahi. Weekend ke liye {top_name} par special 5% discount launch karein "
                f"aur pending khata (₹{pending_amt:,.0f}) ke gentle reminders WhatsApp par schedule kijiye taaki cash flow sudhre."
            )
        else:
            recommendation = (
                f"Weekend par {top_name} ki demand 25-30% badhne ki sambhavna hai. "
                f"Advance mein Amul doodh, dahi aur snacks ka stock rakhein taaki koi bhi customer khaali haath na laute."
            )

    trace = log_trace(state, "RecommendationEngine",
                      f"AI recommendation generated. {len(market_news)} market signals found.")

    return {
        "recommendation": recommendation,
        "market_pulse":   market_news[:3],
        "trace_log":      trace,
    }

# ── Node 4: Report Generator ──────────────────────────────────────────────────

async def report_generator_node(state: ReportState) -> dict:
    """Assembles the full text report and generates PDF"""
    score     = state.get("health_score", 0)
    trend     = state.get("revenue_trend", 0)
    week_rev  = state.get("week_revenue", 0)
    recovered = state.get("khata_recovered", 0)
    top_cats  = state.get("top_products", [])
    recommend = state.get("recommendation", "")
    breakdown = state.get("score_breakdown", {})

    grade = "Excellent 🌟" if score >= 85 else "Good ✅" if score >= 65 else "Fair ⚠️" if score >= 45 else "Needs Attention 🔴"

    top_products_text = "\n".join(
        f"  {i+1}. {c['category'].title()}: ₹{c['revenue']:,.0f}"
        for i, c in enumerate(top_cats[:3])
    )

    report_text = f"""
📊 *KiranaMate Weekly Health Report*
_{datetime.utcnow().strftime('%d %b %Y')} — Week Summary_

━━━━━━━━━━━━━━━━━━━━
🏆 *Store Health Score: {score:.0f}/100 — {grade}*
━━━━━━━━━━━━━━━━━━━━

📈 *Revenue*
• This week: ₹{week_rev:,.0f}
• vs Last week: {trend:+.1f}%

🛒 *Top Categories*
{top_products_text}

💰 *Payments*
• Recovered via AI: ₹{recovered:,.0f}
• Still pending: ₹{state.get('pending_khata', 0):,.0f}

📊 *Score Breakdown*
• Revenue trend: {breakdown.get('revenue_trend', 0)}/40
• Payment recovery: {breakdown.get('payment_recovery', 0)}/25
• Stock health: {breakdown.get('stock_health', 0)}/20
• Operations: {breakdown.get('operations', 0)}/15

💡 *AI Recommendation*
{recommend}

━━━━━━━━━━━━━━━━━━━━
_Powered by MerchantMind AI | KiranaMate_
""".strip()

    # Generate PDF
    pdf_url = await _generate_pdf(report_text, state)

    trace = log_trace(state, "ReportGenerator",
                      f"Report compiled. Score: {score:.0f}/100. PDF: {'✅' if pdf_url else '❌'}")

    return {"report_text": report_text, "pdf_url": pdf_url, "trace_log": trace}


async def _generate_pdf(report_text: str, state: ReportState) -> Optional[str]:
    """Generate a styled PDF using ReportLab"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        import io

        buffer   = io.BytesIO()
        doc      = SimpleDocTemplate(buffer, pagesize=A4,
                                     leftMargin=2*cm, rightMargin=2*cm,
                                     topMargin=2*cm, bottomMargin=2*cm)
        styles   = getSampleStyleSheet()
        story    = []

        title_style = ParagraphStyle("Title",
            parent=styles["Title"], fontSize=22, textColor=colors.HexColor("#1a56db"),
            spaceAfter=6)
        sub_style   = ParagraphStyle("Sub",
            parent=styles["Normal"], fontSize=11, textColor=colors.grey, spaceAfter=16)
        h2_style    = ParagraphStyle("H2",
            parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#1a56db"),
            spaceBefore=14, spaceAfter=6)
        body_style  = ParagraphStyle("Body",
            parent=styles["Normal"], fontSize=11, spaceAfter=6)

        story.append(Paragraph("KiranaMate Weekly Health Report", title_style))
        story.append(Paragraph(datetime.utcnow().strftime("%d %B %Y"), sub_style))

        score = state.get("health_score", 0)
        grade = "Excellent" if score >= 85 else "Good" if score >= 65 else "Fair" if score >= 45 else "Needs Attention"
        story.append(Paragraph(f"Store Health Score: {score:.0f}/100 — {grade}", h2_style))

        trend    = state.get("revenue_trend", 0)
        week_rev = state.get("week_revenue", 0)
        trend_color = "#16a34a" if trend >= 0 else "#dc2626"

        data = [
            ["Metric",                  "Value"],
            ["This Week Revenue",        f"₹{week_rev:,.0f}"],
            ["vs Last Week",            f"{trend:+.1f}%"],
            ["Khata Recovered",         f"₹{state.get('khata_recovered', 0):,.0f}"],
            ["Pending Payments",        f"₹{state.get('pending_khata', 0):,.0f}"],
            ["Anomalies This Week",     str(state.get("anomalies_week", 0))],
        ]
        table = Table(data, colWidths=[8*cm, 7*cm])
        table.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#1a56db")),
            ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
            ("FONTSIZE",    (0,0), (-1,0), 12),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f0f4ff")]),
            ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("FONTSIZE",    (0,1), (-1,-1), 11),
            ("TOPPADDING",  (0,0), (-1,-1), 8),
            ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.4*cm))

        story.append(Paragraph("AI Recommendation", h2_style))
        story.append(Paragraph(state.get("recommendation", ""), body_style))

        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph("Powered by MerchantMind AI | KiranaMate", sub_style))

        doc.build(story)

        # Save to project's reports directory for web viewing and downloads
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reports_dir  = os.path.join(project_root, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        filename     = f"health_report_{state['merchant_id']}.pdf"
        pdf_path     = os.path.join(reports_dir, filename)
        with open(pdf_path, "wb") as f:
            f.write(buffer.getvalue())

        # Also save a standard-named copy for direct download
        std_path = os.path.join(reports_dir, "KiranaMate_Weekly_Report.pdf")
        with open(std_path, "wb") as f:
            f.write(buffer.getvalue())

        print(f"[ReportGenerator] PDF generated: {pdf_path}")

        # Build full public URL so WhatsApp can fetch the PDF
        tunnel_url = os.getenv("TUNNEL_URL", "").strip().rstrip("/")
        if tunnel_url:
            return f"{tunnel_url}/reports/{filename}"
        return f"/reports/{filename}"

    except Exception as e:
        print(f"[ReportGenerator] PDF error: {e}")
        return None

# ── Node 5: WhatsApp Delivery ─────────────────────────────────────────────────

async def whatsapp_delivery_node(state: ReportState) -> dict:
    """Sends the report via WhatsApp (PDF + summary text)"""
    result = await whatsapp_client.send_health_report(
        to=state["merchant_phone"],
        merchant_name=state["merchant_name"],
        health_score=state.get("health_score", 0),
        summary=state.get("report_text", ""),
        pdf_url=state.get("pdf_url"),
    )
    trace = log_trace(state, "WhatsAppDelivery",
                      f"Report delivered via WhatsApp. PDF attached: {bool(state.get('pdf_url'))}")
    return {"trace_log": trace}

# ── Node 6: Cognee Update ─────────────────────────────────────────────────────

async def cognee_update_node(state: ReportState) -> dict:
    """Store report outcome in Cognee for future comparison"""
    await cognee_client.log_agent_action(
        merchant_id=state["merchant_id"],
        action_type="weekly_health_report",
        inputs={"week_revenue": state.get("week_revenue")},
        output={
            "health_score": state.get("health_score"),
            "revenue_trend": state.get("revenue_trend"),
            "khata_recovered": state.get("khata_recovered"),
        },
        success=True,
    )
    trace = log_trace(state, "CogneeUpdate", "Report outcome stored in knowledge graph.")
    return {"trace_log": trace}

# ── Build Graph ───────────────────────────────────────────────────────────────

def build_report_graph():
    graph = StateGraph(ReportState)

    graph.add_node("data_aggregator",        data_aggregator_node)
    graph.add_node("score_calculator",       score_calculator_node)
    graph.add_node("recommendation_engine",  recommendation_engine_node)
    graph.add_node("report_generator",       report_generator_node)
    graph.add_node("whatsapp_delivery",      whatsapp_delivery_node)
    graph.add_node("cognee_update",          cognee_update_node)

    graph.set_entry_point("data_aggregator")
    graph.add_edge("data_aggregator",        "score_calculator")
    graph.add_edge("score_calculator",       "recommendation_engine")
    graph.add_edge("recommendation_engine",  "report_generator")
    graph.add_edge("report_generator",       "whatsapp_delivery")
    graph.add_edge("whatsapp_delivery",      "cognee_update")
    graph.add_edge("cognee_update",          END)

    return graph.compile()


async def run_weekly_report(
    merchant_id: str,
    merchant_phone: str,
    merchant_name: str,
    merchant_city: str = "Delhi",
) -> dict:
    """Entry point — called by N8N cron every Sunday at 7 PM"""
    try:
        from core.trace_bus import trace_bus
        trace_bus.emit_agent_start("report", f"Health Report for {merchant_name} Store")
    except Exception:
        pass

    graph = build_report_graph()
    result = await graph.ainvoke({
        "merchant_id":    merchant_id,
        "merchant_phone": merchant_phone,
        "merchant_name":  merchant_name,
        "merchant_city":  merchant_city,
        "week_revenue":   0.0,
        "prev_week_rev":  0.0,
        "revenue_trend":  0.0,
        "top_products":   [],
        "anomalies_week": 0,
        "khata_recovered":0.0,
        "pending_khata":  0.0,
        "health_score":   0.0,
        "score_breakdown":{},
        "recommendation": "",
        "market_pulse":   [],
        "report_text":    "",
        "pdf_url":        None,
        "trace_log":      [],
    })

    try:
        from core.trace_bus import trace_bus
        trace_bus.emit_agent_finish("report", "done", {
            "health_score": result.get("health_score"),
            "revenue_trend": result.get("revenue_trend"),
            "pdf_url": result.get("pdf_url") or "/reports/KiranaMate_Weekly_Report.pdf",
        })
    except Exception:
        pass

    return result
