"""
Cognee Knowledge Graph Client
Pillar 2: THE MEMORY — persistent merchant intelligence
"""
import os
import json
import httpx
from typing import Any, Optional
from dotenv import load_dotenv

load_dotenv()

COGNEE_API_KEY = os.getenv("COGNEE_API_KEY", "")
COGNEE_BASE_URL = "https://api.cognee.ai/v1"  # Replace with actual endpoint


class CogneeClient:
    """
    Wraps Cognee API for KiranaMate's knowledge graph needs.

    Stores and retrieves:
    - Merchant business profiles
    - Sales baselines & anomaly memory
    - Campaign outcome history
    - Customer relationship & warmth scores
    - Margin floors per SKU/category
    """

    def __init__(self):
        self.api_key = COGNEE_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ── MERCHANT PROFILE ─────────────────────────────

    async def upsert_merchant_profile(self, merchant_id: str, profile: dict) -> bool:
        """Store/update merchant's business profile graph node"""
        payload = {
            "entity_type": "merchant",
            "entity_id": merchant_id,
            "data": profile,
        }
        return await self._post("/add", payload)

    async def get_merchant_profile(self, merchant_id: str) -> dict:
        """Retrieve merchant profile for agent reasoning"""
        return await self._get("/search", {"entity_type": "merchant", "entity_id": merchant_id})

    # ── SALES BASELINE ───────────────────────────────

    async def get_category_baseline(
        self,
        merchant_id: str,
        category: str,
        day_of_week: int,
    ) -> dict:
        """
        Returns the 4-week rolling average for a category on a given day.
        Used by anomaly detector to compare against actual sales.
        """
        return await self._get("/search", {
            "entity_type": "sales_baseline",
            "merchant_id": merchant_id,
            "category": category,
            "day_of_week": day_of_week,
        })

    async def update_daily_baseline(
        self,
        merchant_id: str,
        category: str,
        day_of_week: int,
        revenue: float,
    ) -> bool:
        """Add today's data point to the rolling baseline"""
        payload = {
            "entity_type": "sales_baseline",
            "merchant_id": merchant_id,
            "category": category,
            "day_of_week": day_of_week,
            "data": {"revenue": revenue, "timestamp": "now"},
        }
        return await self._post("/add", payload)

    # ── CAMPAIGN MEMORY ──────────────────────────────

    async def store_campaign_outcome(
        self,
        merchant_id: str,
        campaign_id: str,
        outcome: dict,
    ) -> bool:
        """
        Stores campaign result for future discount recommendation learning.
        Example outcome:
        {
          "category": "dairy",
          "discount_pct": 22,
          "customers_targeted": 150,
          "conversion_rate": 0.57,
          "revenue_recovered": 2340,
          "time_of_day": "18:00",
          "expiry_days": 3,
        }
        """
        payload = {
            "entity_type": "campaign_outcome",
            "entity_id": campaign_id,
            "merchant_id": merchant_id,
            "data": outcome,
        }
        return await self._post("/add", payload)

    async def get_best_discount_for_category(
        self,
        merchant_id: str,
        category: str,
        expiry_days: int,
    ) -> dict:
        """
        Returns historically optimal discount params for a category.
        LLM-queryable: 'What discount worked best for dairy with 3-day expiry?'
        """
        query = (
            f"What is the best discount percentage and timing for {category} "
            f"products with {expiry_days} days to expiry for merchant {merchant_id}? "
            f"Return the conversion rate and revenue outcome."
        )
        return await self._query(query)

    async def get_margin_floor(self, merchant_id: str, category: str) -> float:
        """Returns the minimum acceptable price (below which we lose money)"""
        result = await self._get("/search", {
            "entity_type": "margin_floor",
            "merchant_id": merchant_id,
            "category": category,
        })
        return result.get("floor_price", 0.0)

    # ── CUSTOMER RELATIONSHIP ────────────────────────

    async def get_customer_context(
        self,
        merchant_id: str,
        customer_id: str,
    ) -> dict:
        """
        Returns customer relationship graph for personalized comms.
        Includes: payment history, warmth score, preferred tone, last interaction.
        """
        return await self._get("/search", {
            "entity_type": "customer",
            "entity_id": customer_id,
            "merchant_id": merchant_id,
        })

    async def update_customer_warmth(
        self,
        merchant_id: str,
        customer_id: str,
        event: str,
        delta: float,
    ) -> bool:
        """
        Adjusts customer warmth score based on events.
        event: 'paid_on_time', 'ignored_reminder', 'disputed', 'large_purchase'
        delta: +0.1 or -0.2 etc.
        """
        payload = {
            "entity_type": "customer_warmth_update",
            "entity_id": customer_id,
            "merchant_id": merchant_id,
            "data": {"event": event, "delta": delta},
        }
        return await self._post("/add", payload)

    async def get_dairy_buyers(
        self,
        merchant_id: str,
        radius_km: float = 3.0,
        limit: int = 150,
    ) -> list[dict]:
        """
        Cognee graph query: find customers who bought dairy in last 30 days,
        within radius, active on WhatsApp.
        Used by broadcast sub-agent to select campaign targets.
        """
        query = (
            f"Find customers of merchant {merchant_id} who purchased dairy products "
            f"in the last 30 days, are within {radius_km}km, and are active WhatsApp users. "
            f"Return their name, phone, and segment. Limit {limit}."
        )
        result = await self._query(query)
        return result.get("customers", [])

    # ── SELF-IMPROVEMENT ─────────────────────────────

    async def log_agent_action(
        self,
        merchant_id: str,
        action_type: str,
        inputs: dict,
        output: dict,
        success: bool,
    ) -> bool:
        """
        Every agent action is logged for the self-improvement flywheel.
        Over time, this creates merchant-specific intelligence.
        """
        payload = {
            "entity_type": "agent_action",
            "merchant_id": merchant_id,
            "data": {
                "action_type": action_type,
                "inputs": inputs,
                "output": output,
                "success": success,
                "timestamp": "now",
            },
        }
        return await self._post("/add", payload)

    # ── HTTP HELPERS ─────────────────────────────────

    async def _post(self, path: str, payload: dict) -> Any:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{COGNEE_BASE_URL}{path}",
                    json=payload,
                    headers=self.headers,
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            print(f"[Cognee] POST error: {e}")
            return {}

    async def _get(self, path: str, params: dict) -> Any:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    f"{COGNEE_BASE_URL}{path}",
                    params=params,
                    headers=self.headers,
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            print(f"[Cognee] GET error: {e}")
            return {}

    async def _query(self, natural_language_query: str) -> Any:
        """Natural language query against the knowledge graph"""
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    f"{COGNEE_BASE_URL}/search",
                    json={"query": natural_language_query, "search_type": "GRAPH_COMPLETION"},
                    headers=self.headers,
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            print(f"[Cognee] Query error: {e}")
            return {}


# Singleton
cognee_client = CogneeClient()
