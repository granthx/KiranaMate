"""
KiranaMate — Real-time Trace & Activity Bus
Synchronizes agent execution, LangGraph node transitions, and WhatsApp messages
between the backend and the live dashboard in real-time.
"""
import asyncio
import json
from collections import deque
from datetime import datetime
from typing import Optional, AsyncGenerator

# Node mappings for UI (index 0..5 in AGENT_NODES)
NODE_INDEX_MAP = {
    "campaign": {
        "input_parser": 0, "inputparser": 0,
        "inventory_querier": 1, "inventoryquerier": 1,
        "discount_calculator": 2, "discountcalculator": 2,
        "campaign_designer": 3, "campaigndesigner": 3,
        "approval_gate": 4, "approvalgate": 4,
        "campaign_executor": 5, "campaignexecutor": 5,
        "outcome_summary": 5, "outcomesummary": 5,
    },
    "monitor": {
        "sales_ingestion": 0, "salesingestion": 0,
        "baseline_compare": 1, "anomaly_detector": 1, "anomalydetector": 1,
        "alert_composer": 2, "alertcomposer": 2, "log_normal": 2, "lognormal": 2,
        "khata_correlator": 3, "khatacorrelator": 3,
        "khata_reminder": 4, "khatareminder": 4, "whatsapp_notify": 4,
        "cognee_update": 5, "cogneeupdate": 5,
    },
    "report": {
        "data_aggregator": 0, "dataaggregator": 0,
        "score_calculator": 1, "scorecalculator": 1,
        "recommendation_engine": 2, "recommendationengine": 2,
        "report_generator": 3, "reportgenerator": 3,
        "whatsapp_delivery": 4, "whatsappdelivery": 4,
        "cognee_update": 5, "cogneeupdate": 5,
    }
}


class TraceBus:
    def __init__(self, maxlen: int = 300):
        self._events = deque(maxlen=maxlen)
        self._counter = 0
        self._subscribers: set[asyncio.Queue] = set()

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    def emit(self, event_type: str, data: dict) -> dict:
        evt = {
            "id": self._next_id(),
            "type": event_type,
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
            "data": data,
        }
        self._events.append(evt)

        # Broadcast to all connected SSE clients
        for q in list(self._subscribers):
            try:
                q.put_nowait(evt)
            except Exception:
                pass
        return evt

    def emit_agent_start(self, agent_key: str, title: str, meta: Optional[dict] = None) -> dict:
        return self.emit("agent_start", {
            "agent_key": agent_key,
            "title": title,
            "meta": meta or {},
        })

    def emit_node_step(
        self,
        agent_key: str,
        node: str,
        message: str,
        color: str = "green",
        node_index: Optional[int] = None
    ) -> dict:
        if node_index is None:
            clean_node = node.lower().replace("_", "").replace(" ", "")
            node_index = NODE_INDEX_MAP.get(agent_key, {}).get(clean_node)
            if node_index is None:
                # Fuzzy fallback matching
                for k, v in NODE_INDEX_MAP.get(agent_key, {}).items():
                    if k in clean_node or clean_node in k:
                        node_index = v
                        break

        return self.emit("node_step", {
            "agent_key": agent_key,
            "node": node,
            "node_index": node_index,
            "message": message,
            "color": color,
        })

    def emit_agent_finish(self, agent_key: str, status: str = "done", summary: Optional[dict] = None) -> dict:
        return self.emit("agent_finish", {
            "agent_key": agent_key,
            "status": status,
            "summary": summary or {},
        })

    def emit_wa_msg(self, role: str, text: str, extra: Optional[dict] = None) -> dict:
        """
        role:
          'sent'        = Merchant sent message to KiranaMate (WhatsApp green bubble on right)
          'received'    = KiranaMate replied to Merchant (WhatsApp bubble on left)
          'system-msg'  = System / status notice
          'success-msg' = Success banner
          'error-msg'   = Error notice
        """
        return self.emit("wa_message", {
            "role": role,
            "text": text,
            "extra": extra or {},
        })

    def get_events(self, since_id: int = 0) -> list[dict]:
        return [e for e in self._events if e["id"] > since_id]

    async def subscribe(self) -> AsyncGenerator[str, None]:
        q = asyncio.Queue(maxsize=150)
        self._subscribers.add(q)
        try:
            # Yield last 5 events on initial connect for instant sync
            recent = list(self._events)[-5:]
            for evt in recent:
                yield f"data: {json.dumps(evt)}\n\n"
            while True:
                evt = await q.get()
                yield f"data: {json.dumps(evt)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            self._subscribers.discard(q)


trace_bus = TraceBus()
