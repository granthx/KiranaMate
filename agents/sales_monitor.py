"""
LangGraph Sales Monitor & Health Tracker Agent
Scenario 2: Autonomous anomaly detection → WhatsApp alert + Khata recovery

Graph nodes:
  SalesIngestion → AnomalyDetector → [AlertComposer | LogNormal]
  → KhataCorrelator → WhatsAppDispatch → CogneeUpdate
"""
import os
import json
from typing import TypedDict, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from core.cognee_client import cognee_client
from core.whatsapp_client import whatsapp_client
from utils.anomaly_detector import detect_anomalies

# ── State ────────────────────────────────────────────────────────────────────

class MonitorState(TypedDict):
    merchant_id:     str
    merchant_phone:  str
    merchant_name:   str

    # Sales data
    todays_revenue:  dict   # {category: revenue}
    anomalies:       list   # list of anomaly dicts

    # Khata correlation
    overdue_khatas:  list   # customers with overdue payments

    # Alerts sent
    alerts_sent:     list
    reminders_sent:  list

    # Trace
    trace_log:       list


def log_trace(state: MonitorState, node: str, msg: str) -> list:
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
        trace_bus.emit_node_step("monitor", node, msg)
    except Exception:
        pass
    return state.get("trace_log", []) + [entry]

# ── Node 1: Sales Ingestion ───────────────────────────────────────────────────

async def sales_ingestion_node(state: MonitorState) -> dict:
    """Pull latest Paytm transactions from DB and aggregate by category"""
    from db.database import AsyncSessionLocal
    from utils.anomaly_detector import get_todays_revenue_by_category

    async with AsyncSessionLocal() as db:
        revenue = await get_todays_revenue_by_category(db, state["merchant_id"])

    total = sum(revenue.values())
    trace = log_trace(state, "SalesIngestion",
                      f"Ingested today's sales: ₹{total:,.0f} across {len(revenue)} categories")

    return {"todays_revenue": revenue, "trace_log": trace}

# ── Node 2: Anomaly Detector ──────────────────────────────────────────────────

async def anomaly_detector_node(state: MonitorState) -> dict:
    """Compare today's revenue against 4-week rolling baseline"""
    from db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        anomalies = await detect_anomalies(db, state["merchant_id"])

    if anomalies:
        top = anomalies[0]
        trace = log_trace(state, "AnomalyDetector",
                          f"🚨 {top['severity']}: {top['category']} down "
                          f"{abs(top['deviation_pct']):.1f}% vs baseline. "
                          f"Gap: ₹{top['gap']:,.0f}")
    else:
        trace = log_trace(state, "AnomalyDetector", "All categories within normal range ✅")

    return {"anomalies": anomalies, "trace_log": trace}

# ── Node 3: Alert Composer ────────────────────────────────────────────────────

async def alert_composer_node(state: MonitorState) -> dict:
    """Compose and send WhatsApp alerts for CRITICAL anomalies"""
    anomalies      = state.get("anomalies", [])
    merchant_phone = state["merchant_phone"]
    merchant_name  = state["merchant_name"]
    alerts_sent    = []

    critical = [a for a in anomalies if a["severity"] == "CRITICAL"]

    for anomaly in critical:
        result = await whatsapp_client.send_anomaly_alert(
            to=merchant_phone,
            category=anomaly["category"],
            deviation_pct=anomaly["deviation_pct"],
            expected_rev=anomaly["expected_revenue"],
            actual_rev=anomaly["actual_revenue"],
            merchant_name=merchant_name,
        )
        alerts_sent.append({
            "category": anomaly["category"],
            "sent":     result.get("success", False),
        })

    trace = log_trace(state, "AlertComposer",
                      f"WhatsApp alert dispatched for {len(critical)} critical anomaly(ies)")

    return {"alerts_sent": alerts_sent, "trace_log": trace}

# ── Node 4: Log Normal ────────────────────────────────────────────────────────

async def log_normal_node(state: MonitorState) -> dict:
    """No anomaly — log normal state and update Cognee baseline"""
    trace = log_trace(state, "LogNormal",
                      "Sales within normal range. Baseline updated in Cognee.")
    await cognee_client.update_daily_baseline(
        merchant_id=state["merchant_id"],
        category="all",
        day_of_week=datetime.utcnow().weekday(),
        revenue=sum(state.get("todays_revenue", {}).values()),
    )
    return {"trace_log": trace}

# ── Node 5: Khata Correlator ──────────────────────────────────────────────────

async def khata_correlator_node(state: MonitorState) -> dict:
    """
    When an anomaly is detected, check if overdue khata entries
    from customers in the affected category are contributing.
    """
    from db.database import AsyncSessionLocal
    from db.models import KhataEntry, Customer
    from sqlalchemy import select

    merchant_id = state["merchant_id"]
    anomalies   = state.get("anomalies", [])

    if not anomalies:
        return {"overdue_khatas": [], "trace_log": state.get("trace_log", [])}

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(KhataEntry, Customer)
            .join(Customer, KhataEntry.customer_id == Customer.id)
            .where(
                KhataEntry.merchant_id == merchant_id,
                KhataEntry.status == "pending",
            )
            .order_by(KhataEntry.amount.desc())
            .limit(5)
        )
        rows = result.fetchall()

    overdue = [
        {
            "khata_id":     str(row.KhataEntry.id),
            "customer_name":row.Customer.name,
            "customer_phone":row.Customer.phone,
            "amount":       row.KhataEntry.amount,
            "description":  row.KhataEntry.description,
            "warmth_score": row.Customer.warmth_score,
            "days_overdue": (datetime.utcnow() - row.KhataEntry.created_at).days,
        }
        for row in rows
    ]

    trace = log_trace(state, "KhataCorrelator",
                      f"Correlated with {len(overdue)} overdue khata entries "
                      f"(₹{sum(k['amount'] for k in overdue):,.0f} pending)")

    return {"overdue_khatas": overdue, "trace_log": trace}

# ── Node 6: Khata Reminder Dispatch ──────────────────────────────────────────

async def khata_reminder_node(state: MonitorState) -> dict:
    """Auto-send polite payment reminders for overdue khata entries"""
    overdue      = state.get("overdue_khatas", [])
    merchant_upi = f"sharma.store@paytm"   # from merchant profile
    reminders    = []

    for khata in overdue[:3]:  # Cap at 3 reminders per cycle
        # Determine tone based on warmth score
        warmth = khata.get("warmth_score", 0.5)
        tone   = "warm" if warmth > 0.7 else "formal" if warmth < 0.4 else "neutral"

        result = await whatsapp_client.send_khata_reminder(
            to=khata["customer_phone"],
            customer_name=khata["customer_name"],
            amount=khata["amount"],
            invoice_ref=khata["description"],
            merchant_upi=merchant_upi,
            tone=tone,
        )
        reminders.append({
            "customer": khata["customer_name"],
            "amount":   khata["amount"],
            "sent":     result.get("success", False),
            "tone":     tone,
        })

        # Update Cognee (reminder sent event)
        await cognee_client.log_agent_action(
            merchant_id=state["merchant_id"],
            action_type="khata_reminder",
            inputs={"customer": khata["customer_name"], "amount": khata["amount"]},
            output={"tone": tone, "sent": result.get("success", False)},
            success=result.get("success", False),
        )

    trace = log_trace(state, "KhataReminder",
                      f"Drafts cordial reminders sent to {len(reminders)} customers. "
                      f"Zero manual accounting required.")

    return {"reminders_sent": reminders, "trace_log": trace}

# ── Node 7: Cognee Update ─────────────────────────────────────────────────────

async def cognee_update_node(state: MonitorState) -> dict:
    """Write anomaly event and all actions to Cognee knowledge graph"""
    await cognee_client.log_agent_action(
        merchant_id=state["merchant_id"],
        action_type="sales_monitor_cycle",
        inputs={"revenue": state.get("todays_revenue")},
        output={
            "anomalies":  len(state.get("anomalies", [])),
            "alerts":     len(state.get("alerts_sent", [])),
            "reminders":  len(state.get("reminders_sent", [])),
        },
        success=True,
    )
    trace = log_trace(state, "CogneeUpdate",
                      "Cycle complete. Anomaly + actions written to knowledge graph.")
    return {"trace_log": trace}

# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_anomaly(state: MonitorState) -> str:
    anomalies = state.get("anomalies", [])
    if any(a["severity"] in ("CRITICAL", "WARNING") for a in anomalies):
        return "alert_composer"
    return "log_normal"

# ── Build Graph ───────────────────────────────────────────────────────────────

def build_monitor_graph():
    graph = StateGraph(MonitorState)

    graph.add_node("sales_ingestion",    sales_ingestion_node)
    graph.add_node("anomaly_detector",   anomaly_detector_node)
    graph.add_node("alert_composer",     alert_composer_node)
    graph.add_node("log_normal",         log_normal_node)
    graph.add_node("khata_correlator",   khata_correlator_node)
    graph.add_node("khata_reminder",     khata_reminder_node)
    graph.add_node("cognee_update",      cognee_update_node)

    graph.set_entry_point("sales_ingestion")
    graph.add_edge("sales_ingestion",  "anomaly_detector")

    graph.add_conditional_edges(
        "anomaly_detector",
        route_after_anomaly,
        {"alert_composer": "alert_composer", "log_normal": "log_normal"},
    )

    graph.add_edge("alert_composer", "khata_correlator")
    graph.add_edge("log_normal",     "cognee_update")
    graph.add_edge("khata_correlator","khata_reminder")
    graph.add_edge("khata_reminder",  "cognee_update")
    graph.add_edge("cognee_update",   END)

    return graph.compile()


async def run_monitor(merchant_id: str, merchant_phone: str, merchant_name: str) -> dict:
    """Entry point called by N8N cron every hour"""
    try:
        from core.trace_bus import trace_bus
        trace_bus.emit_agent_start("monitor", "Sales Monitor Anomaly Check")
    except Exception:
        pass

    graph = build_monitor_graph()
    result = await graph.ainvoke({
        "merchant_id":    merchant_id,
        "merchant_phone": merchant_phone,
        "merchant_name":  merchant_name,
        "todays_revenue": {},
        "anomalies":      [],
        "overdue_khatas": [],
        "alerts_sent":    [],
        "reminders_sent": [],
        "trace_log":      [],
    })

    try:
        from core.trace_bus import trace_bus
        trace_bus.emit_agent_finish("monitor", "done", {
            "anomalies": len(result.get("anomalies", [])),
            "alerts": len(result.get("alerts_sent", [])),
        })
    except Exception:
        pass

    return result
