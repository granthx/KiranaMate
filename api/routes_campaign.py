"""
Campaign Executor API Routes
POST /campaign/voice  — Voice note → full campaign
POST /campaign/text   — Text goal → full campaign
POST /campaign/approve/{campaign_id} — Resume after approval
GET  /campaign/{campaign_id} — Status check
"""
import uuid
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import Optional

from agents.campaign_executor import run_campaign, resume_campaign
from core.sarvam_client import sarvam_client

router = APIRouter()

DEMO_MERCHANT = {
    "id":    "11111111-1111-1111-1111-111111111111",
    "phone": os.getenv("DEMO_MERCHANT_PHONE", "917291944074"),
    "name":  "Ramesh",
    "city":  "Delhi",
    "upi":   "sharma.store@paytm",
}


class TextCampaignRequest(BaseModel):
    merchant_id: Optional[str] = None
    goal: str     # e.g. "Dairy expiring in 3 days, run clearance"
    language: Optional[str] = "hi"


@router.post("/voice")
async def campaign_from_voice(
    audio: UploadFile = File(...),
    merchant_id: Optional[str] = Form(None),
    language: Optional[str] = Form("hi-IN"),
):
    """
    Scenario 1: Accepts a WhatsApp voice note (OGG/MP4),
    transcribes it with Sarvam AI, and kicks off the campaign agent.

    Returns immediately with a thread_id.
    Campaign pauses at ApprovalGate and resumes via /campaign/approve/{id}.
    """
    audio_bytes = await audio.read()

    # Step 1: Transcribe
    transcription = await sarvam_client.transcribe_audio(
        audio_bytes=audio_bytes,
        language_hint=language,
        audio_format=audio.filename.split(".")[-1] if audio.filename else "ogg",
    )

    if not transcription.get("transcript"):
        raise HTTPException(status_code=422, detail="Could not transcribe audio. Please try again.")

    transcript = transcription["transcript"]
    thread_id  = f"camp_{uuid.uuid4().hex[:12]}"
    mid        = merchant_id or DEMO_MERCHANT["id"]

    # Step 2: Run agent (will pause at approval gate)
    initial_state = {
        "merchant_id":     mid,
        "merchant_phone":  DEMO_MERCHANT["phone"],
        "merchant_name":   DEMO_MERCHANT["name"],
        "merchant_city":   DEMO_MERCHANT["city"],
        "merchant_upi":    DEMO_MERCHANT["upi"],
        "raw_input":       transcript,
        "skus_found":      [],
        "total_units":     0,
        "wa_messages":     [],
        "target_customers":[],
        "alerts_sent":     [],
        "trace_log":       [],
    }

    result = await run_campaign(initial_state, thread_id)

    return {
        "status":      result.get("status", "running"),
        "thread_id":   thread_id,
        "transcript":  transcript,
        "language":    transcription.get("language_detected"),
        "provider":    transcription.get("provider"),
        "message":     result.get("message", ""),
        "trace":       result.get("trace_log", []),
    }


@router.post("/text")
async def campaign_from_text(req: TextCampaignRequest):
    """
    Scenario 1 (text input variant):
    Accepts a text goal directly and kicks off the campaign agent.
    Useful for testing without audio.
    """
    thread_id = f"camp_{uuid.uuid4().hex[:12]}"
    mid       = req.merchant_id or DEMO_MERCHANT["id"]

    initial_state = {
        "merchant_id":     mid,
        "merchant_phone":  DEMO_MERCHANT["phone"],
        "merchant_name":   DEMO_MERCHANT["name"],
        "merchant_city":   DEMO_MERCHANT["city"],
        "merchant_upi":    DEMO_MERCHANT["upi"],
        "raw_input":       req.goal,
        "skus_found":      [],
        "total_units":     0,
        "wa_messages":     [],
        "target_customers":[],
        "alerts_sent":     [],
        "trace_log":       [],
    }

    result = await run_campaign(initial_state, thread_id)

    return {
        "status":    result.get("status", "running"),
        "thread_id": thread_id,
        "goal":      req.goal,
        "message":   result.get("message", ""),
        "trace":     result.get("trace_log", []),
    }


@router.post("/approve/{thread_id}")
async def approve_campaign(thread_id: str):
    """
    Called by WhatsApp webhook when merchant taps 'Approve'.
    Resumes the paused LangGraph and executes the campaign.
    """
    result = await resume_campaign(thread_id, approval_status="approved")
    return {
        "status":           "completed",
        "thread_id":        thread_id,
        "execution_result": result.get("execution_result", {}),
        "trace":            result.get("trace_log", []),
    }


@router.post("/cancel/{thread_id}")
async def cancel_campaign(thread_id: str):
    """Called when merchant taps 'Cancel' on WhatsApp"""
    result = await resume_campaign(thread_id, approval_status="cancelled")
    return {"status": "cancelled", "thread_id": thread_id}
