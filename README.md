# Magicpin Vera AI Challenge — Merchant AI Assistant Submission

This repository contains a competition-ready, production-grade AI solution for **Magicpin Vera**, Magicpin's AI assistant for merchants.

## 🌟 Overview & Architecture

Vera is designed around the **4-Context Framework**:
1. **Category Context**: Slow-changing vertical knowledge (dentists, salons, restaurants, gyms, pharmacies) including clinical tone, taboo lists, peer statistics, offer catalogs, and research digests.
2. **Merchant Context**: Specific merchant state, performance metrics (views, calls, CTR vs. peer benchmarks), active catalog offers, and locality identity.
3. **Trigger Context**: Event driving the outreach right now (research digest release, performance spike/dip, seasonal events, IPL matches, customer recall, review theme).
4. **Customer Context** (optional): Patient/customer profile, visit history, preferred channels/times, and consent data for customer-facing messages.

```
┌─────────────────────────┐          ┌──────────────────────────┐
│   Magicpin Contexts     │ ───────► │   ContextStore           │
│ (Category, Merchant,    │          │  (In-Memory Idempotent)  │
│  Trigger, Customer)     │          └────────────┬─────────────┘
└─────────────────────────┘                       │
                                                  ▼
┌─────────────────────────┐          ┌──────────────────────────┐
│   Judge / Simulator /   │ ───────► │   FastAPI Server         │
│   WhatsApp Harness      │ ◄─────── │  (5 REST Endpoints)      │
└─────────────────────────┘          └────────────┬─────────────┘
                                                  │
                        ┌─────────────────────────┴────────────────────────┐
                        ▼                                                  ▼
         ┌─────────────────────────────┐                    ┌────────────────────────────┐
         │ CompositionEngine           │                    │ ReplyHandler               │
         │ - Category Voice Rules      │                    │ - Auto-reply Detector      │
         │ - Concrete Specificity      │                    │ - Intent Transition Router │
         │ - Single Binary/Low-Fr. CTA │                    │ - Hostile Opt-Out Exits    │
         └─────────────────────────────┘                    └────────────────────────────┘
```

---

## 🚀 Key Technical Highlights

1. **Category-Specific Tone & Taboo Compliance**:
   - **Dentists**: Clinical, peer-to-peer, `Dr.` prefix required, taboos enforced (no "cure", no "guaranteed").
   - **Salons**: Warm, friendly, fellow-operator voice, practical grooming packages.
   - **Restaurants**: Operator-to-operator, covers, match-night delivery reframing, AOV optimization.
   - **Gyms**: Motivational coaching, no-shame winback, member retention, seasonal dip reframe.
   - **Pharmacies**: Precise molecule names, batch numbers, senior citizen discount respect, namaste salutation.

2. **Concrete Specificity & Verified Data Anchors**:
   - Anchors outreach on actual numbers (e.g. `2,100-patient trial`, `38% caries reduction`, `JIDA Oct 2026, p.14`, `views +28%`, `6,777 missed searches`, `Haircut @ ₹99`).
   - Zero hallucinated offers or fabricated research citations.

3. **Intelligent Multi-Turn Reply Handling**:
   - **Auto-Reply Pollution**: Detects WhatsApp Business canned messages ("Thank you for contacting us...") and exits gracefully without burning turns.
   - **Intent Transitions**: Immediately transitions to action execution mode when merchants express intent ("yes let's do it", "mujhe join karna hai") instead of asking redundant qualification questions.
   - **Hostile Handling**: Respects opt-outs ("stop", "spam") immediately and gracefully terminates the session.

---

## 🛠️ API Endpoints Summary

All 5 mandatory endpoints are fully implemented in `bot.py`:

- **`GET /v1/healthz`**: Liveness probe returning status and context load counts.
- **`GET /v1/metadata`**: Returns team identity, model, version, and architecture approach.
- **`POST /v1/context`**: Idempotent context push endpoint (`scope`, `context_id`, `version`, `payload`).
- **`POST /v1/tick`**: Evaluates available triggers and returns proactive outbound actions (< 30s latency, max 20 actions per tick).
- **`POST /v1/reply`**: Synchronous reply handling returning `send`, `wait`, or `end`.

---

## 💻 Local Setup & Execution

### 1. Prerequisites & Installation

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Generate the Dataset & Submission

```bash
# Expand dataset from seeds
python dataset/generate_dataset.py --seed-dir ./dataset --out ./expanded

# Generate canonical 30-line submission.jsonl
python generate_submission.py
```

### 3. Start the API Server

```bash
python -m uvicorn bot:app --host 0.0.0.0 --port 8080
```

---

## 🧪 Testing & Evaluation

### Run Automated Unit Tests

In a separate terminal window while the server is running:

```bash
python test_bot.py
```

### Run official `judge_simulator.py`

```bash
python judge_simulator.py
```

---

## 🌐 Public Cloud Deployment

To deploy for official evaluation:

1. **Render / Fly.io / Railway / AWS / GCP**:
   - Set start command: `uvicorn bot:app --host 0.0.0.0 --port $PORT`
2. **ngrok Tunnel (for local evaluation)**:
   ```bash
   ngrok http 8080
   ```
3. Submit your HTTPS endpoint URL via the submission portal.

---

## 📝 Team Metadata

- **Team Name**: Team Magicpin Vera Architect
- **Model**: Hybrid Policy & Context Composition Engine
- **Version**: 1.0.0
