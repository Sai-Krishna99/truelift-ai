# TrueLift AI - Session Handover Document

## 🎯 Project Vision & Context

**Hackathon**: 
- Google Cloud AI Partner Catalyst - Confluent Challenge (Deadline: Dec 31, 2025)
- URL - https://ai-partner-catalyst.devpost.com/?ref_feature=challenge&ref_medium=your-open-hackathons&ref_content=Submissions+open

**Problem Statement**: Retailers run promotions expecting "Gross Lift" (total sales increase) but often experience **promotional cannibalization** - where discounted items steal sales from full-price items, resulting in misleading metrics and revenue loss. The actual benefit ("True Lift") is much lower than reported.

**Solution**: TrueLift AI - A real-time event-driven system that:
1. Detects promotional cannibalization as it happens
2. Uses AI (Gemini) to explain WHY it's occurring
3. Recommends actionable strategies to fix it
4. Tracks action effectiveness through feedback loops
5. Learns and improves over time

---

## 🆕 Latest Session Updates (Dec 2025)
- DEMO bursts now carry `burst_id` end-to-end; UI badges are reliable (no time-window guessing).
- Actions publish with price context; simulator honors stop/price; feedback-loop computes real impact and caches to Redis; backend surfaces effectiveness/sales/price deltas.
- UI: compact impact badges; modal auto-flips from pending → measured when feedback arrives; pricing context visible; demo onboarding strip added.
- Infra fixes: Redis wiring corrected across services; feedback-loop consumer group set; Decimal/float issues patched.

---

## 🏗️ System Architecture

**Tech Stack**:
- **Streaming**: Apache Kafka (Confluent 7.5.0) - 3 topics
- **ML/AI**: Isolation Forest (anomaly detection) + Google Gemini 2.5 Flash (strategy generation)
- **Backend**: Python 3.11, FastAPI, PostgreSQL 15, Redis 7
- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
- **Infrastructure**: Docker Compose (10 microservices)

**Event Flow**:
```
Virtual Shoppers → Kafka (shopping-events) 
  → ML Detector (aggregates 1-min windows, detects cannibalization)
    → Kafka (cannibalization-alerts)
      → Gemini Agent (generates AI strategies)
        → PostgreSQL (stores strategies)
          → Backend API → Frontend Dashboard
            → User Actions → Kafka (user-actions)
              → Feedback Loop (tracks effectiveness)
```

---

## 📂 Key Files & What They Do

### **Services** (`/services/`)

1. **`virtual-shoppers/simulator.py`**
   - Generates 8-15 shopping events/min
   - Simulates cannibalization (marks some events as cannibalized)
   - Publishes to Kafka `shopping-events` topic

2. **`ml-detector/detector.py`** ⭐ (CRITICAL - Recently Fixed)
   - Consumes from `shopping-events`
   - Aggregates sales in 1-minute windows
   - Compares actual vs predicted sales
   - Uses Isolation Forest for anomaly detection
   - **Fixed Issues**: Kafka heartbeat timeouts, Decimal JSON serialization
   - Publishes alerts to Kafka `cannibalization-alerts` topic
   - **Key Config** (lines 54-66): Kafka consumer with `session_timeout_ms=30000`, `max_poll_interval_ms=300000`

3. **`gemini-agent/agent.py`** ⭐ (CRITICAL - Recently Upgraded)
   - Consumes from `cannibalization-alerts`
   - Calls Gemini 2.5 Flash to generate strategies
   - **Upgraded**: Old SDK (`google-generativeai`) → New SDK (`google-genai`)
   - **Model**: `gemini-2.5-flash` (best price-performance)
   - Falls back to default strategy if API quota exceeded
   - Stores strategies in PostgreSQL `ai_strategies` table
   - **Key Code** (lines 28-29): `self.client = genai.Client(api_key=self.gemini_api_key)`
   - **Key Code** (lines 136-140): `self.client.models.generate_content(model='gemini-2.5-flash', contents=prompt)`

4. **`feedback-loop/processor.py`**
   - Consumes from `user-actions` topic
   - Tracks before/after metrics
   - Calculates action effectiveness scores
   - **Status**: Service exists but needs user actions to trigger

### **Backend** (`/backend/main.py`)

- FastAPI REST API with 7 endpoints:
  - `GET /health` - Health check
  - `GET /alerts` - List alerts (prioritizes `strategy_generated` status)
  - `GET /alerts/{alert_id}` - Get alert with full strategy details
  - `GET /promotions` - List promotions
  - `POST /actions` - Record user action (publishes to Kafka)
  - `GET /dashboard/stats` - Dashboard metrics
  - `WebSocket /ws` - Real-time updates

- **Recent Fixes**:
  - Line 135-145: Handles JSON vs dict for `recommended_action` and `alternatives`
  - Line 129-150: Prioritizes alerts with strategies in results

### **Frontend** (`/frontend/app/page.tsx`)

- Next.js dashboard with:
  - Real-time alert listing (polls every 10s)
  - Clickable alerts open modal with AI strategy
  - Action buttons: Stop Promotion, Adjust Price, Dismiss
  - **Recent Fix** (line 289): Shows buttons for `strategy_generated` status (not just `pending`)
  - **Key Functions**:
    - `handleAlertClick()` (line 70): Fetches full alert details
    - `handleAction()` (line 80): Posts action to backend

### **Database** (`/infrastructure/`)

1. **`init.sql`** - Schema (6 tables):
   - `promotions` - Product promotions with predicted sales
   - `sales_events` - Individual shopping events
   - `cannibalization_alerts` - Detected issues
   - `ai_strategies` - Gemini-generated recommendations
   - `user_actions` - Actions taken by users
   - `feedback_loop` - Effectiveness tracking

2. **`seed_data.sql`** - Auto-loads 4 promotions on startup:
   - PROMO001: Premium Coffee Beans ($18.99)
   - PROMO002: Organic Protein Powder ($34.99)
   - PROMO003: Smart Watch Series X ($249.99)
   - PROMO004: Designer Sunglasses ($89.99)
   - All set with `predicted_sales=50000` to trigger alerts

### **Scripts** (`/scripts/`)

- **`generate_strategies.py`** - Manual fallback script
  - Finds alerts without strategies
  - Inserts default fallback strategies
  - Useful when Gemini agent is down or for testing
  - Run: `docker-compose exec backend-api python scripts/generate_strategies.py`

---

## ✅ What's Working (Current State)

1. **Event Generation** ✅
   - Virtual shoppers generating 8-15 events/min
   - Events flowing to Kafka `shopping-events` topic

2. **Cannibalization Detection** ✅
   - ML Detector consuming events
   - 1-minute aggregation windows working
   - Publishing alerts to Kafka `cannibalization-alerts` topic
   - Alerts stored in PostgreSQL

3. **AI Strategy Generation** ✅
   - Gemini Agent consuming alerts from Kafka
   - Real Gemini 2.5 Flash API working (when quota available)
   - Graceful fallback when quota exceeded
   - Strategies stored in `ai_strategies` table

4. **Dashboard** ✅
   - Alerts display with real-time polling
   - Click alert → Modal shows AI explanation + recommendations
   - Action buttons visible (Stop Promotion, Adjust Price, Dismiss)

5. **Auto-Seeding** ✅
   - Database auto-seeds 4 promotions on `docker-compose up`
   - No manual seeding needed

---

## 🚧 What's Pending (Next Session Tasks)

### Product & Demo Realism
- Increase SKU/promo variety and diversify price/discount patterns for richer demos.

### Onboarding & UX
- Add concise “How this works” strip and clarify actions vs alerts; minor polish.

### Deployment Plan
- Draft runbook for GCP + Confluent Cloud: Cloud Run (min scale 0), Kafka cost controls, Redis/DB choices, secrets/envs.

### Optional Polish
- Finish eliminating remaining polling in favor of WebSocket-only updates; microcopy tweaks.

## 🧭 Design/Deploy Considerations (to align on)
- **Demo vs Live**: Default to demo mode (preseed + bursts) with a visible toggle; keep live mode available but off to avoid quota/costs.
- **Tagging Reliability**: Attach a `burst_id` or `queued_at` from backend to events/alerts; UI tags by that instead of timestamp guesswork.
- **Quota/Cost**: Keep Gemini calls cached/throttled; prefer fallback/seeded strategies. Cloud Run with min instances 0; Kafka/simulator off by default in cloud.
- **Realistic Numbers**: Clamp loss%/loss$; ensure predicted/actual ranges are believable for the demo.
- **Confluent Cloud + GCP**: Plan to swap local Kafka to Confluent Cloud and deploy services on Cloud Run; ensure this covers the second sponsor tech for the hackathon.

---

## 🐛 Known Issues & Fixes Applied

### **Issue 1: Kafka Heartbeat Timeouts** (FIXED ✅)
- **Problem**: Services stuck in reconnection loops
- **Files**: `/services/ml-detector/detector.py`, `/services/gemini-agent/agent.py`
- **Fix**: Added `session_timeout_ms=30000`, `heartbeat_interval_ms=10000`, `max_poll_interval_ms=300000`

### **Issue 2: Decimal JSON Serialization** (FIXED ✅)
- **Problem**: PostgreSQL returns Decimal, JSON can't serialize
- **File**: `/services/ml-detector/detector.py`
- **Fix**: Added `decimal_to_float()` helper (line 18), convert before Kafka publish (line 174)

### **Issue 3: Gemini SDK Outdated** (FIXED ✅)
- **Problem**: Using old `google-generativeai` SDK with deprecated model names
- **File**: `/services/gemini-agent/agent.py`, `requirements.txt`
- **Fix**: Upgraded to `google-genai`, using `gemini-2.5-flash` model

### **Issue 4: Action Buttons Not Showing** (FIXED ✅)
- **Problem**: Buttons only showed for `status='pending'`, but alerts have `status='strategy_generated'`
- **File**: `/frontend/app/page.tsx` (line 289)
- **Fix**: Changed condition to show buttons unless `status='action_taken'` or `status='resolved'`

---

## 🔧 How to Run Locally

```bash
# Start all services
cd /home/saikrishnaj/projects/truelift-ai
docker-compose down -v  # Clean slate (removes volumes)
docker-compose up -d --build

# Wait ~30 seconds for Kafka to be healthy, then check
docker-compose ps  # All should be "Up" or "Up (healthy)"

# Access dashboard
open http://localhost:3000

# Check logs if issues
docker-compose logs -f gemini-agent  # See AI strategy generation
docker-compose logs -f ml-detector    # See cannibalization detection
docker-compose logs -f backend-api    # See API requests
```

**Database auto-seeds on startup**, so alerts should start appearing within 1-2 minutes.

---

## 🎯 Hackathon Demo Flow

1. **Show Dashboard** - Real-time alerts appearing
2. **Click Alert** - Modal shows AI explanation + recommendations
3. **Show Gemini Strategy** - Point out AI-generated vs fallback
4. **Click Action Button** - (TODO: Wire to Kafka + show confirmation)
5. **Show Feedback Loop** - (TODO: Track effectiveness metrics)
6. **Explain Architecture** - Event-driven, microservices, real-time ML

---

## 📝 Environment Variables

**Required** (in `.env`):
```env
GEMINI_API_KEY=your_api_key_here  # Get from https://aistudio.google.com/apikey
```

**All other vars have defaults** in `docker-compose.yml` and work out-of-the-box.

---

## 🔗 Important References

- **Gemini API Docs**: https://ai.google.dev/gemini-api/docs/quickstart
- **Confluent Kafka**: https://docs.confluent.io/
- **Project README**: `/home/saikrishnaj/projects/truelift-ai/README.md`
- **Architecture Diagrams**: Mentioned in README (workflow + architecture images)

---

## 💡 Key Insights for Next Session

1. **Action buttons exist but don't publish to Kafka** - This is the #1 priority
2. **Feedback loop service is idle** - Needs user actions to activate
3. **Gemini API quota resets daily** - Free tier has limits, graceful fallback works
4. **Database auto-seeds** - No manual setup needed on fresh start
5. **Frontend polls every 10s** - Consider WebSocket for true real-time

**Start next session with**: "Let's wire the action buttons to publish to Kafka and activate the feedback loop"
