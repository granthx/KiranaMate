# KiranaMate — MerchantMind AI
## Complete Setup & Integration Guide
### For: Anti Gravity Team Handoff

> This document covers every step needed to get KiranaMate running end-to-end.
> Sections marked **[ANTI GRAVITY]** are tasks for the Anti Gravity team to handle.
> Sections marked **[YOU]** are things you do yourself (website/app logins, API signups).

---

## TABLE OF CONTENTS

1. [What You Are Building](#1-what-you-are-building)
2. [API Keys — Where to Get Each One](#2-api-keys--where-to-get-each-one)
3. [Environment File Setup](#3-environment-file-setup)
4. [Running the Backend](#4-running-the-backend)
5. [Database Setup & Seed Data](#5-database-setup--seed-data)
6. [N8N Workflow Setup — Step by Step](#6-n8n-workflow-setup--step-by-step)
7. [WhatsApp Business API Setup](#7-whatsapp-business-api-setup)
8. [Cognee Knowledge Graph Setup](#8-cognee-knowledge-graph-setup)
9. [Sarvam AI Voice Setup](#9-sarvam-ai-voice-setup)
10. [Paytm Business API Setup](#10-paytm-business-api-setup)
11. [What Anti Gravity Needs to Build/Configure](#11-what-anti-gravity-needs-to-buildconfigure)
12. [Demo Flow — How to Run All 3 Scenarios](#12-demo-flow--how-to-run-all-3-scenarios)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. WHAT YOU ARE BUILDING

KiranaMate has **3 autonomous agents** that run independently:

| Agent | Trigger | What It Does |
|---|---|---|
| **Sales Monitor** | Every hour (N8N cron) | Detects sales drops → sends WhatsApp alert |
| **Campaign Executor** | Merchant voice note on WhatsApp | Transcribes → finds stock → prices → blasts campaign |
| **Weekly Report** | Every Sunday 7 PM (N8N cron) | Generates 0-100 health score → sends PDF on WhatsApp |

**Tech Stack:**
- **Backend:** Python + FastAPI (your codebase)
- **Agent Brain:** LangGraph (multi-step AI agent graphs)
- **LLM:** Gemini 1.5 Pro (primary) + OpenAI GPT-4o (fallback)
- **Memory:** Cognee Knowledge Graph
- **Voice:** Sarvam AI (Indian languages)
- **Automation:** N8N (cron jobs + webhook routing)
- **Messaging:** Meta WhatsApp Business API
- **Pricing Intel:** Serper AI (Google Shopping scraper)
- **Payments:** Paytm Business API
- **Database:** PostgreSQL
- **State Store:** Redis (LangGraph pause/resume)

---

## 2. API KEYS — WHERE TO GET EACH ONE

### 2.1 Gemini API Key (PRIMARY LLM)
**[YOU]**
1. Go to: **https://aistudio.google.com/app/apikey**
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key — it starts with `AIza...`
5. Paste into `.env` as `GEMINI_API_KEY=AIza...`

> Free tier: 60 requests/min. Enough for hackathon demo.

---

### 2.2 OpenAI API Key (Fallback LLM + DALL-E posters + Whisper)
**[YOU]**
1. Go to: **https://platform.openai.com/api-keys**
2. Sign in or create an account
3. Click **"+ Create new secret key"**
4. Name it `kiranamate` and copy the key — starts with `sk-...`
5. Paste into `.env` as `OPENAI_API_KEY=sk-...`
6. Add a minimum **$5 credit** at https://platform.openai.com/settings/organization/billing

> Used for: Whisper voice transcription fallback, DALL-E promotional poster generation, GPT-4o fallback reasoning.

---

### 2.3 Sarvam AI Key (Indian Language Voice)
**[YOU]**
1. Go to: **https://www.sarvam.ai/**
2. Click **"Get API Access"** or **"Sign Up"**
3. Fill the form — mention you are building for a hackathon
4. You will get an email with your API key
5. Paste into `.env` as `SARVAM_API_KEY=your_key`

> Sarvam supports: Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Punjabi.
> This is what transcribes the merchant's WhatsApp voice notes into text.

---

### 2.4 Cognee API Key (Knowledge Graph / Memory)
**[YOU]**
1. Go to: **https://www.cognee.ai/**
2. Click **"Get Started"** or **"Sign Up"**
3. Create an account
4. Go to **Settings → API Keys**
5. Generate a new key and copy it
6. Paste into `.env` as `COGNEE_API_KEY=your_key`

> Cognee is what gives the agent "memory" — it remembers which discounts worked, customer warmth scores, margin floors, past campaign outcomes. This is the "Compounding Moat."

---

### 2.5 Serper AI Key (Competitor Price Intelligence)
**[YOU]**
1. Go to: **https://serper.dev/**
2. Click **"Get Started Free"**
3. Sign up with Google or email
4. Your API key is shown immediately on the dashboard
5. Paste into `.env` as `SERPER_API_KEY=your_key`

> Free tier: 2,500 searches/month — plenty for demo.
> Used to scrape Google Shopping for local competitor prices before recommending a discount.

---

### 2.6 Stability AI Key (Promo Poster Generation)
**[YOU]**
1. Go to: **https://platform.stability.ai/**
2. Click **"Sign Up"**
3. After login, go to **Account → API Keys**
4. Click **"Create API Key"**
5. Paste into `.env` as `STABILITY_API_KEY=your_key`

> Free credits given on signup. Used to generate promotional posters (Stable Diffusion 3.5).
> If this doesn't work, the system automatically falls back to DALL-E (OpenAI).

---

### 2.7 Meta WhatsApp Business API
**[YOU + ANTI GRAVITY]** — This is the most involved setup.

#### Step 1: Create a Meta Developer Account
1. Go to: **https://developers.facebook.com/**
2. Log in with a Facebook account
3. Click **"My Apps"** → **"Create App"**
4. Select **"Business"** type
5. Name it `KiranaMate`

#### Step 2: Add WhatsApp Product
1. In your app dashboard, scroll down to find **"WhatsApp"**
2. Click **"Set Up"**
3. You will land on the WhatsApp Getting Started page

#### Step 3: Get Your Credentials
1. Under **"Step 1: Select phone numbers"**, you will see a **Test number** already provided by Meta (free to use for testing)
2. Copy:
   - **Phone Number ID** → paste as `WHATSAPP_PHONE_ID=` in `.env`
   - **Access Token (temporary)** → paste as `WHATSAPP_TOKEN=` in `.env`
3. For production: generate a **permanent token** via Meta Business Manager → System Users

#### Step 4: Add a Test Recipient
1. In the same page, under **"Step 2: Send messages with the API"**
2. In the **"To"** dropdown, click **"Manage phone number list"**
3. Add the merchant's phone number (must be a real WhatsApp number)
4. They will receive a verification code on WhatsApp — enter it

#### Step 5: Register Webhook (Do AFTER backend is running)
→ **See Section 6 (N8N) and Section 7 for webhook registration steps**

---

### 2.8 Paytm Business API
**[YOU]**
1. Go to: **https://business.paytm.com/**
2. Log in with your Paytm merchant account
3. Go to **Developer Settings → API Keys**
4. Copy:
   - **Merchant ID (MID)** → paste as `PAYTM_MERCHANT_ID=` in `.env`
   - **Merchant Key** → paste as `PAYTM_MERCHANT_KEY=` in `.env`
5. For testing, use **Staging environment**: set `PAYTM_ENVIRONMENT=staging` in `.env`

> For the hackathon demo, the Paytm integration has a **mock fallback** built in — even if the real API isn't set up, the demo will work and show "catalog updated" messages.

---

## 3. ENVIRONMENT FILE SETUP

**[YOU]** After collecting all keys above:

1. Open the project folder
2. Copy the example file:
   ```bash
   cp .env.example .env
   ```
3. Open `.env` in any text editor and fill in every value:

```env
# ── LLM ──────────────────────────────────────
GEMINI_API_KEY=AIza...your_key_here
OPENAI_API_KEY=sk-...your_key_here

# ── VOICE ─────────────────────────────────────
SARVAM_API_KEY=your_sarvam_key

# ── MEMORY ────────────────────────────────────
COGNEE_API_KEY=your_cognee_key

# ── COMPETITOR PRICING ────────────────────────
SERPER_API_KEY=your_serper_key

# ── WHATSAPP ──────────────────────────────────
WHATSAPP_TOKEN=EAAxxxxxxx...
WHATSAPP_PHONE_ID=1234567890
WHATSAPP_VERIFY_TOKEN=kiranamate_webhook_verify_2024

# ── PAYTM ─────────────────────────────────────
PAYTM_MERCHANT_KEY=your_paytm_key
PAYTM_MERCHANT_ID=your_merchant_id
PAYTM_ENVIRONMENT=staging

# ── DATABASE ──────────────────────────────────
DATABASE_URL=postgresql+asyncpg://kiranamate:kiranamate123@localhost:5432/kiranamate

# ── REDIS ─────────────────────────────────────
REDIS_URL=redis://localhost:6379

# ── IMAGE GENERATION ──────────────────────────
STABILITY_API_KEY=your_stability_key

# ── APP ───────────────────────────────────────
SECRET_KEY=make_this_any_random_long_string
DEBUG=true
PORT=8000
```

> **Do NOT share the `.env` file publicly or push it to GitHub.**

---

## 4. RUNNING THE BACKEND

**[ANTI GRAVITY]** — Hand them the codebase zip + this `.env` file.

### Option A: Docker (Recommended — runs everything)

```bash
# Install Docker Desktop first: https://www.docker.com/products/docker-desktop/

# From inside the kiranamate/ folder:
docker-compose up --build
```

This starts:
- FastAPI app on **http://localhost:8000**
- PostgreSQL on port **5432**
- Redis on port **6379**
- N8N on **http://localhost:5678**

### Option B: Manual (without Docker)

```bash
# 1. Install Python 3.11+
# 2. Install dependencies
pip install -r requirements.txt

# 3. Make sure PostgreSQL is running locally
# 4. Make sure Redis is running locally

# 5. Start the app
uvicorn api.main:app --reload --port 8000
```

### Verify it's working:
- Open **http://localhost:8000** → should show `{"product": "KiranaMate — MerchantMind AI"}`
- Open **http://localhost:8000/docs** → full Swagger API documentation

---

## 5. DATABASE SETUP & SEED DATA

**[ANTI GRAVITY]**

After the backend is running, seed the demo data:

```bash
python db/seed.py
```

This creates:
- **1 demo merchant**: Sharma General Store, Laxmi Nagar, Delhi
- **8 demo customers** with names, phones, payment behavior profiles
- **12 inventory SKUs** including 3 dairy items expiring in 2-3 days
- **30 days of transaction history** with today's dairy anomaly baked in
- **3 overdue khata entries** (Mohan ₹420, Sunita ₹1,240, Ramesh Gupta ₹2,540)
- **Sales baselines** for anomaly detection (4-week rolling averages)

> After seeding, the anomaly detector will immediately find the dairy drop when triggered.

---

## 6. N8N WORKFLOW SETUP — STEP BY STEP

**[YOU]** — You do this yourself on the N8N website/app.

N8N is the automation tool that runs the cron jobs (hourly monitor, Sunday report) and routes WhatsApp messages to the right agent.

### Step 1: Access N8N

**If using Docker (recommended):**
- Open your browser → **http://localhost:5678**
- Login: `admin` / `kiranamate`

**If using N8N Cloud:**
- Go to: **https://app.n8n.io/**
- Sign up for a free account
- You get 5 active workflows on the free plan — enough for this project

---

### Step 2: Import the Pre-built Workflows

1. In N8N, click the **☰ menu** (top left)
2. Click **"Workflows"**
3. Click **"Import from File"** (top right area)
4. Upload the file: `kiranamate/n8n_workflows/workflows.json`
5. Click **"Import"**

You will see **4 workflows** appear:
- `Hourly Sales Monitor`
- `Sunday 7 PM Report`
- `Paytm Transaction Sync`
- `WhatsApp Incoming Webhook`

---

### Step 3: Configure the HTTP Request URLs

Each workflow calls your FastAPI backend. You need to update the URL in each node.

**For Docker (local):** URL is `http://app:8000`
**For deployed server:** Replace with your server URL e.g. `https://your-server.com`

To update:
1. Open each workflow by clicking on it
2. Click on each **"HTTP Request"** node (they look like a plug icon)
3. Check the URL field — update `http://app:8000` to your actual server URL if different
4. Click **"Save"**

---

### Step 4: Set Up the WhatsApp Webhook in N8N

1. Open the **"WhatsApp Incoming Webhook"** workflow
2. Click on the **"WhatsApp Incoming Webhook"** trigger node (the first node)
3. You will see a **Webhook URL** like:
   ```
   http://localhost:5678/webhook/whatsapp-incoming
   ```
4. Copy this URL — you will need it in the next section (WhatsApp Setup)
5. Click **"Save"**

---

### Step 5: Activate All 4 Workflows

1. Open each workflow
2. Toggle the **"Active"** switch (top right of the workflow editor) to **ON**
3. It will turn green — the workflow is now live

Do this for all 4 workflows.

---

### Step 6: Test the Hourly Monitor Manually

1. Open the **"Hourly Sales Monitor"** workflow
2. Click **"Execute Workflow"** (the ▶ play button)
3. You should see each node light up green as it runs
4. The last node should show: `anomalies: [{"category": "dairy", "severity": "CRITICAL"...}]`

> If you see errors in red, check that your backend is running at the correct URL.

---

### Step 7: Test the Sunday Report Manually

1. Open the **"Sunday 7 PM Report"** workflow
2. Click **"Execute Workflow"**
3. The report agent will run and generate a health score
4. Check your WhatsApp — the report should arrive (if WhatsApp is configured)

---

### Step 8: Set Up N8N Credentials for WhatsApp (Optional Advanced)

If you want N8N itself to send WhatsApp messages (instead of the Python backend):

1. In N8N, go to **Settings → Credentials**
2. Click **"+ Add Credential"**
3. Search for **"HTTP Header Auth"**
4. Name: `WhatsApp Meta API`
5. Header Name: `Authorization`
6. Header Value: `Bearer YOUR_WHATSAPP_TOKEN`
7. Save and assign to the HTTP Request nodes that call WhatsApp

> For the hackathon, the Python backend handles all WhatsApp calls — N8N just acts as the trigger/router. So this step is optional.

---

## 7. WHATSAPP BUSINESS API SETUP

**[YOU]** — You do this on the Meta Developer portal.

### Step 1: Register Your Webhook with Meta

After your backend is running (Section 4) and N8N is set up (Section 6):

1. Go to: **https://developers.facebook.com/apps/**
2. Click your **KiranaMate** app
3. In the left menu, click **WhatsApp → Configuration**
4. Under **"Webhook"**, click **"Edit"**
5. Fill in:
   - **Callback URL:**
     - If using N8N: `http://your-server:5678/webhook/whatsapp-incoming`
     - If direct to FastAPI: `http://your-server:8000/webhook/whatsapp`
   - **Verify Token:** `kiranamate_webhook_verify_2024`
     *(This must match `WHATSAPP_VERIFY_TOKEN` in your `.env`)*
6. Click **"Verify and Save"**
7. Meta will call your server to verify — it must return the challenge string
8. After verification, click **"Manage"** next to Webhook Fields
9. Subscribe to: `messages`, `messaging_postbacks`

> **Important:** Your server must be publicly accessible for Meta to reach it. For local development, use **ngrok** (see below).

### Using ngrok for Local Development

If your server is running locally and not on a public URL:

1. Download ngrok: **https://ngrok.com/download**
2. Run:
   ```bash
   ngrok http 8000
   ```
3. You will get a URL like `https://abc123.ngrok.io`
4. Use this as your Callback URL: `https://abc123.ngrok.io/webhook/whatsapp`

---

### Step 2: Test WhatsApp is Working

Send a message from your WhatsApp to the **Test Number** Meta gave you. You should see it appear in:
- Your N8N execution logs (if using N8N routing)
- Your FastAPI terminal logs

---

## 8. COGNEE KNOWLEDGE GRAPH SETUP

**[ANTI GRAVITY]**

After getting the Cognee API key (Section 2.4), the Anti Gravity team needs to:

1. The `COGNEE_API_KEY` in `.env` is all that's needed — the `core/cognee_client.py` file handles all calls automatically
2. Verify the Cognee base URL in `core/cognee_client.py`:
   ```python
   COGNEE_BASE_URL = "https://api.cognee.ai/v1"
   ```
   Update this to the actual Cognee endpoint URL from your Cognee dashboard

3. The knowledge graph is **self-populating** — every agent action writes to it automatically:
   - Campaign outcomes → stored for discount learning
   - Customer payment events → warmth score updates
   - Anomaly detections → baseline calibration
   - Sales baselines → weekly updates

4. **First run:** The graph starts empty. After 1-2 demo runs of all 3 scenarios, it will have enough data to provide intelligent recommendations.

> If Cognee API is down or key is invalid, all agents have **graceful fallbacks** — they use the PostgreSQL baselines instead. Nothing breaks.

---

## 9. SARVAM AI VOICE SETUP

**[ANTI GRAVITY]**

Once `SARVAM_API_KEY` is in `.env`:

1. Sarvam is called automatically when a WhatsApp voice note arrives at `/webhook/whatsapp`
2. The flow is:
   ```
   Merchant sends voice note on WhatsApp
   → Meta sends audio to your webhook
   → routes_webhook.py downloads the audio
   → sarvam_client.py transcribes it
   → campaign_executor.py runs the agent
   ```
3. Supported audio formats: OGG (WhatsApp default), MP4, WAV, MP3
4. The language hint is set to `hi-IN` by default — handles Hinglish automatically

**Fallback:** If Sarvam key is missing/invalid, it automatically uses OpenAI Whisper. Set `OPENAI_API_KEY` to ensure the fallback works.

**Test voice transcription directly:**
```bash
curl -X POST http://localhost:8000/campaign/voice \
  -F "audio=@test_voice.ogg" \
  -F "language=hi-IN"
```

---

## 10. PAYTM BUSINESS API SETUP

**[YOU]**

For the hackathon demo, Paytm has **mock fallbacks** — the system works without real Paytm keys, it just won't actually update catalog prices or pull real transactions.

To use real Paytm integration:

1. Log into **https://business.paytm.com/** with your merchant account
2. Go to **Developer → API Access**
3. Enable:
   - **Catalog Management API** (for price updates)
   - **Transaction History API** (for pulling sales data)
4. Get your MID and Merchant Key (Section 2.8)
5. For testing, use **staging environment** — no real money involved

**For the demo:** You can run with `PAYTM_ENVIRONMENT=staging` and mock data from `db/seed.py`. The campaign executor will show "catalog updated" even in mock mode.

---

## 11. WHAT ANTI GRAVITY NEEDS TO BUILD/CONFIGURE

**[ANTI GRAVITY]** — Complete list of tasks for the Anti Gravity team:

### A. Backend Deployment
- [ ] Deploy the FastAPI app on a server (AWS EC2 / GCP / Railway / Render)
- [ ] Set up PostgreSQL database (managed service like AWS RDS or Supabase is fine)
- [ ] Set up Redis (Redis Cloud free tier: https://redis.com/try-free/)
- [ ] Configure all environment variables from Section 3 on the server
- [ ] Make sure the server has a **public HTTPS URL** (needed for WhatsApp webhook)

### B. Database
- [ ] Run `docker-compose up` to start PostgreSQL
- [ ] Run `python db/seed.py` to seed demo data
- [ ] Verify seed worked: `GET http://localhost:8000/merchant/dashboard` should return data

### C. Cognee Integration
- [ ] Update `COGNEE_BASE_URL` in `core/cognee_client.py` with the correct Cognee endpoint
- [ ] Test: Run `POST /demo/trigger-monitor` and check Cognee logs for writes
- [ ] Cognee stores: merchant margins, customer warmth, campaign outcomes, baselines

### D. LangGraph + Redis State
- [ ] Verify Redis is running: `redis-cli ping` should return `PONG`
- [ ] The campaign executor uses Redis to pause/resume graphs across the approval step
- [ ] If `AsyncRedisSaver` import fails, install: `pip install langgraph[redis]`

### E. N8N Configuration
- [ ] Import `n8n_workflows/workflows.json` into N8N (see Section 6)
- [ ] Update all HTTP Request node URLs to the deployed server URL
- [ ] Activate all 4 workflows
- [ ] Test each workflow manually before the demo

### F. WhatsApp Webhook
- [ ] Register the webhook URL with Meta (see Section 7)
- [ ] Verify the webhook handshake succeeds (green tick in Meta dashboard)
- [ ] Test end-to-end: send a voice note → should trigger the campaign agent

### G. Image Generation
- [ ] Test Stability AI poster: `POST /campaign/text` with `{"goal": "dairy clearance"}`
- [ ] Check the `poster_url` in the response is a valid image URL
- [ ] If Stability API fails, verify OpenAI DALL-E is working as fallback

### H. PDF Health Report
- [ ] Run `POST /report/generate` — check a PDF is created at `/tmp/health_report_*.pdf`
- [ ] The PDF is generated using ReportLab (already in `requirements.txt`)
- [ ] For production: upload PDF to AWS S3 or Cloudinary and return a public URL
  - Update `_generate_pdf()` in `agents/weekly_report.py` to upload and return URL

### I. Things NOT in the Codebase (Needs to be Built/Added)
- [ ] **Stable Diffusion image upload to S3** — currently saves locally to `/tmp/`. Anti Gravity needs to add S3 upload in `agents/campaign_executor.py` → `_generate_poster()` function
- [ ] **PDF upload to S3/Cloudinary** — same issue in `agents/weekly_report.py` → `_generate_pdf()` function
- [ ] **Paytm Catalog API endpoint** — the exact Paytm API path in `core/paytm_client.py` → `update_catalog_price()` needs to be verified against current Paytm docs
- [ ] **Customer phone number lookup** — in `core/cognee_client.py` → `get_dairy_buyers()` returns customers from Cognee graph. For the first demo run, seed customers from `db/seed.py` are used as fallback. Anti Gravity should verify Cognee returns real customer data after a few campaign runs
- [ ] **Ngrok or HTTPS for local demo** — WhatsApp webhook requires HTTPS. Use ngrok for local demos or deploy to a server with SSL

---

## 12. DEMO FLOW — HOW TO RUN ALL 3 SCENARIOS

**[YOU]** — These are the steps for the live hackathon demo.

### PRE-DEMO CHECKLIST
- [ ] Backend running at `http://localhost:8000`
- [ ] Database seeded (`python db/seed.py`)
- [ ] N8N running at `http://localhost:5678` with all 4 workflows active
- [ ] WhatsApp webhook registered with Meta
- [ ] Your phone number added as a test recipient in Meta dashboard
- [ ] All 3 API keys working: Gemini, Sarvam, Serper

---

### SCENARIO 1: Voice Clearance Launch (< 90 seconds)

**What the judges will see:** Merchant speaks a 5-second Hindi voice note → full WhatsApp campaign blasted to 150 customers in under 90 seconds.

**Steps to demo:**

1. Open WhatsApp on your phone
2. Find the **MerchantMind AI** contact (the test number Meta gave you)
3. Record and send a voice note saying:
   > *"Dairy items teen din mein expire ho rahe hain, clearance campaign chalao"*
   > *(Translation: "Dairy items are expiring in 3 days, run a clearance campaign")*
4. Watch the N8N execution logs at **http://localhost:5678** — you will see nodes light up
5. Watch the FastAPI terminal — you will see the agent trace:
   ```
   [00:02.1] [InputParser] Parsed: intent=clearance_campaign, category=dairy
   [00:09.5] [Inventory] SQL matched 161 SKUs (Milk, Paneer, Curd)
   [00:18.0] [SerperAI] Competitor benchmark: avg ₹26, min ₹24
   [00:23.7] [Pricing] Optimal 22% discount applied. Floor protected.
   [00:36.4] [Creative] Poster rendered + 3 copy variations
   ```
6. You will receive a **WhatsApp message** on your phone with the approval card
7. Tap **"✅ Approve"**
8. Campaign goes live — 150 WhatsApp broadcasts sent + Paytm catalog updated

**Alternative (if WhatsApp not set up):**
```bash
curl -X POST http://localhost:8000/campaign/text \
  -H "Content-Type: application/json" \
  -d '{"goal": "dairy items expiring in 3 days, run clearance campaign"}'
```

---

### SCENARIO 2: Anomaly Alert & Recovery

**What the judges will see:** Agent autonomously detects dairy sales down 41% → WhatsApp alert → khata correlation → polite reminders sent.

**Steps to demo:**

1. Trigger the monitor manually:
   ```bash
   curl -X POST http://localhost:8000/demo/trigger-monitor
   ```
   Or in N8N: open **"Hourly Sales Monitor"** → click **"Execute Workflow"**

2. The response shows:
   ```json
   {
     "anomalies": [{"category": "dairy", "severity": "CRITICAL", "deviation_pct": -41}],
     "alerts": [{"category": "dairy", "sent": true}],
     "reminders": [{"customer": "Mohan Sharma", "amount": 420, "sent": true}]
   }
   ```

3. Check your WhatsApp — you will receive:
   - 🚨 Anomaly alert with action buttons
   - 📒 Khata reminder sent to Mohan Sharma in Hindi

4. Tap **"✅ Run Campaign"** on the WhatsApp alert → triggers Scenario 1 automatically

---

### SCENARIO 3: Sunday Health Briefing

**What the judges will see:** Automated weekly report with 0-100 score, PDF, and AI recommendation.

**Steps to demo:**

1. Trigger the report manually:
   ```bash
   curl -X POST http://localhost:8000/demo/trigger-report
   ```
   Or in N8N: open **"Sunday 7 PM Report"** → click **"Execute Workflow"**

2. The response shows:
   ```json
   {
     "health_score": 74,
     "revenue_trend": 14.0,
     "week_revenue": 53360,
     "khata_recovered": 4200,
     "recommendation": "Rice category up 22% — pre-order 20% more stock before Thursday",
     "pdf_url": "file:///tmp/health_report_111...pdf"
   }
   ```

3. Check your WhatsApp — you will receive:
   - 📊 Health score message: "Store Score: 74/100 — Good ✅"
   - 📄 PDF attachment with the full weekly breakdown

---

## 13. TROUBLESHOOTING

### ❌ "Connection refused" when starting the app
- Make sure PostgreSQL is running: `docker-compose up postgres`
- Check `DATABASE_URL` in `.env` is correct

### ❌ WhatsApp webhook verification failing
- Your server must be publicly accessible — use ngrok for local: `ngrok http 8000`
- Check `WHATSAPP_VERIFY_TOKEN` in `.env` matches what you entered in Meta dashboard
- The verify token must be exactly: `kiranamate_webhook_verify_2024`

### ❌ "No module named 'langgraph'"
```bash
pip install -r requirements.txt
```

### ❌ LangGraph Redis error
- Make sure Redis is running: `docker-compose up redis`
- Or install: `pip install langgraph[redis]`

### ❌ Sarvam transcription returning empty
- Check `SARVAM_API_KEY` is correct
- System will auto-fallback to OpenAI Whisper — make sure `OPENAI_API_KEY` is set

### ❌ Campaign agent stops at approval gate and never resumes
- This is expected behaviour — it's waiting for the merchant to tap "Approve" on WhatsApp
- For testing without WhatsApp, manually resume:
  ```bash
  curl -X POST http://localhost:8000/campaign/approve/YOUR_THREAD_ID
  ```
  Get `thread_id` from the initial campaign response

### ❌ No transactions showing on dashboard
- Run seed data: `python db/seed.py`
- Check: `GET http://localhost:8000/merchant/transactions`

### ❌ N8N workflows not triggering
- Check workflows are **Active** (green toggle in N8N)
- Check the HTTP Request URL points to your running backend
- Click **"Execute Workflow"** manually to test

---

## QUICK REFERENCE — ALL API ENDPOINTS

| Method | URL | What it does |
|---|---|---|
| GET | `/` | Health check |
| GET | `/docs` | Full API documentation (Swagger) |
| POST | `/demo/trigger-monitor` | Manually run anomaly detection |
| POST | `/demo/trigger-report` | Manually run weekly health report |
| GET | `/merchant/dashboard` | Full dashboard data |
| GET | `/merchant/khata` | All overdue khata entries |
| POST | `/merchant/khata/remind` | Send reminder to one customer |
| GET | `/merchant/inventory` | Inventory with expiry status |
| GET | `/merchant/anomalies` | Active anomalies |
| POST | `/campaign/text` | Start campaign from text goal |
| POST | `/campaign/voice` | Start campaign from voice note (audio file) |
| POST | `/campaign/approve/{thread_id}` | Approve a pending campaign |
| POST | `/campaign/cancel/{thread_id}` | Cancel a pending campaign |
| POST | `/report/generate` | Generate weekly health report |
| GET | `/report/latest` | Get most recent health report |
| GET | `/webhook/whatsapp` | WhatsApp webhook verification (Meta calls this) |
| POST | `/webhook/whatsapp` | WhatsApp incoming messages |
| POST | `/webhook/paytm` | Paytm transaction events |

---

*KiranaMate — MerchantMind AI | Team Epoch | Paytm Build for India AI Hackathon — Delhi Edition*
