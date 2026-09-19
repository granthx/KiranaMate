"""
WhatsApp Business API Client (Meta Cloud API)
Zero-friction merchant interface — 100% WhatsApp native
"""
import os
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

WA_TOKEN    = os.getenv("WHATSAPP_TOKEN", "")
WA_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WA_BASE_URL = f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages"


class WhatsAppClient:

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {WA_TOKEN}",
            "Content-Type": "application/json",
        }

    # ── TEXT MESSAGE ──────────────────────────────────

    async def send_text(self, to: str, message: str) -> dict:
        """Send a plain text WhatsApp message"""
        try:
            from core.trace_bus import trace_bus
            trace_bus.emit_wa_msg("received", message)
        except Exception:
            pass
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }
        return await self._post(payload)

    # ── ANOMALY ALERT with ACTION BUTTONS ────────────

    async def send_anomaly_alert(
        self,
        to: str,
        category: str,
        deviation_pct: float,
        expected_rev: float,
        actual_rev: float,
        merchant_name: str = "ji",
    ) -> dict:
        """
        Sends an interactive anomaly alert with 2 quick-reply buttons:
        [Run Clearance] [View Details]
        """
        gap = round(expected_rev - actual_rev, 2)
        message = (
            f"🚨 *Alert: {category.title()} Sales Down {abs(deviation_pct):.0f}%*\n\n"
            f"Namaste {merchant_name}, aapki {category} category expected se "
            f"₹{gap:,.0f} neeche hai aaj.\n\n"
            f"Expected: ₹{expected_rev:,.0f} | Actual: ₹{actual_rev:,.0f}\n\n"
            f"Kya main ek clearance campaign launch karun?"
        )
        try:
            from core.trace_bus import trace_bus
            trace_bus.emit_wa_msg("received", message, extra={"buttons": ["Run Campaign", "Details", "Ignore"]})
        except Exception:
            pass
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "run_clearance",  "title": "✅ Run Campaign"}},
                        {"type": "reply", "reply": {"id": "view_details",   "title": "📊 Details"}},
                        {"type": "reply", "reply": {"id": "ignore_alert",   "title": "❌ Ignore"}},
                    ]
                },
            },
        }
        return await self._post(payload)

    # ── CAMPAIGN APPROVAL REQUEST ────────────────────

    async def send_campaign_approval(
        self,
        to: str,
        campaign_summary: dict,
        campaign_id: str,
    ) -> dict:
        """
        Sends a Human-in-the-Loop approval request.
        Merchant taps Approve → campaign goes live.
        """
        skus      = campaign_summary.get("skus", "dairy items")
        discount  = campaign_summary.get("discount_pct", 22)
        customers = campaign_summary.get("customers_targeted", 0)
        est_rev   = campaign_summary.get("estimated_revenue", 0)
        price_new = campaign_summary.get("new_price", "N/A")
        price_old = campaign_summary.get("old_price", "N/A")

        body = (
            f"📣 *Campaign Ready to Launch!*\n\n"
            f"• Products: {skus}\n"
            f"• Discount: *{discount}% off* (₹{price_old} → ₹{price_new})\n"
            f"• Customers to notify: *{customers}*\n"
            f"• Estimated revenue recovery: *₹{est_rev:,.0f}*\n\n"
            f"Competitor price checked ✅ | Margin protected ✅\n\n"
            f"Approve karna hai?"
        )
        try:
            from core.trace_bus import trace_bus
            trace_bus.emit_wa_msg("received", body, extra={"buttons": ["Approve", "Cancel"]})
        except Exception:
            pass
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": f"approve_{campaign_id}", "title": "✅ Approve"}},
                        {"type": "reply", "reply": {"id": f"cancel_{campaign_id}",  "title": "❌ Cancel"}},
                    ]
                },
            },
        }
        return await self._post(payload)

    # ── CAMPAIGN BROADCAST ───────────────────────────

    async def send_campaign_broadcast(
        self,
        to: str,
        customer_name: str,
        message_body: str,
        image_url: Optional[str] = None,
    ) -> dict:
        """
        Sends a promotional campaign message to a customer.
        Optionally includes a promo poster image.
        """
        if image_url:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "image",
                "image": {
                    "link": image_url,
                    "caption": message_body,
                },
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message_body},
            }
        return await self._post(payload)

    # ── KHATA REMINDER ───────────────────────────────

    async def send_khata_reminder(
        self,
        to: str,
        customer_name: str,
        amount: float,
        invoice_ref: str,
        merchant_upi: str,
        tone: str = "warm",
    ) -> dict:
        """
        Sends a polite, personalized payment reminder.
        Tone is set based on Cognee's warmth score for the customer.
        """
        if tone == "warm":
            message = (
                f"Namaste {customer_name} bhai 🙏\n\n"
                f"Ek choti si yaad dilata hun — aapka *₹{amount:,.0f}* "
                f"({invoice_ref}) se baaki hai.\n\n"
                f"Aap apni suvidha se UPI se bhej sakte hain:\n"
                f"*{merchant_upi}*\n\n"
                f"Koi baat nahi, bas record ke liye! 😊\n"
                f"— Sharma General Store"
            )
        elif tone == "formal":
            message = (
                f"Dear {customer_name},\n\n"
                f"This is a gentle reminder regarding your outstanding amount of "
                f"*₹{amount:,.0f}* against {invoice_ref}.\n\n"
                f"Kindly settle via UPI: *{merchant_upi}*\n\n"
                f"Thank you for your continued business.\n"
                f"— Sharma General Store"
            )
        else:
            message = (
                f"Hi {customer_name} 👋\n\n"
                f"Just a reminder — ₹{amount:,.0f} ({invoice_ref}) is pending.\n"
                f"Pay via UPI: *{merchant_upi}*\n\n"
                f"Thanks! 🙏"
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "paid_khata", "title": "✅ I've Paid"}},
                        {"type": "reply", "reply": {"id": "call_me",    "title": "📞 Call Me"}},
                    ]
                },
            },
        }
        return await self._post(payload)

    # ── HEALTH REPORT ────────────────────────────────

    async def send_health_report(
        self,
        to: str,
        merchant_name: str,
        health_score: float,
        summary: str,
        pdf_url: Optional[str] = None,
    ) -> dict:
        """Sends the Sunday weekly health report + optional PDF attachment"""
        if "KiranaMate Weekly Health Report" in summary:
            full_msg = summary
        else:
            full_msg = (
                f"📊 *KiranaMate Weekly Health Report*\n\n"
                f"Store Score: *{health_score:.0f}/100*\n\n"
                f"{summary}"
            )

        try:
            from core.trace_bus import trace_bus
            trace_bus.emit_wa_msg("received", full_msg, extra={"pdf_url": pdf_url, "health_score": health_score})
        except Exception:
            pass

        if pdf_url and (pdf_url.startswith("http://") or pdf_url.startswith("https://")):
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "document",
                "document": {
                    "link": pdf_url,
                    "caption": full_msg[:1024],
                    "filename": "KiranaMate_Weekly_Report.pdf",
                },
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {
                    "body": full_msg
                },
            }
        return await self._post(payload)

    # ── EXECUTION SUMMARY ────────────────────────────

    async def send_campaign_result(
        self,
        to: str,
        units_sold: int,
        revenue_recovered: float,
        customers_responded: int,
    ) -> dict:
        message = (
            f"✅ *Campaign Update!*\n\n"
            f"• {units_sold} units sold in first 30 mins 🎉\n"
            f"• ₹{revenue_recovered:,.0f} revenue recovered\n"
            f"• {customers_responded} customers responded\n\n"
            f"Campaign is live! Keep going 🚀"
        )
        return await self.send_text(to, message)

    # ── HTTP ──────────────────────────────────────────

    async def _post(self, payload: dict) -> dict:
        load_dotenv(override=True)
        token = os.getenv("WHATSAPP_TOKEN", "")
        phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
        url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(url, json=payload, headers=headers)
                r.raise_for_status()
                return {"success": True, "response": r.json()}
        except Exception as e:
            print(f"[WhatsApp] Send error: {e}")
            return {"success": False, "error": str(e)}


whatsapp_client = WhatsAppClient()
