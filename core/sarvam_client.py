"""
Sarvam AI Voice Transcription Client
Handles vernacular Indian language voice notes from WhatsApp
Supports: Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Punjabi
"""
import os
import httpx
import base64
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY  = os.getenv("SARVAM_API_KEY", "")
SARVAM_BASE_URL = "https://api.sarvam.ai"

# Fallback to OpenAI Whisper if Sarvam key not available
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")


class SarvamClient:
    """
    Transcribes WhatsApp voice notes (OGG/MP4) to text.
    Prioritises Sarvam AI for Indian language accuracy.
    Falls back to OpenAI Whisper.
    """

    def __init__(self):
        self.sarvam_key = SARVAM_API_KEY
        self.openai_key = OPENAI_API_KEY

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        language_hint: str = "hi-IN",
        audio_format: str = "ogg",
    ) -> dict:
        """
        Transcribes audio bytes → structured goal dict.

        Returns:
        {
            "transcript": "Dairy items expiring in 3 days, run clearance",
            "language_detected": "hi",
            "confidence": 0.94,
            "provider": "sarvam"
        }
        """
        load_dotenv(override=True)
        sarvam_key = os.getenv("SARVAM_API_KEY", self.sarvam_key)
        if sarvam_key:
            result = await self._transcribe_sarvam(audio_bytes, language_hint, audio_format)
            if result and "transcript" in result:
                return result

        # Fallback to Whisper only if valid OpenAI key is set
        openai_key = os.getenv("OPENAI_API_KEY", self.openai_key)
        if openai_key and not openai_key.startswith("your_openai"):
            return await self._transcribe_whisper(audio_bytes, audio_format)

        return {"transcript": "", "error": "No transcription available"}

    async def _transcribe_sarvam(
        self,
        audio_bytes: bytes,
        language: str,
        audio_format: str,
    ) -> dict:
        """Sarvam AI — optimized for Indian vernacular speech (saaras:v3)"""
        try:
            load_dotenv(override=True)
            sarvam_key = os.getenv("SARVAM_API_KEY", self.sarvam_key)
            ext = audio_format.lower()
            if ext in ("ogg", "opus"):
                mime_type = "audio/ogg"
                filename = "voice.ogg"
            elif ext == "mp4":
                mime_type = "audio/mp4"
                filename = "voice.mp4"
            elif ext == "wav":
                mime_type = "audio/wav"
                filename = "voice.wav"
            else:
                mime_type = f"audio/{ext}"
                filename = f"voice.{ext}"

            files = {
                "file": (filename, audio_bytes, mime_type)
            }
            data = {
                "model": "saaras:v3"
            }
            if language and language != "unknown":
                data["language_code"] = language

            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{SARVAM_BASE_URL}/speech-to-text",
                    files=files,
                    data=data,
                    headers={
                        "api-subscription-key": sarvam_key,
                    },
                )
                r.raise_for_status()
                res = r.json()
                transcript = res.get("transcript", "").strip()
                lang = res.get("language_code", language or "hi")
                prob = res.get("language_probability", 0.9)
                return {
                    "transcript": transcript,
                    "language_detected": str(lang).split("-")[0],
                    "confidence": prob,
                    "provider": "sarvam",
                }
        except Exception as e:
            print(f"[Sarvam] Transcription error: {e}")
            return {}

    async def _transcribe_whisper(
        self,
        audio_bytes: bytes,
        audio_format: str,
    ) -> dict:
        """OpenAI Whisper fallback"""
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.openai_key)

            # Write bytes to a temp-like object
            import io
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"voice.{audio_format}"

            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="hi",  # hint for Hindi
                response_format="verbose_json",
            )
            return {
                "transcript": response.text,
                "language_detected": response.language,
                "confidence": 0.85,
                "provider": "whisper",
            }
        except Exception as e:
            print(f"[Whisper] Transcription error: {e}")
            return {"transcript": "", "error": str(e)}

    async def parse_merchant_goal(self, transcript: str, llm_client) -> dict:
        """
        Uses the LLM to parse a free-form transcript into structured JSON.

        Input:  "Dairy items wale 100 units hain jo 3 din mein expire ho rahe hain, sale karo"
        Output: {
            "intent": "clearance_campaign",
            "category": "dairy",
            "quantity": 100,
            "deadline_days": 3,
            "confidence": 0.95
        }
        """
        prompt = f"""
You are a parser for an Indian Kirana store AI assistant.
Parse the following merchant voice command into structured JSON.

Voice command: "{transcript}"

Return ONLY valid JSON with these fields:
{{
    "intent": one of ["clearance_campaign", "check_inventory", "khata_reminder", "sales_query", "reorder", "unknown"],
    "category": product category if mentioned (dairy/snacks/staples/beverages/personal_care/all),
    "quantity": number of units if mentioned (null if not),
    "deadline_days": days mentioned for urgency (null if not),
    "discount_hint": percentage if merchant mentioned a specific discount (null if not),
    "customer_name": customer name if this is a khata query (null if not),
    "confidence": 0.0-1.0,
    "raw_transcript": the original transcript
}}
"""
        response = await llm_client.generate(prompt)
        try:
            import json
            return json.loads(response)
        except Exception:
            return {
                "intent": "unknown",
                "raw_transcript": transcript,
                "confidence": 0.0,
            }


sarvam_client = SarvamClient()
