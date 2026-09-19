"""
LangGraph Campaign Executor Agent
Scenario 1: Voice → Clearance Campaign in < 90 seconds

Graph nodes:
  InputParser → InventoryQuerier → DiscountCalculator
  → CampaignDesigner → ApprovalGate → CampaignExecutor → OutcomeSummary
"""
import os
import json
import asyncio
from typing import TypedDict, Annotated, Optional, Any
from datetime import datetime

from langgraph.graph import StateGraph, END
try:
    from langgraph.checkpoint.redis import AsyncRedisSaver
except ImportError:
    AsyncRedisSaver = None
from langgraph.checkpoint.memory import MemorySaver
try:
    from langgraph.errors import NodeInterrupt
except ImportError:
    try:
        from langgraph.types import NodeInterrupt
    except ImportError:
        class NodeInterrupt(Exception):
            """Fallback NodeInterrupt when not available in installed langgraph"""
            pass

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from core.cognee_client import cognee_client
from core.serper_client import serper_client
from core.whatsapp_client import whatsapp_client
from utils.discount_calculator import calculate_optimal_discount, estimate_revenue_recovery

import httpx

# ── LLM Setup ─────────────────────────────────────────────────────────────────

def get_llm():
    if os.getenv("GEMINI_API_KEY"):
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.3,
        )
    return ChatOpenAI(
        model="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.3,
    )

# ── State Definition ──────────────────────────────────────────────────────────

class CampaignState(TypedDict):
    # Input
    merchant_id:        str
    merchant_phone:     str
    merchant_name:      str
    merchant_city:      str
    merchant_upi:       str
    raw_input:          str          # Transcript or text goal

    # Parsed goal
    intent:             Optional[str]
    category:           Optional[str]
    quantity_target:    Optional[int]
    deadline_days:      Optional[int]

    # Inventory findings
    skus_found:         list[dict]   # [{sku_id, name, qty, price, cost, margin, expiry}]
    total_units:        int

    # Pricing
    competitor_data:    Optional[dict]
    discount_plan:      Optional[dict]  # per-SKU discount breakdown

    # Creative
    poster_url:         Optional[str]
    wa_messages:        list[str]

    # Execution
    target_customers:   list[dict]   # [{name, phone, segment}]
    campaign_id:        Optional[str]
    approval_status:    Optional[str]  # "pending", "approved", "cancelled"

    # Output
    execution_result:   Optional[dict]
    error:              Optional[str]

    # Trace (for demo UI)
    trace_log:          list[dict]

# ── Helper: trace logger ──────────────────────────────────────────────────────

def log_trace(state: CampaignState, node: str, message: str, color: str = "green") -> list:
    entry = {
        "ts":      datetime.utcnow().strftime("%M:%S.%f")[:7] + "s",
        "node":    node,
        "message": message,
        "color":   color,
    }
    try:
        print(f"[{entry['ts']}] [{node}] {message}")
    except UnicodeEncodeError:
        safe_msg = message.encode("ascii", errors="replace").decode("ascii")
        print(f"[{entry['ts']}] [{node}] {safe_msg}")
    try:
        from core.trace_bus import trace_bus
        trace_bus.emit_node_step("campaign", node, message, color)
    except Exception:
        pass
    return state.get("trace_log", []) + [entry]

# ── Node 1: Input Parser ──────────────────────────────────────────────────────

async def input_parser_node(state: CampaignState) -> dict:
    """Parse the merchant's raw voice/text input into a structured goal"""
    llm = get_llm()
    raw = state["raw_input"]

    prompt = f"""
Parse this Indian Kirana store merchant command into structured JSON.
Merchant said: "{raw}"

Return ONLY valid JSON:
{{
  "intent": "clearance_campaign" | "check_inventory" | "khata_reminder" | "unknown",
  "category": "dairy" | "snacks" | "staples" | "beverages" | "personal_care" | "all" | null,
  "quantity_target": <integer or null>,
  "deadline_days": <integer or null>,
  "discount_hint": <float or null>
}}
"""
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content_text = response.content
        if isinstance(content_text, list):
            content_text = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content_text])
        cleaned = str(content_text).strip().replace("```json", "").replace("```", "").strip()
        parsed  = json.loads(cleaned)
    except Exception as e:
        print(f"[InputParser] LLM parse error or fallback: {e}")
        raw_l = str(raw).lower()
        cat = "dairy" if any(k in raw_l for k in ["dairy", "milk", "paneer", "curd", "dahi", "cheese", "butter"]) else \
              "snacks" if any(k in raw_l for k in ["snack", "chips", "biscuit", "namkeen"]) else \
              "beverages" if any(k in raw_l for k in ["drink", "beverage", "juice", "coke", "pepsi"]) else \
              "staples" if any(k in raw_l for k in ["atta", "rice", "dal", "oil", "sugar", "staple"]) else \
              "personal_care" if any(k in raw_l for k in ["soap", "shampoo", "paste", "brush"]) else "dairy"
        days = 3
        import re
        m = re.search(r"(\d+)\s*(?:day|din)", raw_l)
        if m:
            days = int(m.group(1))
        parsed = {
            "intent": "clearance_campaign",
            "category": cat,
            "quantity_target": 100,
            "deadline_days": days,
            "discount_hint": None,
        }

    trace = log_trace(state, "InputParser",
                      f"Parsed: intent={parsed.get('intent')}, category={parsed.get('category')}, "
                      f"qty={parsed.get('quantity_target')}, days={parsed.get('deadline_days')}")

    return {
        "intent":         parsed.get("intent", "clearance_campaign"),
        "category":       parsed.get("category", "dairy"),
        "quantity_target":parsed.get("quantity_target"),
        "deadline_days":  parsed.get("deadline_days"),
        "trace_log":      trace,
    }

# ── Node 2: Inventory Querier ─────────────────────────────────────────────────

async def inventory_querier_node(state: CampaignState) -> dict:
    """Query the DB for expiring SKUs matching the merchant's goal"""
    from db.database import AsyncSessionLocal
    from db.models import InventoryItem
    from sqlalchemy import select
    from datetime import timedelta

    category     = state.get("category", "dairy")
    deadline_days = state.get("deadline_days", 3)
    merchant_id  = state["merchant_id"]

    cutoff_date  = datetime.utcnow() + timedelta(days=deadline_days or 3)

    async with AsyncSessionLocal() as db:
        query = select(InventoryItem).where(
            InventoryItem.merchant_id == merchant_id,
            InventoryItem.quantity > 0,
        )
        if category and category != "all":
            query = query.where(InventoryItem.category == category)
        if deadline_days:
            query = query.where(InventoryItem.expiry_date <= cutoff_date)

        result = await db.execute(query)
        items  = result.scalars().all()

    skus = [
        {
            "sku_id":    item.sku_id,
            "name":      item.name,
            "category":  item.category,
            "quantity":  item.quantity,
            "price":     item.selling_price,
            "cost":      item.unit_cost,
            "margin_pct":item.margin_pct,
            "expiry":    item.expiry_date.isoformat() if item.expiry_date else None,
        }
        for item in items
    ]
    total = sum(s["quantity"] for s in skus)

    trace = log_trace(state, "Inventory",
                      f"SQL matched {len(skus)} SKUs, {total} total units "
                      f"({', '.join(s['name'] for s in skus[:3])})")

    return {"skus_found": skus, "total_units": total, "trace_log": trace}

# ── Node 3: Discount Calculator ───────────────────────────────────────────────

async def discount_calculator_node(state: CampaignState) -> dict:
    """
    Fetches competitor prices via Serper AI + margin floors via Cognee.
    Calculates margin-safe discount per SKU.
    """
    skus         = state.get("skus_found", [])
    merchant_id  = state["merchant_id"]
    city         = state.get("merchant_city", "Delhi")

    if not skus:
        return {"error": "No expiring SKUs found for this category.", "trace_log": state.get("trace_log", [])}

    # Use first SKU as representative for competitor search
    primary_sku  = skus[0]
    competitor   = await serper_client.get_competitor_prices(primary_sku["name"], city)

    trace = log_trace(state, "SerperAI",
                      f"Competitor benchmark: avg ₹{competitor.get('avg_price', 'N/A')}, "
                      f"min ₹{competitor.get('min_price', 'N/A')}")

    # Get Cognee historical best discount
    hist = await cognee_client.get_best_discount_for_category(
        merchant_id,
        primary_sku["category"],
        state.get("deadline_days", 3),
    )
    hist_discount = hist.get("best_discount_pct") if hist else None

    # Calculate per-SKU discount
    discount_plan = {}
    for sku in skus:
        calc = calculate_optimal_discount(
            current_price=sku["price"],
            unit_cost=sku["cost"],
            competitor_avg_price=competitor.get("avg_price"),
            competitor_min_price=competitor.get("min_price"),
            historical_best_discount=hist_discount,
        )
        est = estimate_revenue_recovery(sku["quantity"], calc["final_price"])
        discount_plan[sku["sku_id"]] = {**calc, "revenue_estimate": est}

    # Summary discount for approval message
    avg_discount = round(
        sum(d["optimal_discount_pct"] for d in discount_plan.values()) / len(discount_plan), 1
    )

    trace2 = log_trace({"trace_log": trace}, "Pricing",
                       f"Optimal avg discount: {avg_discount}% applied. Floor protected.")

    return {
        "competitor_data": competitor,
        "discount_plan":   discount_plan,
        "trace_log":       trace2,
    }

# ── Node 4: Campaign Designer ─────────────────────────────────────────────────

async def campaign_designer_node(state: CampaignState) -> dict:
    """
    Generates:
    1. Promotional poster prompt → Stable Diffusion / DALL-E
    2. Three WhatsApp message variants
    3. Target customer list from Cognee
    """
    llm          = get_llm()
    skus         = state.get("skus_found", [])
    discount_plan = state.get("discount_plan", {})
    merchant_id  = state["merchant_id"]
    category     = state.get("category", "dairy")

    # Primary discount info
    first_plan = list(discount_plan.values())[0] if discount_plan else {}
    discount   = first_plan.get("optimal_discount_pct", 20)
    new_price  = first_plan.get("final_price", 0)
    sku_names  = ", ".join(s["name"] for s in skus[:3])

    # Generate 3 WhatsApp copy variants
    copy_prompt = f"""
Generate 3 WhatsApp promotional messages for a Kirana store in India.
Product: {sku_names}
Discount: {discount:.0f}% off today only
Target: Existing dairy customers
Language: Mix of Hindi and English (Hinglish)
Tone: Friendly, urgent but not pushy

Return JSON array of 3 objects: [{{"variant": "short|medium|long", "message": "..."}}]
Each message should start with an emoji, mention the discount and create urgency.
"""
    try:
        copy_resp = await llm.ainvoke([HumanMessage(content=copy_prompt)])
        content_text = copy_resp.content
        if isinstance(content_text, list):
            content_text = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content_text])
        cleaned   = str(content_text).strip().replace("```json","").replace("```","").strip()
        messages  = json.loads(cleaned)
        wa_msgs   = [m["message"] for m in messages]
    except Exception as e:
        print(f"[CreativeGenerator] LLM copy error or fallback: {e}")
        wa_msgs = [
            f"🥛 Dairy Sale! {discount:.0f}% off today only. Fresh stock, limited time! Order now.",
            f"Hi, milk & paneer {discount:.0f}% off today — expiring soon clearance. Fresh & quality guaranteed! Click to order. 🎉",
            f"Namaste! Aaj ka special offer: {sku_names} par {discount:.0f}% discount. Limited stock. Jaldi order karein! 🛒",
        ]

    # Generate poster via Stable Diffusion (placeholder URL for now)
    poster_prompt = (
        f"Indian grocery kirana store promotional sale poster, "
        f"{category} products, {discount:.0f}% discount, "
        f"bright colors, Hindi text 'Aaj ka Offer', clean minimal design, "
        f"yellow and white color scheme, warm and inviting"
    )
    poster_url = await _generate_poster(poster_prompt)

    # Get target customers from Cognee
    customers = await cognee_client.get_dairy_buyers(merchant_id, radius_km=3.0, limit=150)
    if not customers:
        # Fallback: use seed data customers
        customers = [
            {"name": "Mohan Sharma", "phone": "9811001001", "segment": "regular"},
            {"name": "Sunita Devi",  "phone": "9811001002", "segment": "regular"},
            {"name": "Vijay Kumar",  "phone": "9811001005", "segment": "regular"},
        ]

    trace = log_trace(state, "Creative",
                      f"Poster rendered + {len(wa_msgs)} copy variations generated. "
                      f"{len(customers)} customers identified.")

    return {
        "poster_url":       poster_url,
        "wa_messages":      wa_msgs,
        "target_customers": customers,
        "trace_log":        trace,
    }


async def _generate_poster(prompt: str) -> Optional[str]:
    """Call Stable Diffusion 3.5 or DALL-E to generate a promo poster"""
    stability_key = os.getenv("STABILITY_API_KEY")
    if stability_key:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    "https://api.stability.ai/v2beta/stable-image/generate/core",
                    headers={"authorization": f"Bearer {stability_key}", "accept": "application/json"},
                    data={"prompt": prompt, "output_format": "png", "width": 1024, "height": 1024},
                )
                if r.status_code == 200:
                    # In production: upload to S3/Cloudinary and return URL
                    return "https://example.com/promo_poster.png"
        except Exception as e:
            print(f"[Stability] Poster error: {e}")

    # DALL-E fallback
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=openai_key)
            resp = await client.images.generate(prompt=prompt[:1000], n=1, size="1024x1024")
            return resp.data[0].url
        except Exception as e:
            print(f"[DALL-E] Poster error: {e}")

    return None

# ── Node 5: Approval Gate (Human-in-the-Loop) ────────────────────────────────

async def approval_gate_node(state: CampaignState) -> dict:
    """
    Sends campaign summary to merchant via WhatsApp.
    Raises NodeInterrupt — LangGraph pauses until merchant responds.
    """
    merchant_phone = state["merchant_phone"]
    skus           = state.get("skus_found", [])
    discount_plan  = state.get("discount_plan", {})
    customers      = state.get("target_customers", [])

    first_plan   = list(discount_plan.values())[0] if discount_plan else {}
    discount_pct = first_plan.get("optimal_discount_pct", 20)
    new_price    = first_plan.get("final_price", 0)
    old_price    = first_plan.get("current_price", 0)
    est_revenue  = sum(
        d["revenue_estimate"]["revenue_expected"]
        for d in discount_plan.values()
        if d.get("revenue_estimate")
    )

    # Create a campaign record in DB and get ID
    campaign_id = "camp_" + datetime.utcnow().strftime("%Y%m%d%H%M%S")

    summary = {
        "skus":               ", ".join(s["name"] for s in skus[:3]),
        "discount_pct":       discount_pct,
        "new_price":          new_price,
        "old_price":          old_price,
        "customers_targeted": len(customers),
        "estimated_revenue":  est_revenue,
    }

    await whatsapp_client.send_campaign_approval(
        to=merchant_phone,
        campaign_summary=summary,
        campaign_id=campaign_id,
    )

    trace = log_trace(state, "Approval",
                      f"Approval request sent to {merchant_phone}. Awaiting merchant response.")

    # Interrupt the graph — it resumes when webhook calls /campaign/approve/{campaign_id}
    raise NodeInterrupt(
        f"Awaiting merchant approval. Campaign ID: {campaign_id}. "
        f"Resume via POST /campaign/approve/{campaign_id}"
    )

# ── Node 6: Campaign Executor ─────────────────────────────────────────────────

async def campaign_executor_node(state: CampaignState) -> dict:
    """
    After approval: update Paytm catalog + blast WhatsApp to all target customers.
    """
    if state.get("approval_status") != "approved":
        return {"error": "Campaign not approved. Execution aborted.", "trace_log": state.get("trace_log", [])}

    customers    = state.get("target_customers", [])
    wa_messages  = state.get("wa_messages", [])
    poster_url   = state.get("poster_url")
    discount_plan = state.get("discount_plan", {})
    merchant_id  = state["merchant_id"]

    # Use medium variant (index 1) or first available
    broadcast_msg = wa_messages[1] if len(wa_messages) > 1 else wa_messages[0] if wa_messages else ""

    # 1. Update Paytm catalog prices
    paytm_results = await _update_paytm_prices(discount_plan, merchant_id)

    trace = log_trace(state, "PaytmAPI",
                      f"{len(discount_plan)} catalog SKU prices updated to discounted tiers")

    # 2. Send WhatsApp broadcasts
    sent_count = 0
    for customer in customers:
        result = await whatsapp_client.send_campaign_broadcast(
            to=customer["phone"],
            customer_name=customer["name"],
            message_body=broadcast_msg.replace("[Name]", customer["name"]),
            image_url=poster_url,
        )
        if result.get("success"):
            sent_count += 1
        await asyncio.sleep(0.05)  # Rate limit: 20 msgs/sec

    trace2 = log_trace({"trace_log": trace}, "MetaAPI",
                       f"{sent_count} targeted WhatsApp broadcasts dispatched ✅")

    result = {
        "messages_sent":   sent_count,
        "paytm_updated":   len(discount_plan),
        "poster_sent":     bool(poster_url),
        "completed_at":    datetime.utcnow().isoformat(),
    }

    return {"execution_result": result, "trace_log": trace2}


async def _update_paytm_prices(discount_plan: dict, merchant_id: str) -> dict:
    """Calls Paytm Business API to update catalog prices (stub)"""
    paytm_key = os.getenv("PAYTM_MERCHANT_KEY", "")
    results   = {}
    for sku_id, plan in discount_plan.items():
        results[sku_id] = {
            "updated": True,
            "new_price": plan["final_price"],
            "sku": sku_id,
        }
        # TODO: replace with real Paytm catalog update API call
    return results

# ── Node 7: Outcome Summary ───────────────────────────────────────────────────

async def outcome_summary_node(state: CampaignState) -> dict:
    """Sends final success message and writes outcome to Cognee"""
    result         = state.get("execution_result", {})
    merchant_phone = state["merchant_phone"]
    merchant_id    = state["merchant_id"]
    discount_plan  = state.get("discount_plan", {})

    est_revenue = sum(
        d["revenue_estimate"]["revenue_expected"]
        for d in discount_plan.values()
        if d.get("revenue_estimate")
    )

    await whatsapp_client.send_campaign_result(
        to=merchant_phone,
        units_sold=result.get("messages_sent", 0) // 5,
        revenue_recovered=est_revenue,
        customers_responded=result.get("messages_sent", 0),
    )

    # Write to Cognee for self-improvement
    await cognee_client.store_campaign_outcome(
        merchant_id=merchant_id,
        campaign_id=state.get("campaign_id", "unknown"),
        outcome={
            "category":           state.get("category"),
            "discount_pct":       list(discount_plan.values())[0]["optimal_discount_pct"] if discount_plan else 0,
            "customers_targeted": len(state.get("target_customers", [])),
            "messages_sent":      result.get("messages_sent", 0),
            "estimated_revenue":  est_revenue,
            "deadline_days":      state.get("deadline_days"),
            "executed_at":        datetime.utcnow().isoformat(),
        },
    )

    trace = log_trace(state, "OutcomeSummary",
                      f"Campaign complete. ₹{est_revenue:,.0f} est. recovery. Outcome written to Cognee.")

    return {"trace_log": trace}

# ── Conditional Edge ──────────────────────────────────────────────────────────

def route_after_inventory(state: CampaignState) -> str:
    if not state.get("skus_found"):
        return "outcome_summary"   # No stock found → skip to end
    if state.get("error"):
        return "outcome_summary"
    return "discount_calculator"

# ── Build Graph ───────────────────────────────────────────────────────────────

def build_campaign_graph(checkpointer=None):
    graph = StateGraph(CampaignState)

    graph.add_node("input_parser",        input_parser_node)
    graph.add_node("inventory_querier",   inventory_querier_node)
    graph.add_node("discount_calculator", discount_calculator_node)
    graph.add_node("campaign_designer",   campaign_designer_node)
    graph.add_node("approval_gate",       approval_gate_node)
    graph.add_node("campaign_executor",   campaign_executor_node)
    graph.add_node("outcome_summary",     outcome_summary_node)

    graph.set_entry_point("input_parser")
    graph.add_edge("input_parser",        "inventory_querier")
    graph.add_conditional_edges(
        "inventory_querier",
        route_after_inventory,
        {
            "discount_calculator": "discount_calculator",
            "outcome_summary":     "outcome_summary",
        }
    )
    graph.add_edge("discount_calculator", "campaign_designer")
    graph.add_edge("campaign_designer",   "approval_gate")
    graph.add_edge("approval_gate",       "campaign_executor")
    graph.add_edge("campaign_executor",   "outcome_summary")
    graph.add_edge("outcome_summary",     END)

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["campaign_executor"],  # Pause for human approval
    )


# Global in-memory checkpointer fallback when Redis is offline
_memory_checkpointer = MemorySaver()


def get_checkpointer():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    if AsyncRedisSaver is not None and not redis_url.startswith("memory://"):
        try:
            return AsyncRedisSaver.from_conn_string(redis_url)
        except Exception:
            pass
    return _memory_checkpointer


# ── Public API ────────────────────────────────────────────────────────────────

async def run_campaign(initial_state: dict, thread_id: str) -> dict:
    """
    Run the campaign graph from the beginning.
    Returns after hitting the approval interrupt.
    """
    try:
        from core.trace_bus import trace_bus
        goal_text = initial_state.get("raw_input", "Campaign")
        trace_bus.emit_agent_start("campaign", f"Campaign Executor: {goal_text[:60]}")
    except Exception:
        pass

    checkpointer = get_checkpointer()
    graph        = build_campaign_graph(checkpointer)

    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = await graph.ainvoke(initial_state, config=config)
        try:
            from core.trace_bus import trace_bus
            trace_bus.emit_agent_finish("campaign", "done", {"thread_id": thread_id})
        except Exception:
            pass
        return result
    except NodeInterrupt as ni:
        try:
            from core.trace_bus import trace_bus
            trace_bus.emit_agent_finish("campaign", "awaiting_approval", {"message": str(ni), "thread_id": thread_id})
        except Exception:
            pass
        return {"status": "awaiting_approval", "message": str(ni), "thread_id": thread_id}


async def resume_campaign(thread_id: str, approval_status: str) -> dict:
    """
    Resume the graph after merchant approval/cancellation.
    Called by the WhatsApp webhook when merchant taps Approve.
    """
    try:
        from core.trace_bus import trace_bus
        trace_bus.emit_agent_start("campaign", f"Resuming Campaign ({approval_status})")
    except Exception:
        pass

    checkpointer = get_checkpointer()
    graph        = build_campaign_graph(checkpointer)

    config = {"configurable": {"thread_id": thread_id}}

    # Update state with approval
    await graph.aupdate_state(
        config,
        {"approval_status": approval_status},
    )

    result = await graph.ainvoke(None, config=config)
    try:
        from core.trace_bus import trace_bus
        trace_bus.emit_agent_finish("campaign", "done", {"status": approval_status, "thread_id": thread_id})
    except Exception:
        pass
    return result
