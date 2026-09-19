"""
KiranaMate — FastAPI Application Entry Point
"""
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

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

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from db.database import init_db
from api.routes_merchant  import router as merchant_router
from api.routes_campaign  import router as campaign_router
from api.routes_webhook   import router as webhook_router
from api.routes_health    import router as health_router
from api.routes_trace     import router as trace_router

load_dotenv()

# ── Scheduler (replaces N8N cron for local dev) ──────────────────────────────

scheduler = AsyncIOScheduler()

DEMO_MERCHANT = {
    "id":    "11111111-1111-1111-1111-111111111111",
    "phone": os.getenv("DEMO_MERCHANT_PHONE", "917291944074"),
    "name":  "Ramesh",
    "city":  "Delhi",
}


async def hourly_monitor_job():
    """Runs the Sales Monitor agent every hour (via scheduler / N8N)"""
    from agents.sales_monitor import run_monitor
    print(f"[Scheduler] {datetime.utcnow()} — Running hourly sales monitor")
    await run_monitor(
        merchant_id=DEMO_MERCHANT["id"],
        merchant_phone=DEMO_MERCHANT["phone"],
        merchant_name=DEMO_MERCHANT["name"],
    )


async def sunday_report_job():
    """Runs the Weekly Health Report every Sunday at 7 PM IST"""
    from agents.weekly_report import run_weekly_report
    print(f"[Scheduler] {datetime.utcnow()} — Running Sunday health report")
    await run_weekly_report(
        merchant_id=DEMO_MERCHANT["id"],
        merchant_phone=DEMO_MERCHANT["phone"],
        merchant_name=DEMO_MERCHANT["name"],
        merchant_city=DEMO_MERCHANT["city"],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️ Database initialization notice: {e}")

    is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    if not is_serverless:
        # Start tunnel for WhatsApp webhooks in local dev
        try:
            from core.tunnel_manager import start_tunnel
            tunnel_url = start_tunnel(port=int(os.getenv("PORT", 8000)))
            if tunnel_url:
                app.state.tunnel_url = tunnel_url
            else:
                app.state.tunnel_url = None
                print("⚠️  No tunnel started. WhatsApp webhooks may not work.")
        except Exception as e:
            print(f"⚠️ Tunnel manager notice: {e}")

        # Schedule background jobs in local dev
        try:
            scheduler.add_job(hourly_monitor_job, "interval", hours=1, id="hourly_monitor")
            scheduler.add_job(
                sunday_report_job,
                "cron",
                day_of_week="sun",
                hour=13,    # 13:00 UTC = 18:30 IST ≈ 7 PM IST
                minute=30,
                id="weekly_report",
            )
            scheduler.start()
            print("✅ Scheduler started (hourly monitor + Sunday report)")
        except Exception as e:
            print(f"⚠️ Scheduler notice: {e}")
    else:
        vercel_url = os.getenv("VERCEL_URL")
        app.state.tunnel_url = f"https://{vercel_url}" if vercel_url else None

    yield

    # Shutdown
    if not is_serverless:
        try:
            from core.tunnel_manager import stop_tunnel
            stop_tunnel()
        except Exception:
            pass
        try:
            scheduler.shutdown()
        except Exception:
            pass
        print("Scheduler stopped")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="KiranaMate — MerchantMind AI",
    description=(
        "The Autonomous Business Teammate for Every Paytm Merchant.\n\n"
        "Three autonomous agents:\n"
        "- **Sales Monitor**: Hourly anomaly detection → WhatsApp alert\n"
        "- **Campaign Executor**: Voice → campaign in <90s\n"
        "- **Health Reporter**: Sunday 7PM → 0-100 score PDF\n"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(merchant_router,  prefix="/merchant",  tags=["Merchant"])
app.include_router(campaign_router,  prefix="/campaign",  tags=["Campaign"])
app.include_router(webhook_router,   prefix="/webhook",   tags=["Webhooks"])
app.include_router(health_router,    prefix="/report",    tags=["Health Report"])
app.include_router(trace_router,     prefix="/api/trace", tags=["Trace"])
app.include_router(trace_router,     prefix="/trace",     tags=["Trace"])

# ── Serve Hackathon Demo Dashboard & Reports ───────────────────────────────────
import os as _os
from fastapi.responses import FileResponse, RedirectResponse

_dashboard_dir = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "dashboard")
if _os.path.isdir(_dashboard_dir):
    app.mount("/dashboard", StaticFiles(directory=_dashboard_dir, html=True), name="dashboard")
    print(f"Dashboard mounted at /dashboard ({_dashboard_dir})")

is_serverless_runtime = bool(_os.getenv("VERCEL") or _os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
if is_serverless_runtime:
    _reports_dir = "/tmp/reports"
else:
    _reports_dir = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "reports")

try:
    _os.makedirs(_reports_dir, exist_ok=True)
    app.mount("/reports", StaticFiles(directory=_reports_dir), name="reports")
    print(f"Reports mounted at /reports ({_reports_dir})")
except Exception as e:
    print(f"⚠️ Reports directory notice: {e}")


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    """Redirect root visitors directly to the KiranaMate Dashboard UI"""
    return RedirectResponse(url="/dashboard/")


@app.get("/status", tags=["Root"])
async def status_info():
    return {
        "product":    "KiranaMate — MerchantMind AI",
        "version":    "1.0.0",
        "status":     "online",
        "agents":     ["sales_monitor", "campaign_executor", "weekly_report"],
        "docs":       "/docs",
        "hackathon":  "Paytm Build for India AI Hackathon — Delhi Edition",
        "team":       "Epoch",
    }


@app.get("/health", tags=["Root"])
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/tunnel", tags=["Root"])
async def tunnel_status():
    """Shows the current tunnel URL and webhook configuration info."""
    from core.tunnel_manager import get_tunnel_url
    tunnel_url = get_tunnel_url() or getattr(app.state, 'tunnel_url', None)
    webhook_url = f"{tunnel_url}/webhook/whatsapp" if tunnel_url else None
    return {
        "tunnel_url": tunnel_url,
        "webhook_url": webhook_url,
        "verify_token": os.getenv("WHATSAPP_VERIFY_TOKEN", "kiranamate_webhook_verify_2024"),
        "instructions": "Set this webhook_url in Meta Developer Console → WhatsApp → Configuration" if webhook_url else "No tunnel running",
    }


@app.get("/report/download", tags=["Health Report"])
@app.get("/report/pdf", tags=["Health Report"])
async def download_report_pdf():
    pdf_path = _os.path.join(_reports_dir, "KiranaMate_Weekly_Report.pdf")
    if not _os.path.exists(pdf_path):
        from agents.weekly_report import run_weekly_report
        await run_weekly_report(
            merchant_id=DEMO_MERCHANT["id"],
            merchant_phone=DEMO_MERCHANT["phone"],
            merchant_name=DEMO_MERCHANT["name"],
            merchant_city=DEMO_MERCHANT["city"],
        )
    if not _os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF report could not be generated.")
    return FileResponse(pdf_path, media_type="application/pdf", filename="KiranaMate_Weekly_Report.pdf")


# ── Manual Trigger Endpoints (for hackathon demo) ─────────────────────────────

@app.post("/demo/trigger-monitor", tags=["Demo"])
async def trigger_monitor():
    """
    Manually trigger the Sales Monitor (simulates N8N hourly cron).
    Use during demo to show anomaly detection in real-time.
    """
    from agents.sales_monitor import run_monitor
    result = await run_monitor(
        merchant_id=DEMO_MERCHANT["id"],
        merchant_phone=DEMO_MERCHANT["phone"],
        merchant_name=DEMO_MERCHANT["name"],
    )
    return {
        "status":   "completed",
        "anomalies": result.get("anomalies", []),
        "alerts":    result.get("alerts_sent", []),
        "reminders": result.get("reminders_sent", []),
        "trace":     result.get("trace_log", []),
    }


@app.post("/demo/trigger-report", tags=["Demo"])
async def trigger_weekly_report():
    """
    Manually trigger the Sunday Health Report.
    Use during demo to generate a live health score and PDF report.
    """
    from agents.weekly_report import run_weekly_report
    result = await run_weekly_report(
        merchant_id=DEMO_MERCHANT["id"],
        merchant_phone=DEMO_MERCHANT["phone"],
        merchant_name=DEMO_MERCHANT["name"],
        merchant_city=DEMO_MERCHANT["city"],
    )
    return {
        "status":          "completed",
        "health_score":    result.get("health_score"),
        "revenue_trend":   result.get("revenue_trend"),
        "recommendation":  result.get("recommendation"),
        "report_preview":  result.get("report_text", "")[:300],
        "pdf_url":         result.get("pdf_url") or "/reports/KiranaMate_Weekly_Report.pdf",
        "trace":           result.get("trace_log", []),
    }
