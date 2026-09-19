"""
Tunnel Manager for KiranaMate
Automatically starts a tunnel and registers the webhook URL with Meta.
This eliminates manual webhook URL updates when the tunnel URL changes.
"""
import os
import sys
import asyncio
import threading
import httpx
from typing import Optional
from dotenv import load_dotenv

# Fix Windows console encoding for Unicode/emojis
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

# Global state
_tunnel_url: Optional[str] = None
_tunnel_lock = threading.Lock()


def get_tunnel_url() -> Optional[str]:
    """Get the current public tunnel URL."""
    return _tunnel_url


def register_webhook_with_meta(tunnel_url: str) -> bool:
    """
    Programmatically update Meta's webhook subscription to point to the current tunnel.
    Uses an app access token (app_id|app_secret) to call the subscriptions API.
    Returns True on success.
    """
    load_dotenv(override=True)
    app_id = os.getenv("META_APP_ID", "")
    app_secret = os.getenv("META_APP_SECRET", "")
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "kiranamate_webhook_verify_2024")

    if not app_id or not app_secret:
        print("[Tunnel] ⚠️  META_APP_ID or META_APP_SECRET not set. Cannot auto-register webhook.")
        return False

    app_access_token = f"{app_id}|{app_secret}"
    webhook_url = f"{tunnel_url}/webhook/whatsapp"

    print(f"[Tunnel] Registering webhook with Meta: {webhook_url}")

    try:
        r = httpx.post(
            f"https://graph.facebook.com/v19.0/{app_id}/subscriptions",
            data={
                "access_token": app_access_token,
                "object": "whatsapp_business_account",
                "callback_url": webhook_url,
                "verify_token": verify_token,
                "fields": "messages",
            },
            timeout=15,
        )

        if r.status_code == 200 and r.json().get("success"):
            print(f"[Tunnel] ✅ Meta webhook registered: {webhook_url}")
            
            # Also subscribe the WABA (WhatsApp Business Account) to the app
            waba_id = os.getenv("WHATSAPP_WABA_ID", "")
            wa_token = os.getenv("WHATSAPP_TOKEN", "")
            if waba_id and wa_token:
                try:
                    waba_r = httpx.post(
                        f"https://graph.facebook.com/v19.0/{waba_id}/subscribed_apps",
                        params={"access_token": wa_token},
                        timeout=15,
                    )
                    if waba_r.status_code == 200 and waba_r.json().get("success"):
                        print(f"[Tunnel] ✅ WABA {waba_id} subscribed to KiranaMate app")
                    else:
                        print(f"[Tunnel] ⚠️ WABA subscription warning: {waba_r.text}")
                except Exception as ex:
                    print(f"[Tunnel] ⚠️ WABA subscription error: {ex}")

            return True
        else:
            print(f"[Tunnel] ❌ Meta webhook registration failed: {r.status_code} {r.text[:300]}")
            return False

    except Exception as e:
        print(f"[Tunnel] ❌ Meta webhook registration error: {e}")
        return False


def start_tunnel(port: int = 8000) -> Optional[str]:
    """
    Start a localtunnel on the given port and auto-register the webhook with Meta.
    Returns the public HTTPS URL or None on failure.
    """
    global _tunnel_url

    load_dotenv(override=True)
    custom_url = os.getenv("TUNNEL_URL", "").strip().rstrip("/")
    if custom_url:
        with _tunnel_lock:
            _tunnel_url = custom_url
        print(f"✅ Using configured tunnel URL: {custom_url}")
        register_webhook_with_meta(custom_url)
        return custom_url

    # Try ngrok first (no interstitial page, most reliable for webhooks)
    try:
        from pyngrok import ngrok, conf

        # Kill any existing tunnels
        try:
            ngrok.kill()
        except Exception:
            pass

        # Start tunnel
        tunnel = ngrok.connect(port, "http")
        url = tunnel.public_url

        # Ensure HTTPS
        if url.startswith("http://"):
            url = url.replace("http://", "https://")

        with _tunnel_lock:
            _tunnel_url = url

        print(f"✅ Ngrok tunnel started: {url}")

        # Auto-register with Meta
        register_webhook_with_meta(url)
        return url

    except Exception as e:
        print(f"[Tunnel] Ngrok unavailable ({type(e).__name__}), using localtunnel...")

    # Fallback: localtunnel via subprocess
    try:
        import subprocess
        import time

        proc = subprocess.Popen(
            ["npx", "-y", "localtunnel", "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
        )

        # Read the URL from stdout (with timeout)
        line = ""
        for _ in range(30):  # Wait up to 30 seconds
            line = proc.stdout.readline().strip()
            if line:
                break
            time.sleep(1)

        if "your url is:" in line.lower():
            url = line.split("your url is:")[-1].strip()
            with _tunnel_lock:
                _tunnel_url = url
            print(f"✅ Localtunnel started: {url}")

            # Auto-register with Meta
            register_webhook_with_meta(url)
            return url
        else:
            print(f"[Tunnel] Unexpected localtunnel output: {line}")

    except Exception as e:
        print(f"[Tunnel] Localtunnel also failed: {e}")

    return None


def stop_tunnel():
    """Stop the running tunnel."""
    global _tunnel_url
    try:
        from pyngrok import ngrok
        ngrok.kill()
    except Exception:
        pass
    with _tunnel_lock:
        _tunnel_url = None
    print("[Tunnel] Stopped")
