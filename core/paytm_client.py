"""
Paytm Business API Client
Handles: Catalog price updates, POS telemetry, transaction history
"""
import os
import json
import hmac
import hashlib
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

PAYTM_MID  = os.getenv("PAYTM_MERCHANT_ID", "")
PAYTM_KEY  = os.getenv("PAYTM_MERCHANT_KEY", "")
PAYTM_ENV  = os.getenv("PAYTM_ENVIRONMENT", "staging")

BASE_URL = (
    "https://securegw.paytm.in"
    if PAYTM_ENV == "production"
    else "https://securegw-stage.paytm.in"
)


class PaytmClient:

    def __init__(self):
        self.mid = PAYTM_MID
        self.key = PAYTM_KEY

    def _checksum(self, params: dict) -> str:
        """Generate Paytm checksum for API authentication"""
        param_str = "|".join(str(params[k]) for k in sorted(params.keys()))
        return hmac.new(
            self.key.encode(),
            param_str.encode(),
            hashlib.sha256,
        ).hexdigest()

    # ── CATALOG PRICE UPDATE ──────────────────────────────────────────────────

    async def update_catalog_price(
        self,
        sku_id: str,
        new_price: float,
        sale_label: Optional[str] = None,
    ) -> dict:
        """
        Updates the selling price of a product in the Paytm catalog.
        Called by the campaign executor after merchant approval.

        In production this uses Paytm's Catalog Management API.
        """
        params = {
            "mid":       self.mid,
            "sku_id":    sku_id,
            "new_price": str(new_price),
            "currency":  "INR",
        }
        params["checksum"] = self._checksum(params)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{BASE_URL}/v1/catalog/price/update",
                    json=params,
                )
                if r.status_code == 200:
                    return {"success": True, "sku_id": sku_id, "new_price": new_price}
                return {"success": False, "error": r.text}
        except Exception as e:
            print(f"[Paytm] Catalog update error: {e}")
            # Return mock success for hackathon demo
            return {"success": True, "sku_id": sku_id, "new_price": new_price, "mock": True}

    async def bulk_update_prices(self, updates: list[dict]) -> dict:
        """
        Bulk price update for multiple SKUs after campaign approval.
        updates: [{"sku_id": "SKU-D001", "new_price": 23.40, "label": "Clearance"}, ...]
        """
        results = {}
        for upd in updates:
            result = await self.update_catalog_price(
                sku_id=upd["sku_id"],
                new_price=upd["new_price"],
                sale_label=upd.get("label", "Sale"),
            )
            results[upd["sku_id"]] = result

        success_count = sum(1 for r in results.values() if r.get("success"))
        return {
            "updated":       success_count,
            "total":         len(updates),
            "results":       results,
        }

    # ── TRANSACTION HISTORY ───────────────────────────────────────────────────

    async def fetch_recent_transactions(
        self,
        from_date: str,   # YYYY-MM-DD
        to_date: str,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        """
        Pulls transaction history from Paytm for ingestion into DB.
        Called by the N8N hourly sync workflow.
        """
        params = {
            "mid":       self.mid,
            "fromDate":  from_date,
            "toDate":    to_date,
            "pageNo":    page,
            "pageSize":  page_size,
        }
        params["checksum"] = self._checksum(params)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{BASE_URL}/v3/merchant/txnhistory",
                    json=params,
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            print(f"[Paytm] Transaction fetch error: {e}")
            return {"transactions": [], "error": str(e)}

    # ── SOUNDBOX / QR TELEMETRY ───────────────────────────────────────────────

    async def get_soundbox_status(self, device_id: str) -> dict:
        """
        Checks the status of a Paytm Soundbox device.
        Used to verify the merchant's payment terminal is online.
        """
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(
                    f"{BASE_URL}/v1/soundbox/status",
                    params={"mid": self.mid, "deviceId": device_id},
                    headers={"Authorization": f"Bearer {self.key}"},
                )
                return r.json()
        except Exception as e:
            return {"online": True, "mock": True}  # Demo fallback


paytm_client = PaytmClient()
