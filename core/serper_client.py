"""
Serper AI Client — Competitor Price Intelligence
Pillar 4: THE EYES — real-world market awareness
"""
import os
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SERPER_BASE_URL = "https://google.serper.dev"


class SerperClient:
    """
    Uses Serper AI to give the agent real-world market context:
    - Competitor prices for specific SKUs
    - Demand trend detection (festive seasons, events)
    - Local market conditions by pin code
    """

    def __init__(self):
        self.api_key = SERPER_API_KEY
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    async def get_competitor_prices(
        self,
        product_name: str,
        city: str,
        pin_code: Optional[str] = None,
    ) -> dict:
        """
        Scrapes Google Shopping for local competitor prices.

        Returns:
        {
            "product": "Amul Toned Milk 500ml",
            "competitor_prices": [24, 25, 26, 28],
            "avg_price": 25.75,
            "min_price": 24,
            "max_price": 28,
            "sources": ["BigBasket", "Blinkit", "JioMart"],
        }
        """
        location_str = f"{city}" + (f" {pin_code}" if pin_code else "")
        query = f"{product_name} price {location_str} grocery store"

        shopping_results = await self._shopping_search(query)
        web_results = await self._web_search(query)

        prices = []
        sources = []

        for item in shopping_results.get("shopping", []):
            price_str = item.get("price", "").replace("₹", "").replace(",", "").strip()
            try:
                prices.append(float(price_str.split()[0]))
                sources.append(item.get("source", "Unknown"))
            except (ValueError, IndexError):
                pass

        if not prices:
            # Fallback: extract from web results snippets
            for result in web_results.get("organic", [])[:5]:
                snippet = result.get("snippet", "")
                import re
                price_matches = re.findall(r"₹\s*(\d+(?:\.\d+)?)", snippet)
                for p in price_matches:
                    try:
                        prices.append(float(p))
                    except ValueError:
                        pass

        if not prices:
            return {
                "product": product_name,
                "competitor_prices": [],
                "avg_price": None,
                "min_price": None,
                "max_price": None,
                "sources": [],
                "note": "No competitor prices found. Proceed with margin-floor calculation.",
            }

        return {
            "product": product_name,
            "competitor_prices": prices,
            "avg_price": round(sum(prices) / len(prices), 2),
            "min_price": min(prices),
            "max_price": max(prices),
            "sources": list(set(sources))[:5],
        }

    async def get_demand_trends(
        self,
        category: str,
        city: str,
    ) -> dict:
        """
        Detects demand trends for a category (festive season, supply disruptions).
        Used by the weekly health report recommender.
        """
        query = f"{category} demand trend India {city} 2024"
        results = await self._web_search(query)

        snippets = [r.get("snippet", "") for r in results.get("organic", [])[:5]]

        return {
            "category": category,
            "query": query,
            "snippets": snippets,
            "raw": results,
        }

    async def get_local_events(
        self,
        city: str,
        pin_code: Optional[str] = None,
    ) -> dict:
        """
        Checks for local festivals/events that could affect demand.
        e.g. "Diwali in 8 days → stock gift hampers"
        """
        query = f"upcoming festivals events {city} this month 2024"
        results = await self._web_search(query)
        return {
            "city": city,
            "events": [r.get("title", "") + " — " + r.get("snippet", "")
                       for r in results.get("organic", [])[:3]],
        }

    async def get_market_news(self, category: str) -> list[str]:
        """
        GST changes, supply disruptions, regulatory news relevant to a category.
        Used in the weekly health report's 'Market Pulse' section.
        """
        query = f"{category} India news price supply chain 2024"
        results = await self._web_search(query)
        return [
            r.get("title", "")
            for r in results.get("organic", [])[:5]
        ]

    # ── HTTP ──────────────────────────────────────────

    async def _shopping_search(self, query: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{SERPER_BASE_URL}/shopping",
                    json={"q": query, "gl": "in", "hl": "en", "num": 10},
                    headers=self.headers,
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            print(f"[Serper] Shopping search error: {e}")
            return {}

    async def _web_search(self, query: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{SERPER_BASE_URL}/search",
                    json={"q": query, "gl": "in", "hl": "en", "num": 10},
                    headers=self.headers,
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            print(f"[Serper] Web search error: {e}")
            return {}


serper_client = SerperClient()
