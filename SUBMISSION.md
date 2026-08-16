# Social Threat Analyzer — Technical Documentation & Submission Guide

This document provides a comprehensive technical overview of the **Social Threat Analyzer** repository, including system architecture, API documentation, folder structure, database schema, and deployment instructions.

---

## 1. Project Overview & Capabilities
The **Social Threat Analyzer** is an enterprise-grade public safety intelligence dashboard. It ingests, translates, classifies, and visualizes real-time social media text, images, and metadata to detect public safety threats, bot networks, and incitement trends. 

### Core Capabilities
* **Multilingual NLP Classification:** A hybrid TF-IDF + rule-based classifier that categorizes social posts (English, Hindi, Gujarati, Hinglish, Gujlish) into categories: *Incitement to Violence*, *Roadblocks/Protests*, *Fake News*, and *Non-Threat/Neutral*.
* **Visual & OCR Meme Analysis:** Extracts text from images via Tesseract OCR and performs semantic threat alignment via a pre-trained CLIP model to identify malicious memes.
* **Coordinated Amplification Detection:** Grouping algorithms identify synchronicity (same-time posts), text similarity (Jaccard similarity), and high follower-to-engagement anomalies.
* **Interactive Network Visualizations:** Interactive, force-directed canvas networks render account-to-coordination relationships, backed by Neo4j AuraDB.
* **Retrieval-Augmented AI Assistant:** Google Gemini-powered chat box grounded in live/mock dataset variables to compile status reports and trend summaries.

---

## 2. Directory & Folder Structure

```
social-threat-analyzer/
├── backend/                       # Python FastAPI Backend
│   ├── analytics/                 # Analytical engines
│   │   ├── coordination.py        # Coordinated botnet detection logic
│   │   ├── graph_db.py            # Neo4j Graph DB connector and Fallback Graph engine
│   │   ├── incidents.py           # Threat incident compiler and PDF generator
│   │   └── trends.py              # Time-series aggregation and spike detection
│   ├── assistant/                 # Grounded AI assistant routing
│   │   └── query_router.py        # Gemini grounding query engine
│   ├── crawler/                   # Social media data harvesters
│   │   ├── base.py                # Abstract BaseCrawler interface
│   │   ├── mock.py                # Mock crawler utilizing sample_posts.json
│   │   └── social_stubs.py        # Live crawlers (YouTube, Telegram, Meta, X)
│   ├── ml/                        # ML classification algorithms
│   │   ├── classifier.py          # TF-IDF multilingual text threat classifier
│   │   └── image_analyzer.py      # Tesseract OCR + CLIP meme threat analyzer
│   ├── login_telegram.py          # Terminal helper for MTProto interactive login
│   ├── main.py                    # Core FastAPI Router & application lifecycle
│   ├── requirements.txt           # Python dependency file
│   └── test_*.py                  # Isolation and E2E integration tests
├── frontend/                      # React Frontend Dashboard
│   ├── src/
│   │   ├── App.tsx                # Main Dashboard UI & Force Network Graph Canvas
│   │   ├── index.css              # Core styling system (Tailwind v4)
│   │   └── main.tsx               # Frontend entry point
│   ├── package.json               # Node dependency file
│   ├── tsconfig.json              # TypeScript compilation rules
│   └── vite.config.ts             # Vite build pipeline config
├── data/                          # Pre-generated dataset
│   └── sample_posts.json          # Pre-populated 500-post dataset
├── docs/                          # Detailed architecture notebooks
│   ├── AI_ASSISTANT.md            # Assistant grounding documentation
│   ├── IMAGE_ANALYSIS.md          # Meme image analyzer documentation
│   ├── NETWORK_GRAPH.md           # Graph DB structure and models
│   ├── NLP_CLASSIFIER.md          # TF-IDF weights and metrics
│   ├── PERFORMANCE.md             # Benchmark performance profiles
│   └── PLATFORM_COVERAGE.md       # Crawler credentials configuration
├── .env.example                   # Shared template config
├── README.md                      # Setup & local run manual
└── SUBMISSION.md                  # This submission master document
```

---

## 3. System Architecture & Information Flow

The system operates as a reactive event loop driving ingestion from crawlers to database persistence:

```
                  ┌──────────────────────┐
                  │ Social Media Sources │
                  │ Mock, YT, Telegram   │
                  └──────────┬───────────┘
                             │
                      [ Ingestion stream ]
                             │
                             ▼
                  ┌──────────────────────┐
                  │    FastAPI Ingest    │
                  │   (crawler_worker)   │
                  └──────────┬───────────┘
                             │
                    [ Multilingual NLP ]
                             │
                             ▼
                  ┌──────────────────────┐
                  │     ML Classifier    │
                  │   TF-IDF + Rules     │
                  └──────────┬───────────┘
                             │
                     [ Normalisation ]
                             │
                             ▼
        ┌──────────────────────────────────────────┐
        │       In-Memory Post Database            │
        │             (posts_db)                   │
        └───────┬──────────────────────────┬───────┘
                │                          │
        [ Graph Sync ]               [ Grounded RAG ]
                │                          │
                ▼                          ▼
     ┌─────────────────────┐    ┌─────────────────────┐
     │  Neo4j AuraDB Graph │    │  Gemini AI Studio   │
     │   (coordination)    │    │ (Retrieval Router)  │
     └─────────────────────┘    └─────────────────────┘
```

### Critical Data Flow
1. **Ingestion Loop:** Social crawlers (mock or live) fetch posts based on query keywords.
2. **Classification & Enrichment:** Each raw post text is immediately sent to the `MultilingualThreatClassifier` to detect the language, threat category, and calculate a confidence score.
3. **Queue Ingestion:** Normalised posts are fed into an asynchronous queue (`AppState.queue`), and cached in `AppState.posts_db`.
4. **Neo4j Graph Synchronization:** Upon receiving new posts, `AppState.sync_to_graph_db` executes the bot coordination grouping algorithm in a separate worker thread and uploads accounts (`:Account`) and relationships (`:COORDINATES_WITH`) to Neo4j.
5. **AI Assistant Querying:** User questions sent to the assistant are compiled with context extracted from the live `posts_db` (using TF-IDF post search matching) and routed to the Google Gemini model.

---

## 4. API Documentation

Served by default at `http://127.0.0.1:8000/docs` (Swagger UI).

### Core Endpoints

#### 1. System Health
* **Method/Path:** `GET /api/health`
* **Response:**
  ```json
  {
    "status": "healthy",
    "timestamp": 1785520500.66,
    "service": "social-threat-analyzer-backend",
    "version": "0.1.0",
    "gemini_model": "gemini-3.5-flash"
  }
  ```

#### 2. Live Text Threat Classification
* **Method/Path:** `POST /api/classify`
* **Body:** `{"text": "Gujarati protest roadblock at NH8 next Tuesday!"}`
* **Response:**
  ```json
  {
    "language": "Gujlish",
    "threat_category": "Roadblocks/Protests",
    "confidence": 0.90,
    "rule_triggered": true,
    "matched_phrases": ["roadblock"]
  }
  ```

#### 3. Coordinated Botnet Detection
* **Method/Path:** `GET /api/coordination`
* **Response:** A list of detected botnets:
  ```json
  [
    {
      "cluster_id": "cluster_tg_protest_2026-08",
      "platform": "Telegram",
      "member_accounts": ["@bot_agent_01", "@bot_agent_02"],
      "suspicion_score": 95,
      "heuristics": ["Identical message syntax", "Coordinated burst timestamps"],
      "common_keywords": ["roadblock", "NH8"]
    }
  ]
  ```

#### 4. Incident Logs
* **Method/Path:** `GET /api/incidents`
* **Response:** High-threat posts grouped into trackable incidents:
  ```json
  [
    {
      "incident_id": "INC-17855",
      "platform": "Telegram",
      "threat_category": "Incitement to Violence",
      "title": "Violent threat coordinated by 2 accounts on Telegram",
      "timestamp": "2026-08-15T10:30:00Z",
      "related_posts": [...]
    }
  ]
  ```

#### 5. Coordinated Campaign Network Graph
* **Method/Path:** `GET /api/network-graph`
* **Response:** Reconstructs accounts and connections for force-directed layout mapping:
  ```json
  {
    "neo4j_available": true,
    "status": "success",
    "nodes": [
      {"id": "@bot_agent_01", "label": "@bot_agent_01", "platform": "Telegram", "suspicion": 95, "post_count": 8}
    ],
    "edges": [
      {"from": "@bot_agent_01", "to": "@bot_agent_02", "heuristic": "Coordinated burst timestamps", "suspicion_score": 95}
    ]
  }
  ```

#### 6. AI Grounded Chat Assistant
* **Method/Path:** `POST /api/assistant/query`
* **Body:** `{"question": "Summarize the current threat incidents in Vadodara."}`
* **Response:** 
  ```json
  {
    "answer": "Based on the system status, there is 1 active incident in Vadodara concerning roadblock incitement. Two accounts (@bot_agent_01, @bot_agent_02) coordinated similar warning statements...",
    "source_posts": [...]
  }
  ```

#### 7. Visual & OCR Meme Analysis
* **Method/Path:** `POST /api/analyze-image`
* **Body:** Multipart Form Data containing an image file.
* **Response:** 
  ```json
  {
    "status": "success",
    "extracted_text": "Extracted meme text here",
    "detected_language": "English",
    "threat_category": "Incitement to Violence",
    "confidence": 0.85,
    "ocr_status": "success"
  }
  ```

---

## 5. Database Schema & Data Normalization

The Social Threat Analyzer models data in two tiers:

### 5.1 In-Memory Relational Cache (`posts_db`)
Every ingested post is normalised to the following schema:
* `id` (str, unique): Format `<platform>_<username>_<message_id>` (e.g. `tg_divyabhaskar_1423`)
* `username` (str): Handle of the author, prefixed with `@` where applicable
* `platform` (str): Ingestion origin (e.g. `YouTube`, `Telegram`, `Facebook`, `Instagram`, `Twitter`)
* `timestamp` (str): ISO 8601 UTC date string
* `text` (str): Raw post or comment message
* `language` (str): Model-predicted language
* `threat_category` (str): Model-predicted threat category
* `source_url` (str | null): Original post/message permalink
* `engagement` (dict): Likes, shares, and comments count
* `geo` (dict): Associated city, latitude, and longitude (Gujarati cities only)
* `classification_meta` (dict): Model confidence metrics and triggered rules

### 5.2 Neo4j Graph Database Schema
When AuraDB is connected, the coordination cluster graph uses the following entity schema:

```
(:Account {id: String, platform: String, post_count: Integer, suspicion: Integer})
      │
      │  [:COORDINATES_WITH {suspicion_score: Integer, heuristic: String}]
      ▼
(:Account {id: String, platform: String, post_count: Integer, suspicion: Integer})
```

* **Account Nodes (`:Account`)** represent social media accounts that have posted flagged content.
* **Coordinated Relationship Edges (`:COORDINATES_WITH`)** represent links between accounts that posted identical/similar text within small temporal windows.

---

## 6. Dependencies & Requirements

* **Python:** `3.10` or later
* **Node.js:** `18` or later
* **Tesseract OCR:** Required by PyTesseract for parsing images.

### Python requirements (`backend/requirements.txt`)
* `fastapi` & `uvicorn` (server engine)
* `scikit-learn` & `torch` & `transformers` (NLP pipelines)
* `pytesseract` & `pillow` (OCR and image handling)
* `telethon` (Telegram client client)
* `google-generativeai` (Gemini API integration)
* `neo4j` (graph driver)
* `openpyxl` & `reportlab` (incident document generation)

---

## 7. Setup & Installation

Follow these instructions for local setup and testing:

```bash
# 1. Enter backend folder
cd backend
python -m venv venv

# 2. Activate the virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Git Bash on Windows:
source venv/Scripts/activate
# Linux/macOS:
source venv/bin/activate

# 3. Verify activation & install dependencies
pip install -r requirements.txt

# 4. In a separate terminal, set up the frontend
cd ../frontend
npm install
```

### Configuration
1. Create a `.env` file at the **workspace root** (same directory level as `backend/` and `frontend/`).
2. Add your credentials (template in `.env.example`).
3. If using Telegram, execute the one-time interactive login:
   ```bash
   cd backend
   python login_telegram.py
   ```

### Execution
Run both terminals:
* **Terminal 1 (Backend):**
  ```bash
  cd backend
  # (Activate venv)
  python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
  ```
* **Terminal 2 (Frontend):**
  ```bash
  cd frontend
  npm run dev
  ```

---

## 8. Production Deployment Instructions

### 8.1 Backend Deployment (Uvicorn + Gunicorn / Docker)
For production, FastAPI should run behind a reverse proxy (Nginx) using Gunicorn to manage multiple Uvicorn workers.

#### Production Gunicorn Command:
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --daemon
```

#### Docker Deployment:
Create a `Dockerfile` in the `backend/` directory:
```dockerfile
FROM python:3.10-slim

# Install system dependencies (Tesseract)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.2 Frontend Deployment (Nginx / Static hosting)
Deploy the frontend static assets generated by Vite.

1. Build the production assets:
   ```bash
   cd frontend
   npm run build
   ```
   This generates the optimized bundle in the `frontend/dist/` directory.
2. Upload the `dist/` directory to static hosts (Vercel, Netlify, AWS S3, Cloudflare Pages), or serve them via Nginx:
   ```nginx
   server {
       listen 80;
       server_name social-threat-dashboard.com;

       location / {
           root /var/www/frontend/dist;
           index index.html;
           try_files $uri $uri/ /index.html;
       }

       location /api/ {
           proxy_pass http://127.0.0.1:8000/api/;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```
