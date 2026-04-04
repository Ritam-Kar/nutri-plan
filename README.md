# 🥗 NutriPlan — AI-Powered Weekly Meal Planner

> A multi-agent AI system built with Google ADK and Gemini 2.5 Flash that plans your week of meals, analyses nutrition, builds your grocery list, finds nearby stores, and emails the complete plan to you.

---

## 🌐 Live Demo

- **Web UI:** https://nutri-plan-965093005624.us-central1.run.app/dev-ui/
- **API Endpoint:** https://nutri-plan-965093005624.us-central1.run.app/run

---

## 📌 Problem Statement

**Multi-Agent Productivity Assistant** — Build a multi-agent AI system that helps users manage tasks, schedules, and information by interacting with multiple tools and data sources.

NutriPlan addresses this by managing:
- 📅 Weekly meal **scheduling** with per-meal nutrition
- 🛒 Grocery **task list** with costs and quantities
- 📍 Location-aware **store information**
- 📧 **Information delivery** via email

---

## 🤖 Agent Architecture

NutriPlan uses a **5-agent sequential pipeline** coordinated by a root LlmAgent, with an optional email agent triggered on user request.

root_agent (LlmAgent — coordinator)
│
├── planning_pipeline (SequentialAgent)
│       │
│       ├── 1. profile_agent       → Extracts user preferences to session state
│       ├── 2. meal_planner_agent  → Creates 7-day meal plan with inline nutrition
│       ├── 3. recipe_nutrition_agent → Verifies nutrition via MCP tool
│       ├── 4. grocery_agent       → Builds categorised grocery list with INR costs
│       └── 5. storefinder_agent   → Finds nearby stores + presents complete output
│
└── email_agent                    → Emails complete plan on user request

### Agent Responsibilities

| Agent | Role | Output |
|---|---|---|
| `profile_agent` | Extracts dietary restrictions, budget, location, calorie/macro targets | JSON to session state |
| `meal_planner_agent` | Creates 7-day Indian meal plan with per-meal nutrition inline | Meal plan to session state |
| `recipe_nutrition_agent` | Verifies nutrition estimates using USDA/Open Food Facts MCP | Verification note |
| `grocery_agent` | Consolidates all ingredients, estimates INR costs, groups by category | Grocery list to session state |
| `storefinder_agent` | Finds nearby supermarkets via Google Maps API, presents final output | Complete formatted response |
| `email_agent` | Compiles and emails the full plan via Gmail SMTP | Email confirmation |

---

## 🛠️ Tools & MCP Servers

| Tool | Type | Purpose |
|---|---|---|
| **Nutrition MCP** | Custom Python MCP server | Fetches nutrition data from Open Food Facts & USDA FoodData Central APIs |
| **Google Maps API** | FunctionTool (direct httpx calls) | Geocoding, nearby store search, distance matrix |
| **Gmail SMTP** | FunctionTool | Sends formatted HTML email with complete plan |

### Why FunctionTools instead of MCP for Maps & Email?

Google ADK installs a `sitecustomize` hook that intercepts all Python subprocess calls and redirects them to the ADK web server. This makes MCP servers launched via `subprocess`/`StdioServerParameters` unreliable on Cloud Run. Maps and Email are implemented as async `FunctionTool`s that run directly in the agent process — no subprocess required.

The Nutrition MCP (`nutrition_mcp_server.py`) works because it is called via `sys.executable` pointing to the same Python process, which ADK handles correctly.

---

## 📁 Project Structure
nutri-plan/
├── nutri_plan/
│   ├── init.py              # ADK agent module entry point
│   └── agent.py                 # All agents, tools, root_agent definition
├── nutrition_mcp_server.py      # Custom MCP server for nutrition data
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container definition (Python 3.13-slim)
├── entrypoint.sh                # ADK web server startup script
├── .gitignore                   # Excludes service-account.json and credentials
└── README.md                    # This file

---

## 💬 Example Interaction

**User:**
3 people, non-vegetarian, no seafood, ₹6000 weekly budget,
2000 kcal/day per person, 120g protein/day, Bhubaneswar

**NutriPlan responds with:**
🥗 NUTRIPLAN — YOUR WEEKLY PLAN
📅 7-DAY MEAL PLAN WITH NUTRITION
Day 1 — Monday
🌅 Breakfast — Masala Omelette (3 eggs) + 2 Whole Wheat Rotis + Skim Milk
Calories: ~450 kcal  |  Protein: 30g  |  Carbs: 42g  |  Fat: 17g
☀️ Lunch — Chicken Curry (200g) + Brown Rice + Salad
Calories: ~700 kcal  |  Protein: 65g  |  Carbs: 60g  |  Fat: 22g
🌙 Dinner — Dal Makhani + 2 Rotis + Mixed Vegetable Sabzi
Calories: ~810 kcal  |  Protein: 34g  |  Carbs: 110g  |  Fat: 28g
Day Total — ~1960 kcal  |  Protein: 129g  |  Carbs: 212g  |  Fat: 67g
[...continues for all 7 days...]
🛒 GROCERY LIST
VEGETABLES
Onion           2.5 kg     ₹100
Tomato          2 kg       ₹60
[...]
TOTAL ESTIMATED COST  ₹XXXX
🏪 NEAREST STORES

Reliance Fresh
Galaxy Mall, Patia, Bhubaneswar
4.8 km   12 mins

📧 Want me to email this plan to you? Just share your email address!

**User:** `send to myemail@gmail.com`

**NutriPlan:** `✅ Plan sent! Check your inbox.`

---

## 🚀 Tech Stack

| Component | Technology |
|---|---|
| Agent Framework | Google Agent Development Kit (ADK) 1.28+ |
| LLM | Gemini 2.5 Flash via Vertex AI |
| Authentication | Application Default Credentials (ADC) |
| Nutrition Data | Open Food Facts API + USDA FoodData Central (both free, no key) |
| Maps & Location | Google Maps Platform (Geocoding, Places, Distance Matrix APIs) |
| Email | Gmail SMTP with App Password |
| Containerisation | Docker (Python 3.13-slim) |
| Deployment | Google Cloud Run (us-central1) |
| Container Registry | Google Container Registry (gcr.io) |
| Cloud Project | nutri-plan-26 |

---

## ⚙️ Environment Variables

| Variable | Description |
|---|---|
| `GOOGLE_MAPS_API_KEY` | Google Maps Platform API key |
| `GMAIL_USER` | Gmail address used to send emails |
| `GMAIL_APP_PASSWORD` | 16-character Gmail App Password |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID (`nutri-plan-26`) |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI region (`us-central1`) |
| `GOOGLE_GENAI_USE_VERTEXAI` | Set to `true` to use Vertex AI |

---

## 🏃 Running Locally

### Prerequisites
- Google Cloud SDK installed and authenticated
- Docker installed
- Google Maps API key
- Gmail App Password

### Steps
```bash
# Clone the repo
git clone https://github.com/Ritam-Kar/nutri-plan.git
cd nutri-plan

# Authenticate with Google Cloud
gcloud auth application-default login
gcloud config set project nutri-plan-26

# Build Docker image
docker build -t nutri-plan-fresh .

# Run locally
docker run --rm -p 8080:8080 \
  -v ~/.config/gcloud:/root/.config/gcloud \
  -e GOOGLE_MAPS_API_KEY="your_maps_api_key" \
  -e GMAIL_USER="your@gmail.com" \
  -e GMAIL_APP_PASSWORD="your_app_password" \
  nutri-plan-fresh

# Open in browser
open http://localhost:8080/dev-ui/
```

---

## ☁️ Deploying to Cloud Run
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/nutri-plan-26/nutri-plan-fresh .

# Get image digest
gcloud container images describe gcr.io/nutri-plan-26/nutri-plan-fresh \
  --format="value(image_summary.digest)" > /tmp/digest.txt
IMAGE_DIGEST=$(cat /tmp/digest.txt)

# Deploy
gcloud run deploy nutri-plan \
  --image=gcr.io/nutri-plan-26/nutri-plan-fresh@$IMAGE_DIGEST \
  --region=us-central1 \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --set-env-vars="GOOGLE_MAPS_API_KEY=...,GMAIL_USER=...,GMAIL_APP_PASSWORD=..."
```

---

## 🔑 Key Design Decisions

**Sequential pipeline over parallel agents** — Each agent's output feeds the next via session state (`output_key`). This ensures the grocery list is based on the actual meal plan, and the final output includes all prior context.

**FunctionTools over MCP for Maps and Email** — ADK's subprocess interception on Cloud Run made external MCP servers unreliable. Direct async HTTP calls via `httpx` inside FunctionTools are process-local, reliable, and faster.

**Gemini 2.5 Flash via Vertex AI** — No API key required. Uses Application Default Credentials tied to the GCP project billing account, avoiding AI Studio quota limits.

**Single container deployment** — All agents, the nutrition MCP server, and the ADK web UI are served from one Cloud Run container on port 8080, keeping deployment simple and cost-effective.

---

## 👤 Author

**Ritam Kar**
- GitHub: [@Ritam-Kar](https://github.com/Ritam-Kar)
- Project: NutriPlan (Multi-Agent Productivity Assistant track)