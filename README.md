# KiranaMate — MerchantMind AI
### *The Autonomous Business Teammate for 12+ Million Indian Kirana Stores*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent_StateGraph-FF6F00?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Meta WhatsApp](https://img.shields.io/badge/WhatsApp-Cloud_API_Native-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)](https://developers.facebook.com/docs/whatsapp/)
[![Sarvam AI](https://img.shields.io/badge/Sarvam_AI-saaras:v3_Vernacular_Voice-9C27B0?style=for-the-badge)](https://sarvam.ai)
[![Cognee](https://img.shields.io/badge/Cognee-Knowledge_Graph_Memory-4CAF50?style=for-the-badge)](https://cognee.ai)
[![Paytm](https://img.shields.io/badge/Paytm-Soundbox_&_UPI_Webhooks-002E6E?style=for-the-badge&logo=paytm&logoColor=white)](https://paytm.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

---

> **"Like a GPS for your business — always watching, always guiding, never needing to be asked."**  
> *Zero-app adoption friction, vernacular voice-first interaction, proactive multi-agent intelligence, and 100% margin-guaranteed execution.*

---

## 🗂️ Project Structure

```
kiranamate/
├── agents/                     # LangGraph StateGraph Autonomous Agents
│   ├── sales_monitor.py        # Hourly Sales Deviation & Trend Tracker
│   ├── campaign_executor.py    # 6-Step Autonomous Campaign Swarm
│   └── weekly_report.py        # ReportLab PDF Generation & WhatsApp Delivery
├── api/                        # FastAPI Webhook & Dashboard Endpoints
│   ├── main.py                 # Application router, CORS & SSE bus
│   ├── routes_merchant.py      # /merchant telemetry & metrics endpoints
│   ├── routes_campaign.py      # /campaign/text & approval endpoints
│   ├── routes_webhook.py       # WhatsApp Cloud API & Paytm webhooks
│   └── routes_health.py        # Health & system diagnostics
├── core/                       # Integrations & Core Infrastructure
│   ├── cognee_client.py        # Knowledge graph memory store
│   ├── serper_client.py        # Serper AI live competitor price scraping
│   ├── whatsapp_client.py      # Meta WhatsApp Cloud API client
│   ├── paytm_client.py         # Paytm Business & Soundbox event parser
│   ├── sarvam_client.py        # Sarvam AI vernacular speech-to-text
│   ├── trace_bus.py            # Real-time SSE trace event bus
│   └── tunnel_manager.py       # Localtunnel / ngrok webhook tunnel
├── dashboard/                  # Human-Crafted Airbnb Design System Frontend
│   ├── index.html              # Clean, semantic merchant interface
│   ├── style.css               # Airbnb Cereal tokens, pure white canvas
│   └── app.js                  # SSE stream listener & real-time telemetry
├── db/                         # Persistence Layer
│   ├── database.py             # SQLAlchemy async engine & session
│   ├── models.py               # Merchant, Transaction, Campaign & Khata models
│   └── seed.py                 # Realistic Kirana store demo seed script
└── utils/                      # Deterministic Mathematical Engines
    ├── anomaly_detector.py     # 4-week rolling baseline statistical engine
    └── discount_calculator.py  # Cost floor & margin-safe discount calculus
```

---

> **"Like a GPS for your business — always watching, always guiding, never needing to be asked."**  
> *Zero-app adoption friction, vernacular voice-first interaction, proactive multi-agent intelligence, and 100% margin-guaranteed execution.*

---

## 📑 Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Exact Problem & Quality of the Problem](#2-the-exact-problem--quality-of-the-problem)
   - [The Quick-Commerce Assault](#21-the-quick-commerce-assault)
   - [The SaaS & ERP Adoption Paradox](#22-the-saas--erp-adoption-paradox)
   - [The Triple Silent Margin Bleed](#23-the-triple-silent-margin-bleed)
3. [Relevance & Philosophy of the Technical Solution](#3-relevance--philosophy-of-the-technical-solution)
   - [Why WhatsApp Native?](#31-why-whatsapp-native)
   - [Why Sarvam AI Vernacular Voice (`saaras:v3`)?](#32-why-sarvam-ai-vernacular-voice-saarasv3)
   - [Why Event-Driven Passive Ingestion (Paytm Soundbox)?](#33-why-event-driven-passive-ingestion-paytm-soundbox)
   - [Why LangGraph Stateful Orchestration?](#34-why-langgraph-stateful-orchestration)
   - [Why Knowledge Graph Memory (Cognee) over Flat SQL?](#35-why-knowledge-graph-memory-cognee-over-flat-sql)
   - [Why Real-Time Competitor Scraping (Serper AI)?](#36-why-real-time-competitor-scraping-serper-ai)
4. [Complete Technical Architecture](#4-complete-technical-architecture)
   - [High-Level Architectural Blueprint](#41-high-level-architectural-blueprint)
   - [End-to-End Ingestion, Reasoning & Delivery Pipeline](#42-end-to-end-ingestion-reasoning--delivery-pipeline)
   - [Data & State Management](#43-data--state-management)
5. [Autonomous AI Agents & Multi-Agent Workflows](#5-autonomous-ai-agents--multi-agent-workflows)
   - [Agent 1: Autonomous Sales Anomaly Monitor (`sales_monitor.py`)](#51-agent-1-autonomous-sales-anomaly-monitor)
   - [Agent 2: LangGraph Campaign Executor (`campaign_executor.py`)](#52-agent-2-langgraph-campaign-executor)
   - [Agent 3: Weekly Business Health Doctor (`weekly_report.py`)](#53-agent-3-weekly-business-health-doctor)
   - [Agent 4: Khata Credit Recovery Engine (`khata_recovery.py`)](#54-agent-4-khata-credit-recovery-engine)
6. [Mathematical Foundations & Algorithmic Formulations](#6-mathematical-foundations--algorithmic-formulations)
   - [Statistical Anomaly Detection (EWMA + Z-Score)](#61-statistical-anomaly-detection-ewma--z-score)
   - [Margin-Safe Dynamic Pricing Engine](#62-margin-safe-dynamic-pricing-engine)
   - [4-Pillar Composite Business Health Diagnostic (0–100 Scale)](#63-4-pillar-composite-business-health-diagnostic-0100-scale)
7. [System Workflows & Sequence Diagrams](#7-system-workflows--sequence-diagrams)
   - [Workflow A: Voice-to-Clearance Campaign (< 90s)](#71-workflow-a-voice-to-clearance-campaign--90s)
   - [Workflow B: Autonomous Sales Anomaly to Khata Escalation](#72-workflow-b-autonomous-sales-anomaly-to-khata-escalation)
8. [Innovation & Competitive Differentiation](#8-innovation--competitive-differentiation)
   - [Comparative Matrix](#81-comparative-matrix)
   - [Core Innovations](#82-core-innovations)
9. [Technology Stack Defense](#9-technology-stack-defense)
10. [Repository Directory & Component Index](#10-repository-directory--component-index)
11. [Installation & Deployment Guide](#11-installation--deployment-guide)
12. [API Reference & Webhook Contract](#12-api-reference--webhook-contract)
13. [Anticipated Questions & Technical Defense](#13-anticipated-questions--technical-defense)

---

## 1. Executive Summary

India's retail landscape is anchored by **over 12 million mom-and-pop grocery stores (*Kiranas*)**, accounting for over **85% of the country's $800B+ retail food and grocery market**. These merchants are under severe structural threat from heavily capitalized, algorithm-driven Quick-Commerce platforms (Blinkit, Zepto, Swiggy Instamart) that operate with hyper-optimized pricing, instant delivery, and real-time inventory tracking.

While corporate conglomerates deploy fleets of quantitative data scientists, the typical Kirana merchant ("Ramesh ji") works 14-to-16-hour days with only a paper ledger (*Bahi-Khata*), a counter-top Paytm Soundbox, and a smartphone used almost exclusively for **WhatsApp**.

**KiranaMate (MerchantMind AI)** levels this playing field. It is an **Autonomous Business Teammate** operating entirely through **Meta WhatsApp Cloud API** and **Vernacular Voice AI (Sarvam AI)**. KiranaMate does not ask the merchant to learn, install, or navigate a dashboard. Instead, it runs 24/7 background agentic loops that listen to real-time Paytm soundbox transactions, detect category sales anomalies using time-series baselines, scrape hyper-local competitor pricing in real time, calculate margin-guaranteed clearance discounts, formulate targeted WhatsApp buyer campaigns, and deliver executive-grade Sunday PDF audits.

With **zero adoption friction** and **human-in-the-loop safeguards**, KiranaMate turns unorganized retail into an automated, data-empowered powerhouse.

---

## 2. The Exact Problem & Quality of the Problem

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           THE KIRANA CRISIS IN NUMBERS                            │
├─────────────────────┬───────────────────────────┬─────────────────────────────────┤
│    12+ Million      │          $800B+           │            40% - 60%            │
│   Kirana Stores     │   Retail Market Value     │   Drop in Walk-ins (Q-Commerce) │
├─────────────────────┼───────────────────────────┼─────────────────────────────────┤
│     14-16 Hours     │         ₹45,000+          │            15% - 25%            │
│   Daily Work Hours  │   Trapped Working Capital │   Perishables Expiring Unsold   │
└─────────────────────┴───────────────────────────┴─────────────────────────────────┘
```

### 2.1 The Quick-Commerce Assault
Quick-Commerce (Q-Commerce) companies have built 10-minute dark-store supply chains directly inside residential clusters. They leverage:
- **Dynamic algorithmic pricing** that undercuts physical retail on high-velocity staples.
- **Predictive reordering engines** that virtually eliminate out-of-stock and over-stock scenarios.
- **Aggressive push notifications** timed precisely around consumer replenishment cycles.

Neighborhood Kiranas, traditionally protected by geographic proximity and personal customer relationships, are losing their highest-margin baskets (packaged snacks, dairy, personal care, and beverages).

### 2.2 The SaaS & ERP Adoption Paradox
Over the past decade, dozens of startups have built desktop billing software, mobile ERP apps, and digital khata products for Kirana owners. **Over 80% suffer from catastrophic churn.** Why?
- **Extreme Cognitive Load:** A merchant handling 200–400 customer walk-ins per day while balancing physical stock, weighing grains, and answering calls cannot sit down to enter barcode numbers or update SKUs manually.
- **English-Centric, Text-Heavy UIs:** Most solutions assume tech literacy and desktop or structured mobile usage.
- **Passive Nature of Software:** Traditional apps are *passive ledgers*. They record what happened, but they never tell the merchant *what to do right now* to prevent financial loss.

### 2.3 The Triple Silent Margin Bleed
Kirana merchants suffer from three compounding financial leaks that occur invisibly:
1. **Perishable Dead Stock & Capital Traps:** Milk, curd, bread, paneer, and packaged confectionery sit in deep shelves and pass their expiry dates silently. Once expired, they represent a total 100% loss of working capital.
2. **Asymmetric Pincode Pricing Blindness:** Merchants have zero visibility into what Zepto or Blinkit are charging for an identical SKU 400 meters away. They either overprice (driving customers to apps) or underprice (leaving gross margin on the table).
3. **Informal Khata (Credit) Float Paralysis:** Kiranas survive on personal trust, lending money via informal ledgers (*Udhar / Khata*). Overdue debt accumulates for months. Merchants hesitate to call or send harsh reminders for fear of damaging neighborhood social relationships, leading to cash-flow starvation.

---

## 3. Relevance & Philosophy of the Technical Solution

KiranaMate rejects the premise that merchants should adapt to enterprise software. Instead, **enterprise-grade AI adapts entirely to the merchant's existing daily behavior.**

```
Traditional Approach (Fails)                KiranaMate Approach (Succeeds)
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│  New Complex App to Download   │         │  100% Inside WhatsApp Native    │
│  Barcode Scanners & Manual Data │   VS    │  Passive Paytm Soundbox Events  │
│  Passive Dashboard Reports      │         │  Proactive Multi-Agent Triggers │
│  Complex English UIs            │         │  Sarvam Vernacular Voice Notes  │
└─────────────────────────────────┘         └─────────────────────────────────┘
```

### 3.1 Why WhatsApp Native?
WhatsApp is the de facto digital operating system of India. Kirana owners already use WhatsApp 50+ times a day to chat with family, distributors, and customers.
- **Zero App Download:** No Google Play Store installation, no storage constraints, no app updates.
- **Zero Training:** The merchant already understands how to tap a message, listen to a voice note, and press quick-reply buttons (`[Approve]`, `[Details]`, `[Ignore]`).
- **100% Open & Delivery Rate:** Direct notification delivery ensures urgent alerts (e.g., *“Dairy down 40%”*) are read within 3 minutes.

### 3.2 Why Sarvam AI Vernacular Voice (`saaras:v3`)?
Kirana stores are noisy acoustic environments (honking traffic, customer chatter, ceiling fans). Furthermore, merchants communicate in vernacular languages or mixed dialects (Hindi, Hinglish, Tamil, Marathi, Telugu).
- Standard global Speech-to-Text models (like vanilla Whisper) degrade significantly on Indian acoustic noise and colloquial mixed-language syntax.
- **Sarvam AI (`saaras:v3`)** is custom-trained on Indian linguistic datasets, accurately transcribing spoken Hinglish (e.g., *"Amul doodh expiry ho raha hai, padosi grahako ko offer bhej do"*), enabling completely hands-free voice commands.

### 3.3 Why Event-Driven Passive Ingestion (Paytm Soundbox)?
Paytm Soundboxes are already present on the counter of nearly every Indian Kirana. By tapping into **Paytm UPI Transaction Webhooks**, KiranaMate automatically captures the timestamp, amount, and payment memo of every transaction **without requiring the merchant to scan a barcode or tap a register**. Sales volume is inferred passively in real-time.

### 3.4 Why LangGraph Stateful Orchestration?
Autonomous retail workflows require multi-step reasoning: parsing goals, querying stock, checking competitor pricing, calculating margins, identifying customers, drafting messages, and pausing for approval.
- Traditional linear chains or simple LLM wrappers fail when a step errors or requires asynchronous human confirmation.
- **LangGraph** models this as a cyclic, deterministic **StateGraph** with checkpointed state and built-in **Human-in-the-Loop (`interrupt_before`)** capabilities. The system formulates the complete campaign and halts, waiting for the merchant’s WhatsApp button click before dispatching.

### 3.5 Why Knowledge Graph Memory (Cognee) over Flat SQL?
Customer-store relationships in Indian Kiranas are deeply relational and non-linear:
- Relational databases struggle with fuzzy semantic affinities: *“Ramesh’s neighbor Sharma ji buys cow milk every Tuesday morning, has high price sensitivity, and owes ₹350 on khata.”*
- **Cognee Knowledge Graph** builds an associative memory graph connecting `Customer` ➔ `Product Affinity` ➔ `Price Elasticity` ➔ `Khata Repayment Behavior`, allowing hyper-personalized clearance targeting rather than indiscriminate spam.

### 3.6 Why Real-Time Competitor Scraping (Serper AI)?
Static price databases become stale within hours in the fast-moving Q-Commerce landscape. By utilizing **Serper AI**, KiranaMate performs live Google and quick-commerce searches matching product title, weight, and merchant city/pincode to obtain ground-truth Blinkit, Zepto, and Instamart prices.

---

## 4. Complete Technical Architecture

### 4.1 High-Level Architectural Blueprint

```mermaid
graph TD
    %% TRIGGERS & INGESTION
    subgraph S1["1. Event Ingestion & Trigger Layer"]
        PSB["Paytm Soundbox & QR<br/>(UPI Webhooks)"]
        WAV["Merchant Voice Note / Audio<br/>(Meta WhatsApp Cloud API)"]
        WAT["Merchant Text / Button Click<br/>(Meta Interactive Webhook)"]
        CRON["APScheduler Engine<br/>(Hourly Monitor & Sun 7PM Audit)"]
    end

    %% GATEWAY
    subgraph S2["2. Asynchronous API Gateway (FastAPI)"]
        GW["FastAPI Core Gateway<br/>(/webhook, /campaign, /merchant, /health)"]
        SEC["Webhook HMAC Verification & Idempotency"]
        SSE["Server-Sent Events (SSE) Bus<br/>(Live Command Center Sync)"]
        GW --> SEC
        GW --> SSE
    end

    PSB -->|JSON Webhook| GW
    WAV -->|Media URL| GW
    WAT -->|Payload| GW
    CRON -->|Async Cron Trigger| GW

    %% COGNITIVE BRAIN
    subgraph S3["3. Multi-Agent Reasoning Engine (LangGraph + LLMs)"]
        STT["Sarvam AI Engine<br/>(saaras:v3 Indian Voice STT)"]
        ANOM["Anomaly Detection Engine<br/>(EWMA + 4-Week Rolling Z-Score)"]
        
        subgraph LG["LangGraph Stateful Agent Pipeline"]
            direction TB
            N_IN["InputParser Node<br/>(Intent, Entity & Category Extractor)"]
            N_INV["InventoryQuerier Node<br/>(Expiry & Stock Velocity Filter)"]
            N_PRC["DiscountCalculator Node<br/>(Margin Floor + Competitor Match)"]
            N_DSG["CampaignDesigner Node<br/>(Hinglish Copy & Target Segmentation)"]
            N_APP["ApprovalGate Node<br/>(Human-in-the-Loop Breakpoint)"]
            N_EXE["CampaignExecutor Node<br/>(Batch WhatsApp Dispatch)"]
            N_SUM["OutcomeSummary Node<br/>(ROI & Revenue Recovery Projection)"]

            N_IN --> N_INV --> N_PRC --> N_DSG --> N_APP
            N_APP -.->|Merchant Approved| N_EXE --> N_SUM
        end

        REP["Weekly Health Diagnostic Engine<br/>(4-Pillar Store Scoring & Audit)"]
    end

    SEC -->|Voice Payload| STT --> N_IN
    SEC -->|Interactive Button| N_APP
    SEC -->|Paytm Transaction| ANOM
    CRON -->|Hourly Scan| ANOM
    CRON -->|Sunday 7 PM| REP

    %% MEMORY & EXTERNAL INTELLIGENCE
    subgraph S4["4. Memory, Intelligence & Compute Engines"]
        COG["Cognee Knowledge Graph<br/>(Customer Affinity & Semantic Memory)"]
        SERP["Serper AI Engine<br/>(Live Blinkit / Zepto / Instamart Scraping)"]
        MATH["Dynamic Margin Math<br/>(5% Absolute Floor Protection)"]
        PDF["ReportLab Vector Engine<br/>(In-Memory Multi-Page PDF Generator)"]
        LLM["Primary LLM: Gemini 1.5 / 2.0 Flash<br/>Fallback: OpenAI GPT-4o"]
    end

    N_INV <--> COG
    N_PRC <--> SERP
    N_PRC <--> MATH
    N_DSG <--> LLM
    N_DSG <--> COG
    REP <--> PDF
    REP <--> COG

    %% PERSISTENCE
    subgraph S5["5. Persistence & State Storage"]
        SQL["Async Relational DB (PostgreSQL / SQLite)<br/>Transactions, Products, Customers, Khata"]
        REDIS["Redis / Memory Checkpointer<br/>(LangGraph State Persistence)"]
    end

    N_APP <--> REDIS
    ANOM <--> SQL
    REP <--> SQL
    N_INV <--> SQL

    %% OUTBOUND DELIVERY
    subgraph S6["6. Action & Omnichannel Delivery"]
        WA_SND["Meta WhatsApp Cloud API<br/>(Interactive Buttons, Templates & PDF Media)"]
        DASH["Glassmorphism Merchant Dashboard<br/>(Vanilla CSS, Real-time Charts & Simulated Phone)"]
    end

    N_APP -->|Send Campaign Proposal| WA_SND
    N_EXE -->|Personalized WhatsApp Offers| WA_SND
    ANOM -->|Push Anomaly Alerts| WA_SND
    REP -->|Send Diagnostic PDF| WA_SND
    SSE --> DASH
```

### 4.2 End-to-End Ingestion, Reasoning & Delivery Pipeline

The operational pipeline flows through six distinct phases:

1. **Ingestion & Handshake:**
   - Inbound HTTP requests arrive at `api/routes_webhook.py`.
   - Meta webhook challenge handshakes (`hub.mode`, `hub.verify_token`, `hub.challenge`) are verified in microseconds.
   - Incoming audio messages trigger an asynchronous media download via Meta Graph API, which is piped directly to Sarvam AI's REST endpoint without writing temporary files to disk.

2. **Vernacular Understanding:**
   - Sarvam AI transcribes Indian dialect speech to UTF-8 text.
   - The primary LLM (Gemini / GPT-4o) extracts structured JSON intent:
     ```json
     {
       "intent": "CLEARANCE_CAMPAIGN",
       "category": "dairy",
       "quantity_target": 15,
       "urgency_days": 2
     }
     ```

3. **Autonomous Intelligence Retrieval:**
   - **Database Query:** Identifies all SKUs matching the category where `expiry_date <= now() + 3 days` or stock velocity has dropped.
   - **Serper AI Web Search:** Simultaneously queries Google for `"Amul Taaza Milk 500ml price Blinkit Mumbai"` and extracts competitor pricing.
   - **Cognee Graph Query:** Traverses edges between target product category and regular customer nodes to find high-affinity buyers.

4. **Algorithmic Pricing Optimization:**
   - The pricing engine evaluates the unit cost floor ($Cost \times 1.05$), calculates the target competitor undercut ($P_{competitor} \times 0.95$), and clamps the discount to a margin-safe envelope.

5. **Human-in-the-Loop Gate:**
   - The campaign agent compiles an interactive WhatsApp message containing product details, competitor benchmark, clearance price, and target audience count.
   - LangGraph checkpoints the current state into memory/Redis and raises an execution interrupt.
   - The merchant receives an interactive message with two tap targets: `[✅ Approve]` or `[❌ Cancel]`.

6. **Execution & Feedback:**
   - Upon receiving the `[Approve]` webhook, LangGraph resumes from its checkpoint, iterates through the target customer list, formats personalized Hinglish WhatsApp offers with Paytm UPI deep-links, and dispatches them via Meta Cloud API.
   - Real-time events stream to the Glassmorphism Web Dashboard via Server-Sent Events (SSE).

---

## 5. Autonomous AI Agents & Multi-Agent Workflows

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      KIRANAMATE AGENTIC SPECIALIZATION                          │
├──────────────────────┬──────────────────────┬───────────────────────────────────┤
│ Agent Name           │ Execution Frequency  │ Primary Responsibility            │
├──────────────────────┼──────────────────────┼───────────────────────────────────┤
│ Sales Anomaly Monitor│ Hourly Background    │ Rolling EWMA time-series tracking │
│ Campaign Executor    │ On-Demand / Triggered│ 7-Node LangGraph clearance engine │
│ Health Report Doctor │ Sunday 7:00 PM IST   │ 4-Pillar diagnostic & PDF audit   │
│ Khata Recovery       │ Event / Batch Driven │ Soft vernacular debt collection   │
└──────────────────────┴──────────────────────┴───────────────────────────────────┘
```

### 5.1 Agent 1: Autonomous Sales Anomaly Monitor
*Implemented in `agents/sales_monitor.py` & `utils/anomaly_detector.py`*

Operating as a continuous background daemon, this agent monitors store velocity without requiring any human prompts:
- **Data Ingestion:** Aggregates real-time Paytm transactions grouped by 5 core Kirana categories: `Dairy`, `Snacks`, `Staples`, `Beverages`, and `Personal Care`.
- **Baseline Comparison:** Fetches 4-week rolling baselines specific to the current day of the week and hour.
- **Severity Classification:**
  - **CRITICAL (> 30% drop):** Immediate WhatsApp interactive alert pushed to the merchant.
  - **WARNING (15% - 30% drop):** Queued for inclusion in the evening summary.
  - **INFO (< 15% drop):** Silent internal telemetry log.
- **Interactive Escalation:** On CRITICAL drops, dispatches a WhatsApp prompt:
  > *"🚨 Alert Ramesh ji! Dairy sales are down 41% compared to your usual Friday. 14 milk packets risk expiring. Should I launch a clearance campaign?"*  
  > Buttons: `[✅ Run Campaign]` | `[📊 Details]` | `[❌ Ignore]`

### 5.2 Agent 2: LangGraph Campaign Executor
*Implemented in `agents/campaign_executor.py`*

Constructed using a deterministic 7-node **LangGraph StateGraph**:

```mermaid
stateDiagram-v2
    [*] --> InputParser
    InputParser --> InventoryQuerier: Intent & Category Identified
    InventoryQuerier --> DiscountCalculator: Near-Expiry SKUs Found
    DiscountCalculator --> CampaignDesigner: Optimal Margin Computed
    CampaignDesigner --> ApprovalGate: Proposal Drafted
    
    state ApprovalGate {
        [*] --> AwaitingMerchantTap
        AwaitingMerchantTap --> Approved: Tap [Approve]
        AwaitingMerchantTap --> Rejected: Tap [Cancel]
    }
    
    ApprovalGate --> CampaignExecutor: Approved
    ApprovalGate --> [*]: Rejected
    CampaignExecutor --> OutcomeSummary: Messages Dispatched
    OutcomeSummary --> [*]: Final Report Logged
```

- **Node 1 (`InputParser`):** Normalizes vernacular speech or text into structured intent, category, and quantity constraints.
- **Node 2 (`InventoryQuerier`):** Queries relational database for products in the category expiring within $N$ days.
- **Node 3 (`DiscountCalculator`):** Invokes Serper AI for Blinkit/Zepto live pricing, runs margin safety algorithms, and selects the optimal clearance price.
- **Node 4 (`CampaignDesigner`):** Queries Cognee Knowledge Graph for high-propensity customer segments and drafts warm, localized Hinglish promotional copy.
- **Node 5 (`ApprovalGate`):** Halts execution via `interrupt_before`. Dispatches an interactive approval card to the merchant's WhatsApp.
- **Node 6 (`CampaignExecutor`):** Iterates over recipient customers, injecting unique customer names and payment links into approved copy, and fires Meta WhatsApp API requests.
- **Node 7 (`OutcomeSummary`):** Aggregates dispatch counts, expected revenue recovery, and margin saved; updates Cognee graph memory.

### 5.3 Agent 3: Weekly Business Health Doctor
*Implemented in `agents/weekly_report.py`*

Every Sunday at 7:00 PM IST (or on-demand when the merchant asks *"Report bhejo"*):
- Synthesizes the last 7 days of transactions against the previous 14 days.
- Computes the **4-Pillar 0–100 Store Health Score**:
  1. **Revenue Health (0–25 pts)**
  2. **Inventory & Dead Capital Risk (0–25 pts)**
  3. **Customer Retention (0–25 pts)**
  4. **Khata Outstanding Risk (0–25 pts)**
- Dynamically compiles a multi-page, publication-quality **Vector PDF Report** using `ReportLab`.
- Sends the PDF document natively into the merchant's WhatsApp chat accompanied by a 2-sentence conversational voice summary.

### 5.4 Agent 4: Khata Credit Recovery Engine
*Implemented in `agents/khata_recovery.py`*

Recovers trapped working capital without alienating community relationships:
- Scans `KhataEntry` ledger records for debts overdue past 14 and 30 days.
- Cross-references customer loyalty records in Cognee: VIP customers receive polite, respectful reminders; infrequent buyers receive clear balance notifications with direct Paytm UPI deep-links.
- Drafts culturally nuanced vernacular follow-ups (*"Namaste Sharma ji, pichle mahine ka ₹450 ka hisab baaki hai. Suvidha anusar Paytm link se chukta kar dijiye"*).

---

## 6. Mathematical Foundations & Algorithmic Formulations

### 6.1 Statistical Anomaly Detection (EWMA + Z-Score)

To prevent false alarms caused by natural daily retail fluctuations (e.g., quiet Tuesday afternoons vs. busy Sunday mornings), KiranaMate uses an **Exponentially Weighted Moving Average (EWMA)** combined with dynamic day-of-week standard deviations.

For category $c$ on day-of-week $d$ at hour $h$, the rolling expected revenue baseline $\mu_{c,d}$ and variance $\sigma^2_{c,d}$ are computed over a 4-week historical window ($W = 4$):

$$\mu_{c,d} = \frac{\sum_{w=1}^{W} \alpha (1 - \alpha)^{w-1} \cdot R_{c,d,w}}{\sum_{w=1}^{W} \alpha (1 - \alpha)^{w-1}}$$

Where:
- $R_{c,d,w}$ is the historical revenue for category $c$ on day $d$ in historical week $w$.
- $\alpha \in (0, 1]$ is the decay factor giving higher weight to recent weeks (configured to $\alpha = 0.4$).

The hourly percentage deviation $\Delta_{pct}$ and Z-score $Z_{c}$ are calculated as:

$$\Delta_{pct} = \left( \frac{R_{actual} - \mu_{c,d}}{\mu_{c,d}} \right) \times 100$$

$$Z_c = \frac{R_{actual} - \mu_{c,d}}{\sigma_{c,d}}$$

A **CRITICAL Anomaly** is flagged if and only if:

$$\Delta_{pct} \le -30.0\% \quad \text{AND} \quad Z_c \le -1.96 \quad (p < 0.05)$$

---

### 6.2 Margin-Safe Dynamic Pricing Engine

Kirana clearance discounts must clear inventory rapidly without ever selling below cost. The algorithm establishes an **absolute cost floor** and benchmarks against real-time competitor prices:

1. **Absolute Merchant Cost Floor ($P_{floor}$):**
   $$P_{floor} = C_{unit} \times (1 + \mu_{min})$$
   *Where $C_{unit}$ is the wholesale procurement cost, and $\mu_{min} = 0.05$ (guaranteeing a strict minimum 5% gross profit margin).*

2. **Competitor Undercut Target ($P_{comp\_target}$):**
   $$P_{comp\_target} = \min(P_{Blinkit}, P_{Zepto}) \times (1 - \delta_{undercut})$$
   *Where $\delta_{undercut} = 0.05$ (pricing 5% below the lowest quick-commerce competitor).*

3. **Optimal Clearance Price Selection ($P_{final}$):**
   $$P_{target} = \min\left( P_{comp\_target}, P_{historical\_best} \right)$$
   $$P_{final} = \max\left( P_{target}, P_{floor} \right)$$

4. **Guaranteed Discount Capping:**
   $$D_{pct} = \min\left( \frac{P_{mrp} - P_{final}}{P_{mrp}} \times 100, \; D_{max\_cap} \right)$$
   *(where $D_{max\_cap} = 40.0\%$)*

5. **Expected Revenue Recovery ($R_{recovery}$):**
   $$R_{recovery} = Q_{inventory} \times \eta_{clearance} \times P_{final}$$
   *Where $\eta_{clearance} \approx 0.70$ (expected 70% inventory clearance rate within 24 hours).*

---

### 6.3 4-Pillar Composite Business Health Diagnostic (0–100 Scale)

The weekly health diagnostic evaluates store vitality across four equal pillars, generating an integer score $S_{total} \in [0, 100]$:

$$S_{total} = S_{rev} + S_{inv} + S_{ret} + S_{khata}$$

Each pillar is scored out of 25 points:

| Pillar | Metric Analyzed | Mathematical Formula | Max Points |
| :--- | :--- | :--- | :---: |
| **1. Revenue Health ($S_{rev}$)** | Week-over-Week Growth Rate ($g_{wow}$) | $S_{rev} = \text{clamp}\left( 15 + \left( \frac{R_{w} - R_{w-1}}{R_{w-1}} \times 50 \right), 0, 25 \right)$ | **25 pts** |
| **2. Inventory Vitality ($S_{inv}$)** | Ratio of Dead/Expiring Stock to Total Active Stock | $S_{inv} = 25 \times \left( 1 - \frac{\text{Value of Stock Expiring in 7 Days}}{\text{Total Inventory Valuation}} \right)$ | **25 pts** |
| **3. Customer Retention ($S_{ret}$)** | Repeat Customer Frequency ($F_{repeat}$) | $S_{ret} = 25 \times \left( \frac{N_{customers}(\ge 2 \text{ txns in 14d})}{N_{total\_active\_customers}} \right)$ | **25 pts** |
| **4. Khata Float Health ($S_{khata}$)** | Overdue Credit (> 30 Days) Ratio | $S_{khata} = 25 \times \left( 1 - \frac{\text{Khata Balance Overdue } > 30d}{\text{Total Outstanding Khata Float}} \right)$ | **25 pts** |

---

## 7. System Workflows & Sequence Diagrams

### 7.1 Workflow A: Voice-to-Clearance Campaign (< 90s)

```mermaid
sequenceDiagram
    autonumber
    actor Merchant as Merchant (Ramesh ji)
    participant WA as Meta WhatsApp Cloud API
    participant GW as FastAPI Gateway
    participant STT as Sarvam AI (saaras:v3)
    participant LG as LangGraph Campaign Agent
    participant SERP as Serper AI (Blinkit Scraper)
    participant COG as Cognee Knowledge Graph
    participant DB as Relational Database
    actor Customer as Local Customer (Sharma ji)

    Merchant->>WA: Sends 5s Hindi Voice Note<br/>("Amul doodh expire ho raha hai, sale chalao")
    WA->>GW: POST /webhook (Audio Payload)
    GW->>STT: Stream Audio Bytes
    STT-->>GW: UTF-8 Transcript: "अमूल दूध एक्सपायर हो रहा है..."
    GW->>LG: Execute CampaignStateGraph(raw_input)
    
    LG->>DB: Query inventory (category='dairy', expiry <= 2 days)
    DB-->>LG: 14 packets Amul Taaza Milk (Cost: ₹26, MRP: ₹30)
    
    LG->>SERP: Scrape competitor price ("Amul Taaza 500ml Mumbai")
    SERP-->>LG: Blinkit Price: ₹29 | Zepto Price: ₹30
    
    LG->>LG: Calculate margin-safe clearance price<br/>(₹27.50 -> Undercuts Blinkit, protects >5% margin)
    
    LG->>COG: Query high-affinity dairy customers nearby
    COG-->>LG: 18 regular milk buyers identified
    
    LG->>WA: Send Interactive Campaign Proposal to Merchant<br/>[✅ Approve Clearance] [❌ Cancel]
    Note over LG: Execution Paused (interrupt_before)
    
    Merchant->>WA: Taps [✅ Approve Clearance]
    WA->>GW: POST /webhook (Interactive Callback)
    GW->>LG: Resume StateGraph Execution
    
    LG->>WA: Dispatch personalized Hinglish offers with UPI Link
    WA->>Customer: "Namaste Sharma ji! Aaj Ramesh Kirana par Amul Milk par special offer..."
    Customer->>Merchant: Purchases & pays via Paytm UPI QR
```

### 7.2 Workflow B: Autonomous Sales Anomaly to Khata Escalation

```mermaid
sequenceDiagram
    autonumber
    participant CRON as APScheduler (Hourly)
    participant ANOM as Anomaly Detector
    participant DB as Relational Database
    participant WA as Meta WhatsApp Cloud API
    actor Merchant as Merchant (Ramesh ji)
    participant KHATA as Khata Recovery Agent
    actor Debtor as Customer with Overdue Khata

    CRON->>ANOM: Hourly Trigger: check_store_anomalies()
    ANOM->>DB: Fetch today's sales grouped by category
    DB-->>ANOM: Beverages: ₹180 vs Baseline: ₹1,450 (-87.5%)
    ANOM->>ANOM: Compute EWMA & Z-Score (Z = -2.84, Critical Alert!)
    
    ANOM->>WA: Push Critical WhatsApp Alert with Action Buttons<br/>"Beverages sales down 88%! Launch Cold Drink Offer?"
    WA->>Merchant: Alert delivered to phone screen
    
    ANOM->>KHATA: Trigger Khata Correlation Scan
    KHATA->>DB: Find customers with overdue beverage credit > 21 days
    DB-->>KHATA: 3 customers found with pending balances
    KHATA->>WA: Send gentle automated vernacular reminder with Paytm UPI link
    WA->>Debtor: "Namaste Verma ji, dukaan ka ₹320 ka purana hisab baaki hai..."
```

---

## 8. Innovation & Competitive Differentiation

### 8.1 Comparative Matrix

| Capability / Dimension | Traditional POS / Billing Apps (Vyapar, Tally) | Digital Khata Apps (Khatabook, OkCredit) | Generic AI Chatbot Wrappers (GPT-4 on WhatsApp) | **KiranaMate (MerchantMind AI)** |
| :--- | :--- | :--- | :--- | :--- |
| **Interface / Adoption** | Heavy desktop / tablet app | Standalone mobile application | Text chat interface | **100% WhatsApp Native + Vernacular Voice** |
| **Data Ingestion Friction** | High (Requires manual barcode scan / entry) | Medium (Manual ledger typing) | High (Requires typing every prompt) | **Zero (Listens to Paytm Soundbox webhooks passively)** |
| **Linguistic Accessibility** | English / Hindi menus | Standard UI translations | Generic English/Hindi translation | **Sarvam AI `saaras:v3` tuned for noisy store dialects** |
| **Competitor Awareness** | None (Blind to external market) | None | None (LLM cutoff, no live pricing) | **Live Serper AI scraping of Blinkit, Zepto, Instamart** |
| **Autonomous Action** | None (Passive historical recording) | Basic SMS debt payment reminders | Generates text suggestions, cannot act | **Proactive multi-agent execution with Human-in-the-Loop** |
| **Margin Safety Guardrails**| None | None | None (LLM hallucinated discounts) | **Mathematical margin floor ($Cost \times 1.05$) guarantee** |
| **Customer Memory Model** | Flat customer table | Flat credit balance | Ephemeral LLM context window | **Cognee Semantic Graph of affinities & payment habits** |

### 8.2 Core Innovations

1. **Ambient Commerce Intelligence:**  
   KiranaMate does not wait for user input. It listens to soundbox audio/webhooks and background time-series streams, converting passive payment receipts into proactive commercial interventions.
2. **Vernacular Acoustic Robustness:**  
   Leverages Sarvam AI's Indian speech foundation models designed to decipher regional accents and noisy kirana shop acoustics where standard models fail.
3. **Deterministic Human-in-the-Loop Agent Architecture:**  
   Merges flexible LLM reasoning with deterministic LangGraph execution gates. The AI proposes, calculates, and drafts, but financial execution is strictly gated behind a single merchant WhatsApp button tap.
4. **Mathematical Margin Floor Guarantee:**  
   Eliminates the danger of generative AI hallucinations in pricing by wrapping LLM creative output in strict mathematical margin bounds ($P_{final} \ge C_{unit} \times 1.05$).

---

## 9. Technology Stack Defense

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           TECHNOLOGY STACK JUSTIFICATION                          │
├─────────────────────┬───────────────────────────┬─────────────────────────────────┤
│ Layer               │ Selected Technology       │ Strategic Rationale             │
├─────────────────────┼───────────────────────────┼─────────────────────────────────┤
│ Backend Gateway     │ FastAPI + Uvicorn (Async) │ Ultra-low latency webhook I/O   │
│ Messaging Backbone  │ Meta WhatsApp Cloud API   │ Zero friction, 100% daily open  │
│ Voice Intelligence  │ Sarvam AI (saaras:v3)     │ SOTA vernacular Indian speech   │
│ Agent Framework     │ LangGraph StateGraph      │ Stateful cyclic graphs & gates  │
│ Primary Reasoning   │ Google Gemini 1.5 / 2.0   │ Large context & JSON accuracy   │
│ Semantic Memory     │ Cognee Knowledge Graph    │ Complex customer-product graphs │
│ Competitor Intel    │ Serper AI Web Scraper     │ Real-time pincode pricing       │
│ Payment Processing  │ Paytm Soundbox Webhooks   │ Ubiquitous Indian retail UPI    │
│ Reporting Engine    │ ReportLab Vector PDF      │ Executive-grade diagnostic PDFs │
│ Real-Time UI Sync   │ Server-Sent Events (SSE)  │ Lightweight live web streaming  │
└─────────────────────┴───────────────────────────┴─────────────────────────────────┘
```

---

## 10. Repository Directory & Component Index

```
kiranamate/
├── agents/                         # Autonomous Agent Workflows
│   ├── sales_monitor.py            # Hourly EWMA sales anomaly detector
│   ├── campaign_executor.py        # 7-node LangGraph clearance campaign engine
│   ├── weekly_report.py            # Sunday 7 PM 4-pillar health audit generator
│   └── khata_recovery.py           # Automated vernacular debt recovery agent
│
├── api/                            # FastAPI Application Layer
│   ├── main.py                     # App lifespan, router mounting & static files
│   ├── routes_webhook.py           # Meta WhatsApp & Paytm webhook endpoints
│   ├── routes_campaign.py          # Campaign trigger, status & resume APIs
│   ├── routes_merchant.py          # Merchant inventory, sales & analytics routes
│   └── routes_health.py            # System health & diagnostic endpoints
│
├── core/                           # External Service Clients & Integrations
│   ├── whatsapp_client.py          # Meta Cloud API wrapper (text, buttons, PDF)
│   ├── sarvam_client.py            # Sarvam AI saaras:v3 voice transcription client
│   ├── serper_client.py            # Serper Google/Blinkit/Zepto live pricing scraper
│   ├── cognee_client.py            # Cognee Knowledge Graph semantic memory client
│   ├── paytm_client.py             # Paytm Soundbox webhook formatter & UPI deep-links
│   ├── trace_bus.py                # In-memory event bus for real-time SSE streaming
│   └── tunnel_manager.py           # Auto-registration for local development tunnels
│
├── db/                             # Data Layer & Schemas
│   ├── database.py                 # Asynchronous SQLAlchemy database engine
│   ├── models.py                   # Schemas: Merchant, Product, Transaction, Khata
│   └── seed.py                     # Demo data generator (realistic Kirana store)
│
├── dashboard/                      # Merchant Live Command Center
│   ├── index.html                  # Single-page glassmorphism command center
│   ├── style.css                   # Custom CSS (dark mode, glassmorphism, animations)
│   └── app.js                      # SSE event receiver, Chart.js metrics & trigger controls
│
├── utils/                          # Math, Heuristics & Diagnostics
│   ├── anomaly_detector.py         # Rolling EWMA, baseline & Z-score calculations
│   ├── discount_calculator.py      # Margin-safe clearance pricing & revenue recovery
│   └── report_generator.py         # ReportLab in-memory vector PDF document builder
│
├── n8n_workflows/                  # Visual Automation Blueprints
│   └── workflows.json              # Exported n8n workflow for webhook routing
│
├── .env.example                    # Environment variables blueprint
├── requirements.txt                # Pinned production Python dependencies
├── Dockerfile                      # Production container image configuration
└── docker-compose.yml              # App + PostgreSQL + Redis full stack definition
>>>>>>> origin/main
```

---

<<<<<<< HEAD
## Quick Start

### 1. Clone & Setup Environment

```bash
git clone <repo>
cd kiranamate
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start with Docker (Recommended)

```bash
docker-compose up --build
```

This starts:
- **FastAPI backend** on `http://localhost:8000`
- **PostgreSQL** on port 5432
- **Redis** on port 6379 (for LangGraph state persistence)

### 4. Seed Demo Data
=======
## 11. Installation & Deployment Guide

### Prerequisites
- Python 3.11+
- PostgreSQL & Redis (or use the included `docker-compose.yml`)
- Meta WhatsApp Cloud API credentials
- Sarvam AI, Google Gemini, and Serper API keys

### Step 1: Clone and Configure Environment

```bash
git clone https://github.com/your-org/kiranamate.git
cd kiranamate
cp .env.example .env
```

Edit `.env` with your active service credentials:

```env
# Primary LLM
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.0-flash

# Vernacular Voice
SARVAM_API_KEY=sk_sarvam_...

# Competitor Scraper
SERPER_API_KEY=serper_api_key_...

# WhatsApp Cloud API
WHATSAPP_TOKEN=EAAG...
WHATSAPP_PHONE_ID=1092837465...
WHATSAPP_VERIFY_TOKEN=kiranamate_secret_token

# Paytm Merchant Credentials
PAYTM_MERCHANT_KEY=paytm_key_...
PAYTM_MERCHANT_ID=paytm_mid_...

# Database & Cache
DATABASE_URL=sqlite+aiosqlite:///./kiranamate.db
# Or for PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kiranamate
REDIS_URL=redis://localhost:6379/0
```

### Step 2: Install Dependencies

```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Seed Realistic Demo Data
>>>>>>> origin/main

```bash
python db/seed.py
```
<<<<<<< HEAD

### 5. Run the API

```bash
uvicorn api.main:app --reload --port 8000
```

### 6. API Docs

Visit `http://localhost:8000/docs` for the full Swagger UI.

---

## Environment Variables (`.env`)

```env
# LLM
GEMINI_API_KEY=your_gemini_key          # Primary LLM (JSON & Reasoning)
OPENAI_API_KEY=your_openai_key          # Fallback + Whisper + DALL-E

# Voice
SARVAM_API_KEY=your_sarvam_key          # Vernacular voice transcription

# Memory
COGNEE_API_KEY=your_cognee_key          # Knowledge graph

# Web Intelligence
SERPER_API_KEY=your_serper_key          # Competitor pricing scrape

# Messaging
WHATSAPP_TOKEN=your_meta_token          # Meta WhatsApp Business API
WHATSAPP_PHONE_ID=your_phone_id

# Payments
PAYTM_MERCHANT_KEY=your_paytm_key
PAYTM_MERCHANT_ID=your_merchant_id

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/kiranamate

# Redis (LangGraph state)
REDIS_URL=redis://localhost:6379

# Image Generation
STABILITY_API_KEY=your_stability_key   # Stable Diffusion 3.5
```

---

## Three Demo Scenarios

| Scenario | Trigger | What Happens |
|---|---|---|
| **Voice Clearance** | POST /campaign/voice | 5s voice → full WhatsApp campaign in 90s |
| **Anomaly Alert** | Cron / POST /monitor/check | 41% dairy drop → auto WhatsApp alert + khata recovery |
| **Sunday Report** | Cron (Sun 7PM) / POST /report/generate | 0-100 health score PDF via WhatsApp |

---

## N8N Setup

1. Open N8N (`http://localhost:5678` if using docker-compose)
2. Import `n8n_workflows/workflows.json`
3. Set credentials for WhatsApp, Paytm, and the FastAPI webhook URL
4. Activate all 3 workflows
=======
*Populates the database with 50+ realistic Kirana products (Amul Milk, Britannia Bread, Aashirvaad Atta, Maggi Noodles), 14 days of simulated Paytm transactions, customer profiles, and open khata debt.*

### Step 4: Run the Backend Service

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Documentation (Swagger UI):** `http://localhost:8000/docs`
- **Live Glassmorphism Command Center:** `http://localhost:8000/dashboard/`

### Step 5: Docker Deployment (Production Alternative)

```bash
docker-compose up --build -d
```
Spins up FastAPI, PostgreSQL 16, and Redis with persistent volumes and automated health checks.

---

## 12. API Reference & Webhook Contract

### Webhook Endpoints (`api/routes_webhook.py`)

#### 1. Meta WhatsApp Webhook Handshake
- **Endpoint:** `GET /webhook`
- **Query Parameters:** `hub.mode`, `hub.verify_token`, `hub.challenge`
- **Response:** Returns `hub.challenge` on valid token match.

#### 2. WhatsApp Inbound Messages & Interactive Callbacks
- **Endpoint:** `POST /webhook`
- **Description:** Ingests WhatsApp text messages, voice note media payloads, and interactive button clicks (`[Approve]`, `[Cancel]`, `[Details]`).

#### 3. Paytm Soundbox Transaction Webhook
- **Endpoint:** `POST /webhook/paytm`
- **Sample Request Body:**
  ```json
  {
    "merchant_id": "MERC_001",
    "transaction_id": "TXN_987654321",
    "amount": 60.00,
    "category": "dairy",
    "payment_mode": "UPI_SOUNDBOX",
    "timestamp": "2026-09-19T08:30:00Z"
  }
  ```

---

### Campaign Control Endpoints (`api/routes_campaign.py`)

#### 1. Voice Campaign Initiation
- **Endpoint:** `POST /campaign/voice`
- **Payload:** `multipart/form-data` with audio file or audio URL.
- **Action:** Transcribes via Sarvam AI, initiates LangGraph StateGraph, and returns campaign preview ID.

#### 2. Manual Trigger / Resume Campaign
- **Endpoint:** `POST /campaign/{campaign_id}/approve`
- **Action:** Resumes LangGraph execution from approval checkpoint, broadcasting WhatsApp messages to target segment.

---

## 13. Anticipated Questions & Technical Defense

#### Q1: "Why not simply build a lightweight mobile app instead of relying on WhatsApp?"
> **Defense:** Indian Kirana owners work 14–16 hours daily. Industry data reveals that standalone Kirana apps suffer from 80%+ 90-day churn. WhatsApp is already opened 50+ times a day by merchants; building on Meta WhatsApp Cloud API guarantees **100% interface adoption with zero learning curve**.

#### Q2: "How does the system ensure an LLM doesn't hallucinate an unprofitable discount?"
> **Defense:** We enforce a strict separation of concerns. While the LLM generates creative Hinglish messaging, **all pricing calculations are handled by a deterministic Python mathematical engine (`discount_calculator.py`)**. The discount is hard-clamped to never breach the wholesale cost floor plus a 5% minimum margin: $P_{final} \ge C_{unit} \times 1.05$.

#### Q3: "Kirana stores rarely maintain digital barcode inventory. How can this work in practice?"
> **Defense:** KiranaMate requires zero initial barcode scanning. It infers inventory turnover directly from **Paytm Soundbox transaction amounts and payment notes**. Additionally, the merchant can update stock at any moment by speaking a 5-second voice note (*"10 packet bread aaye hain"*).

#### Q4: "How does Sarvam AI compare to OpenAI Whisper in a noisy Kirana environment?"
> **Defense:** Standard Whisper models struggle with mixed Hinglish syntax and loud Indian street acoustic backgrounds (horns, chatter, fans). Sarvam AI’s `saaras:v3` model is trained specifically on regional Indian speech acoustics, achieving significantly higher Word Error Rate (WER) resilience on everyday Kirana vernacular speech.

---

## 👥 Contributors & Hackathon Team

- **KiranaMate Engineering Team** — Built with passion for empowering India's local retail heroes.
- **License:** MIT Open Source — Free to adapt, build upon, and scale.
