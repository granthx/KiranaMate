"""
Webhook Routes
GET  /webhook/whatsapp  — WhatsApp verification handshake
POST /webhook/whatsapp  — Incoming WhatsApp messages (merchant replies)
POST /webhook/paytm     — Paytm transaction events (new sales)
"""
import os
import asyncio
import hmac
import hashlib
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import PlainTextResponse

from agents.campaign_executor import resume_campaign
from core.whatsapp_client import whatsapp_client

router = APIRouter()

WA_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "kiranamate_webhook_verify_2024")


# ── WhatsApp Verification (GET) ───────────────────────────────────────────────

@router.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """
    Meta requires a GET challenge-response to verify the webhook URL.
    Called once when you register the webhook in Meta Business Manager.
    """
    params = dict(request.query_params)
    mode      = params.get("hub.mode")
    token     = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WA_VERIFY_TOKEN:
        print(f"[WhatsApp] Webhook verified ✅")
        return PlainTextResponse(challenge)

    raise HTTPException(status_code=403, detail="Verification token mismatch")


# ── WhatsApp Incoming Messages (POST) ─────────────────────────────────────────

@router.post("/whatsapp")
async def whatsapp_incoming(request: Request):
    """
    Handles incoming WhatsApp messages from the merchant.
    Key flows:
    1. Merchant taps 'Approve' button → resume LangGraph campaign
    2. Merchant taps 'Run Campaign' on anomaly alert → kick off campaign
    3. Merchant taps 'Paid' on khata → mark entry paid
    4. Merchant sends voice note → transcribe + route to campaign
    """
    body = await request.json()

    try:
        entry   = body["entry"][0]
        changes = entry["changes"][0]
        value   = changes["value"]
        messages = value.get("messages", [])

        if not messages:
            return {"status": "no_message"}

        message = messages[0]
        from_   = message.get("from", "")
        msg_type = message.get("type", "")

        print(f"[WhatsApp] Message from {from_}: type={msg_type}")

        # ── Button/Quick Reply ────────────────────────────────────────────────
        if msg_type == "interactive":
            interactive = message.get("interactive", {})
            reply_type  = interactive.get("type")

            if reply_type == "button_reply":
                btn_id = interactive["button_reply"]["id"]
                print(f"[WhatsApp] Button tapped: {btn_id}")

                from core.trace_bus import trace_bus

                # Campaign approval
                if btn_id.startswith("approve_"):
                    trace_bus.emit_wa_msg("sent", "✅ Approve")
                    thread_id = btn_id.replace("approve_", "")
                    asyncio.create_task(resume_campaign(thread_id, "approved"))
                    return {"status": "campaign_approved", "thread_id": thread_id}

                # Campaign cancel
                if btn_id.startswith("cancel_"):
                    trace_bus.emit_wa_msg("sent", "❌ Cancel")
                    thread_id = btn_id.replace("cancel_", "")
                    asyncio.create_task(resume_campaign(thread_id, "cancelled"))
                    return {"status": "campaign_cancelled", "thread_id": thread_id}

                # Anomaly → run clearance
                if btn_id == "run_clearance":
                    trace_bus.emit_wa_msg("sent", "✅ Run Campaign")
                    import uuid
                    from agents.campaign_executor import run_campaign
                    thread_id = f"camp_{uuid.uuid4().hex[:12]}"
                    initial   = {
                        "merchant_id":    "11111111-1111-1111-1111-111111111111",
                        "merchant_phone": from_,
                        "merchant_name":  "Ramesh",
                        "merchant_city":  "Delhi",
                        "merchant_upi":   "sharma.store@paytm",
                        "raw_input":      "dairy items expiring, run clearance campaign",
                        "skus_found":     [],
                        "total_units":    0,
                        "wa_messages":    [],
                        "target_customers": [],
                        "alerts_sent":    [],
                        "trace_log":      [],
                    }
                    asyncio.create_task(run_campaign(initial, thread_id))
                    return {"status": "campaign_started", "thread_id": thread_id}

                # View anomaly details
                if btn_id == "view_details":
                    trace_bus.emit_wa_msg("sent", "📊 Details")
                    asyncio.create_task(_send_anomaly_details(from_))
                    return {"status": "details_sent"}

                # Ignore anomaly alert
                if btn_id == "ignore_alert":
                    trace_bus.emit_wa_msg("sent", "❌ Ignore")
                    await whatsapp_client.send_text(
                        from_,
                        "👍 Alert acknowledged. Main monitor karta rahunga aur agar zaroorat padi toh dobara alert bhejunga."
                    )
                    return {"status": "alert_ignored"}

                # Khata paid acknowledgement
                if btn_id == "paid_khata":
                    # TODO: match customer phone to khata and mark paid
                    return {"status": "khata_paid_ack"}

        # ── Voice Note ────────────────────────────────────────────────────────
        elif msg_type in ("audio", "voice"):
            audio_obj = message.get("audio") or message.get("voice") or {}
            audio_id = audio_obj.get("id")
            mime_type = audio_obj.get("mime_type", "audio/ogg")
            audio_format = "ogg"
            if "mp4" in mime_type or "m4a" in mime_type:
                audio_format = "mp4"
            elif "wav" in mime_type:
                audio_format = "wav"
            elif "mp3" in mime_type:
                audio_format = "mp3"

            print(f"[WhatsApp] Voice note received from {from_}: id={audio_id}, mime={mime_type}")
            if not audio_id:
                return {"status": "no_audio_id"}

            audio_url = await _get_media_url(audio_id)
            if not audio_url:
                print(f"[WhatsApp] Could not fetch media URL for {audio_id}")
                return {"status": "media_url_failed"}

            audio_bytes = await _download_media(audio_url)
            if not audio_bytes:
                print(f"[WhatsApp] Failed to download audio content")
                return {"status": "audio_download_failed"}

            from core.sarvam_client import sarvam_client
            transcript_dict = await sarvam_client.transcribe_audio(audio_bytes, language_hint="hi-IN", audio_format=audio_format)
            raw_text = transcript_dict.get("transcript", "").strip()
            print(f"[WhatsApp] Voice note transcribed: '{raw_text}'")

            return await _handle_merchant_message(from_, raw_text, is_voice=True)

        # ── Text Message ──────────────────────────────────────────────────────
        elif msg_type == "text":
            raw_text = message.get("text", {}).get("body", "")
            return await _handle_merchant_message(from_, raw_text, is_voice=False)

    except (KeyError, IndexError) as e:
        print(f"[WhatsApp] Parse error: {e}")

    return {"status": "ok"}


async def _send_anomaly_details(to: str, prefix: str = "") -> dict:
    """Fetches latest open or recent anomalies and sends a formatted breakdown to WhatsApp."""
    from db.database import AsyncSessionLocal
    from db.models import Anomaly
    from sqlalchemy import select

    merchant_id = "11111111-1111-1111-1111-111111111111"
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Anomaly)
            .where(Anomaly.merchant_id == merchant_id)
            .order_by(Anomaly.detected_at.desc())
            .limit(5)
        )
        anomalies = result.scalars().all()

    if anomalies:
        lines = [f"{prefix}📊 *Anomaly Details — Ramesh Store*\n"]
        for i, a in enumerate(anomalies, 1):
            severity_emoji = "🔴" if a.severity == "CRITICAL" else "🟡" if a.severity == "WARNING" else "🟢"
            cat_name = a.category.replace('_', ' ').title() if a.category else "General"
            lines.append(
                f"{i}. {severity_emoji} *{cat_name}* — {a.severity}\n"
                f"   📉 Down *{abs(a.deviation_pct):.0f}%* vs baseline\n"
                f"   Expected: ₹{a.expected_rev:,.0f} | Actual: ₹{a.actual_rev:,.0f}\n"
                f"   Gap: *₹{(a.expected_rev - a.actual_rev):,.0f}*\n"
                f"   🕐 {a.detected_at.strftime('%d %b %Y, %I:%M %p') if a.detected_at else 'N/A'}\n"
            )
        lines.append("💡 _Tap 'Run Campaign' or reply 'dairy sale' to launch a clearance campaign!_")
        detail_msg = "\n".join(lines)
    else:
        detail_msg = (
            f"{prefix}📊 *Anomaly Details*\n\n"
            "No active anomalies found right now.\n"
            "Sab kuch normal chal raha hai! ✅"
        )

    await whatsapp_client.send_text(to, detail_msg)
    return {"status": "details_sent"}


async def _handle_merchant_message(from_: str, raw_text: str, is_voice: bool = False) -> dict:
    """
    Unified intent router for incoming text and voice messages from the merchant.
    """
    from core.trace_bus import trace_bus

    # Show the incoming WhatsApp bubble on dashboard immediately
    bubble_text = f"🎙️ {raw_text}" if is_voice else raw_text
    trace_bus.emit_wa_msg("sent", bubble_text)

    text = raw_text.lower().strip()

    # If voice note was silent or unparseable
    if is_voice and not text:
        await whatsapp_client.send_text(
            from_,
            "Namaste Ramesh ji! 🙏 Aapka voice note mila, par awaaz clearly recognize nahi ho paayi.\n\n"
            "Kripya thoda saaf bole ya text me likh kar bhejein! 👍"
        )
        return {"status": "voice_unrecognized"}

    # 1. Campaign trigger (sale, clearance, expiry, etc.)
    if any(kw in text for kw in ["sale", "clearance", "expiry", "expire", "campaign", "offer", "discount", "khatam", "bhai", "nikal"]):
        import uuid
        from agents.campaign_executor import run_campaign
        thread_id = f"camp_{uuid.uuid4().hex[:12]}"
        initial = {
            "merchant_id":     "11111111-1111-1111-1111-111111111111",
            "merchant_phone":  from_,
            "merchant_name":   "Ramesh",
            "merchant_city":   "Delhi",
            "merchant_upi":    "sharma.store@paytm",
            "raw_input":       raw_text,
            "skus_found":      [],
            "total_units":     0,
            "wa_messages":     [],
            "target_customers":[],
            "alerts_sent":     [],
            "trace_log":       [],
        }
        prefix = f"🎙️ *Voice Note: \"{raw_text}\"*\n\n" if is_voice else ""
        async def _run_camp():
            await whatsapp_client.send_text(from_, f"{prefix}🚀 Bilkul Ramesh ji! Main turant campaign prepare kar raha hoon: '{raw_text}'...")
            await run_campaign(initial, thread_id)
        asyncio.create_task(_run_camp())
        return {"status": "campaign_started", "thread_id": thread_id, "is_voice": is_voice}

    # 2. Health Report request
    elif any(kw in text for kw in ["report", "health", "score", "pdf"]):
        prefix = f"🎙️ *Voice Note: \"{raw_text}\"*\n\n" if is_voice else ""
        async def _run_rep():
            await whatsapp_client.send_text(from_, f"{prefix}📊 Aapki Weekly Health Report & PDF generate ho rahi hai, ek minute...")
            from agents.weekly_report import run_weekly_report
            await run_weekly_report(
                merchant_id="11111111-1111-1111-1111-111111111111",
                merchant_phone=from_,
                merchant_name="Ramesh",
                merchant_city="Delhi",
            )
        asyncio.create_task(_run_rep())
        return {"status": "report_started", "is_voice": is_voice}

    # 3. Today's sales status
    elif any(kw in text for kw in ["status", "sales", "bikri", "aaj", "earning", "kamai", "collection"]):
        async def _do_status():
            trace_bus.emit_agent_start("monitor", "Checking Today's Sales Status")
            from db.database import AsyncSessionLocal
            from db.models import Transaction
            from sqlalchemy import select, func
            from datetime import datetime
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(func.sum(Transaction.amount), func.count(Transaction.id))
                    .where(Transaction.merchant_id == "11111111-1111-1111-1111-111111111111", Transaction.txn_time >= today_start)
                )
                row = res.first()
                tot = row[0] or 0
                cnt = row[1] or 0

            p = f"🎙️ *Voice Note: \"{raw_text}\"*\n\n" if is_voice else ""
            await whatsapp_client.send_text(
                from_,
                f"{p}📈 *Aaj Ki Store Update (Ramesh Store):*\n\n"
                f"• Aaj ki Bikri: *₹{tot:,.0f}*\n"
                f"• Total Transactions: *{cnt}*\n\n"
                f"Dukaan badhiya chal rahi hai! 👍"
            )
            trace_bus.emit_agent_finish("monitor", "done", {"sales": tot, "transactions": cnt})
        asyncio.create_task(_do_status())
        return {"status": "status_started", "is_voice": is_voice}

    # 4. Anomaly / Alert Details
    elif any(kw in text for kw in ["detail", "details", "anomaly", "anomalies", "alert", "gadbad"]):
        async def _do_details():
            trace_bus.emit_agent_start("monitor", "Fetching Anomaly Breakdown")
            p = f"🎙️ *Voice Note: \"{raw_text}\"*\n\n" if is_voice else ""
            await _send_anomaly_details(from_, prefix=p)
            trace_bus.emit_agent_finish("monitor", "done")
        asyncio.create_task(_do_details())
        return {"status": "details_started", "is_voice": is_voice}

    # 5. Greetings (Namaste, Hi, Hello) and general interactive AI response
    else:
        voice_heard = f"🎙️ *Voice Command Suna:* \"{raw_text}\"\n\n" if is_voice else ""
        reply = (
            f"{voice_heard}Namaste Ramesh ji! 🙏 Main *KiranaMate AI* hoon, aapka 24/7 business teammate.\n\n"
            "Aap mujhse WhatsApp par bol kar ya likh kar commands de sakte hain:\n"
            "• 📢 *'Dairy items expire hone wale hain, sale chalao'*\n"
            "• 📊 *'Report'* (Weekly Health Report + PDF bhejega)\n"
            "• 💰 *'Status'* (Aaj ki bikri check karega)\n"
            "• 🎙️ *Voice Note* (Aap vernacular Hindi/Hinglish me bol sakte hain!)\n\n"
            "Bataiye, aaj kis item par focus karna hai?"
        )
        asyncio.create_task(whatsapp_client.send_text(from_, reply))
        return {"status": "greeting_delivered", "is_voice": is_voice}


# ── Paytm Transaction Webhook (POST) ──────────────────────────────────────────

@router.post("/paytm")
async def paytm_transaction_webhook(request: Request):
    """
    Receives real-time transaction events from Paytm Soundbox / QR.
    Stores in DB for anomaly detection.
    """
    body = await request.json()

    try:
        txn_id     = body.get("TXNID")
        amount     = float(body.get("TXNAMOUNT", 0))
        status     = body.get("STATUS")
        merchant_id = "11111111-1111-1111-1111-111111111111"

        if status != "TXN_SUCCESS":
            return {"status": "ignored", "reason": "non-success transaction"}

        from db.database import AsyncSessionLocal
        from db.models import Transaction
        from datetime import datetime

        async with AsyncSessionLocal() as db:
            txn = Transaction(
                merchant_id=merchant_id,
                txn_id=txn_id,
                amount=amount,
                category=_infer_category(body),
                payment_mode="upi",
                txn_time=datetime.utcnow(),
            )
            db.add(txn)
            await db.commit()

        return {"status": "recorded", "txn_id": txn_id, "amount": amount}

    except Exception as e:
        print(f"[Paytm Webhook] Error: {e}")
        return {"status": "error", "detail": str(e)}


def _infer_category(txn: dict) -> str:
    """Infer product category from Paytm transaction metadata"""
    desc = (txn.get("ORDERID", "") + txn.get("MERC_UNQ_REF", "")).lower()
    if any(w in desc for w in ["milk", "dairy", "paneer", "curd", "butter"]):
        return "dairy"
    if any(w in desc for w in ["chips", "snack", "maggi", "biscuit"]):
        return "snacks"
    if any(w in desc for w in ["rice", "atta", "dal", "salt", "oil"]):
        return "staples"
    return "misc"


async def _get_media_url(media_id: str) -> str:
    import httpx, os
    from dotenv import load_dotenv
    load_dotenv(override=True)
    token = os.getenv("WHATSAPP_TOKEN", "")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"https://graph.facebook.com/v19.0/{media_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        return r.json().get("url", "")


async def _download_media(url: str) -> bytes:
    import httpx, os
    from dotenv import load_dotenv
    load_dotenv(override=True)
    token = os.getenv("WHATSAPP_TOKEN", "")
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        return r.content
