# Social Threat Analyzer

A real-time social-media intelligence platform for detecting, classifying, and visualising threat content — hate speech, incitement to violence, coordinated amplification — across multiple platforms.

The system ingests posts via live platform crawlers or a pre-generated mock dataset, classifies them with a multilingual TF-IDF + transformer hybrid model, and presents results in an interactive React dashboard. An embedded AI assistant (Google Gemini) can answer natural-language questions grounded in the live dataset.

---

## Table of Contents

1. [Architecture overview](#1-architecture-overview)
2. [Requirements](#2-requirements)
3. [Installation](#3-installation)
4. [Environment variables](#4-environment-variables)
5. [Telegram crawler behaviour](#5-telegram-crawler-behaviour)
6. [Facebook crawler behaviour](#6-facebook-crawler-behaviour)
7. [Running the project](#7-running-the-project)
8. [Telegram first-time authentication](#8-telegram-first-time-authentication)
9. [Facebook / Meta setup](#9-facebook--meta-setup)
10. [API endpoints](#10-api-endpoints)
11. [Post data schema](#11-post-data-schema)
12. [Testing and verification](#12-testing-and-verification)
13. [Troubleshooting](#13-troubleshooting)
14. [Security](#14-security)

---

## 1. Architecture overview

```
┌─────────────────────────────────────────────────────┐
│                    React Frontend                   │
│  Vite + React 19 + Tailwind CSS 4                   │
│  http://localhost:5173                              │
└─────────────────────┬───────────────────────────────┘
                      │ REST / polling
┌─────────────────────▼───────────────────────────────┐
│              FastAPI Backend                        │
│  Python 3.10+  ·  uvicorn  ·  http://localhost:8000 │
│                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────┐  │
│  │   Crawlers   │  │  ML Classifier│  │ Gemini   │  │
│  │  Mock/Live   │  │  TF-IDF +     │  │ AI Chat  │  │
│  │  platform    │  │  Transformers │  │ Assistant│  │
│  │  adapters    │  │               │  │          │  │
│  └──────┬───────┘  └───────────────┘  └──────────┘  │
│         │                                           │
│  ┌──────▼───────────────────────────────────────┐   │
│  │        In-memory post store (posts_db)       │   │
│  │        + Neo4j graph DB (optional)           │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Supported ingestion sources:**

| Platform  | Mode    | Credential required                                          |
|-----------|---------|--------------------------------------------------------------|
| Mock      | Built-in| None — always available                                     |
| YouTube   | Live    | `YOUTUBE_API_KEY`                                            |
| Telegram  | Live    | `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` + session file      |
| Facebook  | Live    | `META_ACCESS_TOKEN`                                          |
| Instagram | Live    | `META_ACCESS_TOKEN`                                          |
| X/Twitter | Live    | `TWITTER_BEARER_TOKEN` (paid X API plan)                    |

---

## 2. Requirements

| Dependency       | Version / Notes                                   |
|------------------|---------------------------------------------------|
| Python           | 3.10 or later                                     |
| Node.js          | 18 or later (LTS recommended)                     |
| npm              | Bundled with Node.js                              |
| Tesseract OCR    | System binary — required for image analysis       |
| Neo4j (optional) | AuraDB or local; falls back gracefully if absent  |

### Python packages (from `requirements.txt`)

```
fastapi
uvicorn
pydantic
scikit-learn
pytesseract
pillow
telethon
python-dotenv
python-multipart
neo4j
openpyxl
reportlab
torch
transformers
google-generativeai
```

### Frontend packages (from `frontend/package.json`)

React 19 · Tailwind CSS 4 · Vite 8 · TypeScript 6

---

## 3. Installation

### 3.1 Open the project

```bash
cd path/to/social-threat-analyzer
```

Or if cloning from a remote repository:

```bash
git clone <repository-url>
cd social-threat-analyzer
```

### 3.2 Backend setup

```bash
cd backend

# Create a virtual environment:
python -m venv venv
```

**Activate it — choose the command for your shell:**

```bash
# macOS / Linux / WSL (bash / zsh):
source venv/bin/activate
```

```powershell
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
```

```cmd
REM Windows Command Prompt:
.\venv\Scripts\activate.bat
```

```bash
# Install Python dependencies:
pip install -r requirements.txt
```

> `torch` and `transformers` are large packages. The first install may take several minutes.

### 3.3 Frontend setup

```bash
cd frontend
npm install
```

### 3.4 Configure environment variables

```bash
# From the project root:
cp .env.example .env
# (On Windows: copy .env.example .env)
```

Open `.env` and fill in the credentials for the services you intend to use. See [Section 4](#4-environment-variables) for all variables.

---

## 4. Environment variables

All configuration lives in a single `.env` file at the **project root** (same directory as `backend/` and `frontend/`). The backend loads it automatically on startup.

Use `.env.example` as the authoritative template — never commit real credentials.

### Complete variable reference

```env
# ── YouTube ──────────────────────────────────────────────────────────────────
YOUTUBE_API_KEY=your_real_youtube_api_key_here

# ── Meta (Facebook / Instagram) ──────────────────────────────────────────────
META_APP_ID=your_meta_app_id_here
META_APP_SECRET=your_meta_app_secret_here
META_ACCESS_TOKEN=your_meta_access_token_here

# ── Telegram ──────────────────────────────────────────────────────────────────
# Obtain from https://my.telegram.org → API development tools
TELEGRAM_API_ID=your_telegram_api_id_here
TELEGRAM_API_HASH=your_telegram_api_hash_here

# Optional seed channels (comma-separated, '@' prefix optional).
# Leave empty to search only channels the session account has already joined.
# Example: TELEGRAM_CHANNELS=gujaratsamacharofficial,divyabhaskar
TELEGRAM_CHANNELS=

# Optional seed Facebook page IDs/slugs (comma-separated).
# Leave empty to rely entirely on auto-discovery.
# Example: FACEBOOK_PAGES=GujaratSamachar,divyabhaskar
FACEBOOK_PAGES=

# ── Social crawler discovery controls ────────────────────────────────────────
SOCIAL_AUTO_DISCOVERY=true   # Set to 'false' to disable auto-discovery
SOCIAL_SOURCE_MODE=auto      # 'auto' or 'manual' (manual = seeds only)
ENABLE_TELEGRAM=true         # Set to 'false' to disable Telegram entirely
ENABLE_FACEBOOK=true         # Set to 'false' to disable Facebook entirely

# ── Neo4j (optional) ─────────────────────────────────────────────────────────
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password_here

# ── X (Twitter) ───────────────────────────────────────────────────────────────
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here

# ── Google Gemini AI assistant ────────────────────────────────────────────────
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
```

### Discovery control variables explained

| Variable | Default | Meaning |
|---|---|---|
| `SOCIAL_AUTO_DISCOVERY` | `true` | Master switch. When `true`, crawlers attempt automatic source discovery in addition to any configured seeds. |
| `SOCIAL_SOURCE_MODE` | `auto` | `auto`: discover then merge with seeds. `manual`: use only explicitly configured seeds — no discovery. |
| `ENABLE_TELEGRAM` | `true` | `false` fully disables the Telegram crawler (no connection, no error). |
| `ENABLE_FACEBOOK` | `true` | `false` fully disables the Facebook crawler. |
| `TELEGRAM_CHANNELS` | _(empty)_ | Optional seed channels to join before global search. Empty is valid. |
| `FACEBOOK_PAGES` | _(empty)_ | Optional seed page IDs. Empty is valid when auto-discovery is on. |

### Minimum configuration for a working demo

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

All other credentials are optional. Without them, the system uses the built-in mock crawler and an in-memory graph.

---

## 5. Telegram crawler behaviour

### How discovery works

When a keyword search is run, the crawler calls:

```python
client.iter_messages(None, search=query, limit=200)
```

This searches **across all dialogs (channels, groups, chats) the authenticated Telegram session account has joined**. Matching messages are returned with their source channel automatically identified — no channel list is required.

### Scope limitation

> **The Telegram MTProto API does not provide a mechanism to search channels or groups that the session account has not joined.** This is a platform-level restriction. There is no "search all of Telegram" public API endpoint.
>
> To expand discovery coverage, join relevant public channels using the Telegram app on the same session account. Once joined, those channels are automatically included in keyword searches.

### Seed channels (`TELEGRAM_CHANNELS`)

If `TELEGRAM_CHANNELS` is set, the crawler joins those channels before running the keyword search — adding them to the searchable dialog set. Seeds are supplemental; leaving this variable empty is valid and does not disable Telegram.

### Source URLs

Each Telegram post includes a `source_url` pointing to the **specific message**:

```
https://t.me/<channel_username>/<message_id>
```

For private channels (no public username), `source_url` is `null`. URLs are never guessed or fabricated.

---

## 6. Facebook crawler behaviour

### How discovery works

With `SOCIAL_AUTO_DISCOVERY=true` (the default), the crawler calls:

```
GET /v20.0/search?type=page&q=<keyword>&access_token=...
```

If successful, discovered page IDs are merged with any seeds from `FACEBOOK_PAGES`. Posts from all pages are fetched and keyword-filtered.

### API limitation

> **Meta removed the ability to search all public Facebook posts by keyword in 2018.** The standard Graph API does not support searching arbitrary public post content.
>
> Page discovery via `/search?type=page` requires the `pages_search` permission on the access token. If this permission is absent, the crawler logs a clear message and falls back to seeds. No exception is raised.

### Seed pages (`FACEBOOK_PAGES`)

`FACEBOOK_PAGES` is an optional comma-separated list of page IDs or slugs, merged with any auto-discovered pages. Leaving it empty is valid when auto-discovery is active.

### Source URLs

Each Facebook post includes a `source_url` pointing to the **specific post**:

```
https://www.facebook.com/<page_id>/posts/<post_id>
```

When a reliable URL cannot be constructed, `source_url` is `null`.

---

## 7. Running the project

Both services must run simultaneously in **two separate terminals**.

### Terminal 1 — Backend

```bash
cd backend
```

**Activate the virtual environment — choose your shell:**

```bash
# macOS / Linux / WSL:
source venv/bin/activate
```

```powershell
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
```

```bash
# Start the server:
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Successful startup output:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

| URL | Purpose |
|-----|---------|
| http://localhost:8000 | Backend API |
| http://localhost:8000/docs | Interactive Swagger API docs |

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Successful startup output:

```
  VITE v8.x.x  ready in xxxx ms
  ➜  Local:   http://localhost:5173/
```

| URL | Purpose |
|-----|---------|
| http://localhost:5173 | React dashboard |

> Both services must remain running. Stopping either will break the dashboard.

---

## 8. Telegram first-time authentication

Telegram uses MTProto session-based authentication. A one-time interactive login is required before the Telegram live crawler can be used.

### Prerequisites

Set in `.env`:

```env
TELEGRAM_API_ID=<integer from my.telegram.org>
TELEGRAM_API_HASH=<string from my.telegram.org>
```

Credentials are obtained from [https://my.telegram.org](https://my.telegram.org) → **API development tools**.

### Run the login script

```bash
# From the backend directory, with the venv active:
python login_telegram.py
```

The script prompts interactively:

1. Enter your phone number (e.g. `+91XXXXXXXXXX`)
2. Enter the code sent to your Telegram app
3. If Two-Step Verification is enabled, enter your 2FA password

On success: `SUCCESS: Telegram session authenticated successfully!`

### Session file

The session is saved to `telegram_session.session` in the **project root**. It must remain there; the crawler reads it at runtime.

- The file is **persistent** — you only need to run `login_telegram.py` once per machine.
- If the session file is deleted or the account is de-authorised in Telegram settings, re-run the login script.
- **Never commit this file.** It is listed in `.gitignore`.

---

## 9. Facebook / Meta setup

### Required credentials

| Variable | Source |
|---|---|
| `META_APP_ID` | [Meta for Developers](https://developers.facebook.com/) → Your App → Basic Settings |
| `META_APP_SECRET` | Same page as App ID |
| `META_ACCESS_TOKEN` | Graph API Explorer or your app's token flow |

### Permissions for full functionality

| Permission | Required for |
|---|---|
| `pages_read_engagement` | Fetching posts from pages managed by your app |
| `pages_search` | Auto-discovering relevant pages by keyword (optional — fallback to seeds if missing) |
| `instagram_basic` | Instagram hashtag search |

### Without credentials

If `META_ACCESS_TOKEN` is not configured, both Facebook and Instagram crawlers return an error status immediately and make no API calls. The rest of the application works normally.

---

## 10. API endpoints

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### System

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Service health check. Returns `status`, timestamp, Gemini model name. |

### Classification

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/classify` | Classify text. Body: `{"text": "..."}`. Returns language, threat category, confidence. |

### Analytics

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/trends` | Post volume trends, keyword frequency, spikes. Params: `threat_category`, `interval` (`day`/`hour`). |
| `GET` | `/api/coordination` | Coordinated amplification clusters with suspicion scores. |
| `GET` | `/api/incidents` | All threat incidents from the in-memory post store. |
| `GET` | `/api/incidents/export` | Excel export of top-N incidents. Param: `n` (default 10). |
| `GET` | `/api/incidents/{incident_id}/pdf` | PDF report for a specific incident. |
| `GET` | `/api/network-graph` | Force-directed graph nodes and edges. Falls back to in-memory computation when Neo4j is offline. |

### Crawler control

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/crawler/start` | Start mock crawler. Param: `lookback_days` (default 7). |
| `POST` | `/api/crawler/start-live` | Start live platform crawler. Params: `platform` (`youtube`/`telegram`/`facebook`/`instagram`/`twitter`), `keywords` (comma-separated string), `lookback_days`. |
| `POST` | `/api/crawler/stop` | Stop active crawler. |
| `GET` | `/api/crawler/status` | Active state, credential load flags per platform, queue size. |
| `GET` | `/api/crawler/posts` | Drain up to `limit` posts from the live queue. Param: `limit` (default 50). |

### AI and image

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/analyze-image` | Upload image (multipart `file`). Returns OCR text + CLIP threat analysis. |
| `POST` | `/api/assistant/query` | Gemini AI question grounded in live data. Body: `{"question": "..."}`. |

---

## 11. Post data schema

All posts from all sources share the following structure:

```json
{
  "id":               "tg_channelname_12345",
  "username":         "@channelname",
  "platform":         "Telegram",
  "timestamp":        "2026-08-15T10:30:00+00:00",
  "text":             "Post content here...",
  "language":         "Hindi",
  "threat_category":  "Incitement to Violence",
  "source_url":       "https://t.me/channelname/12345",
  "engagement": {
    "likes":    42,
    "shares":   7,
    "comments": 3
  },
  "geo": {
    "city":      "Ahmedabad",
    "latitude":  23.0225,
    "longitude": 72.5714
  },
  "classification_meta": {
    "confidence":      0.87,
    "threat_category": "Incitement to Violence",
    "language":        "Hindi",
    "keywords":        ["keyword1", "keyword2"]
  }
}
```

### `source_url` by platform

| Platform | Value |
|---|---|
| Telegram (public channel) | `https://t.me/<username>/<message_id>` — exact message permalink |
| Telegram (private channel) | `null` |
| Facebook | `https://www.facebook.com/<page_id>/posts/<post_id>` |
| YouTube | `https://www.youtube.com/watch?v=<video_id>` |
| Twitter / X | `https://twitter.com/i/web/status/<tweet_id>` |
| Instagram | Constructed from media ID where available |
| Mock | `null` — synthetic data, no real source |

`source_url` is **never fabricated or guessed**. When a reliable permalink cannot be determined, it is `null`.

---

## 12. Testing and verification

Run all test scripts from the `backend/` directory with the virtual environment active.

```bash
# Backend health
curl http://localhost:8000/api/health

# Classifier
python test_classifier.py

# AI assistant (requires GEMINI_API_KEY)
python test_assistant.py

# Mock crawler pipeline
python test_crawler.py

# Telegram crawler
python test_telegram.py

# Meta / Facebook scaffolds
python test_meta_scaffolds.py

# Coordination detection
python test_coordination.py

# Trends analytics
python test_trends.py

# Incident log
python test_incidents.py

# Image OCR + CLIP
python test_image_ocr.py
python test_image_clip.py
```

### Auto-discovery quick verification

```bash
python -c "
import os
os.environ.update({
    'TELEGRAM_CHANNELS':'', 'FACEBOOK_PAGES':'',
    'SOCIAL_AUTO_DISCOVERY':'true', 'SOCIAL_SOURCE_MODE':'auto',
    'ENABLE_TELEGRAM':'true', 'ENABLE_FACEBOOK':'true'
})
from crawler.social_stubs import TelegramCrawler, FacebookCrawler, AUTO_DISCOVERY
tc = TelegramCrawler(); fc = FacebookCrawler()
assert tc.seed_channels == [] and fc.seed_pages == [], 'Unexpected seeds'
assert tc.enabled and fc.enabled, 'Expected enabled=True'
assert AUTO_DISCOVERY == True, 'Expected AUTO_DISCOVERY=True'
print('All checks passed')
"
```

---

## 13. Troubleshooting

### Telegram: `pending_auth` status

**Cause:** Session file missing or the account was de-authorised.  
**Fix:** Run `python login_telegram.py` and complete the interactive flow. Confirm `telegram_session.session` exists in the project root.

### Telegram: `TELEGRAM_API_ID must be an integer`

**Fix:** `TELEGRAM_API_ID` must be a plain integer (e.g. `12345678`), not a quoted string.

### Telegram: `FloodWaitError`

**Cause:** Too many API requests in a short period.  
**Fix:** Wait the indicated number of seconds, then restart the crawler.

### Telegram: global search returns no results

**Cause:** The session account has not joined any channels related to the search keywords.  
**Fix:** Join relevant public channels in the Telegram app (on the same account), then retry. Consider adding `TELEGRAM_CHANNELS` as seed channels.

### Facebook: `Auto-discovery unavailable (HTTP 403)`

**Cause:** Token lacks `pages_search` permission.  
**Fix:** Approve the permission in your Meta app settings, or manually set `FACEBOOK_PAGES` with known page IDs.

### Facebook: `META_ACCESS_TOKEN is missing`

**Fix:** Add `META_ACCESS_TOKEN=<token>` to `.env`.

### Backend: `ModuleNotFoundError`

**Fix:** Ensure the virtual environment is activated. Run `pip install -r requirements.txt` again.

### Backend: port 8000 already in use

```powershell
# Windows PowerShell — find and kill the process:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Frontend: `vite: command not found`

**Fix:** Run `npm install` from the `frontend/` directory.

### Frontend: port 5173 already in use

```powershell
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

### Tesseract OCR not working

**Fix:** Install the Tesseract system binary:
- Windows: [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt install tesseract-ocr`

### Empty mock crawler results

**Cause:** `data/sample_posts.json` is missing, or all posts are outside the lookback window.  
**Fix:** Confirm `<project-root>/data/sample_posts.json` exists. Try increasing `lookback_days` when calling `/api/crawler/start`.

---

## 14. Security

- **Never commit `.env`** — it is listed in `.gitignore`.
- **Never commit `telegram_session.session`** — it grants full Telegram account access.
- **Use `.env.example` as the template** — it contains no real values.
- **Do not embed credentials in source code** — read them from environment variables at runtime.
- **Rotate tokens immediately** if you suspect any credential was exposed.
- The backend CORS policy uses `allow_origins=["*"]` for local development. Restrict this before deploying to a public network.

---

## Quick-start summary

```bash
# ── Backend ────────────────────────────────────────────────────────────────
cd backend
python -m venv venv

# Activate — pick your shell:
#   macOS / Linux / WSL:   source venv/bin/activate
#   Windows PowerShell:    .\venv\Scripts\Activate.ps1
#   Windows cmd:           .\venv\Scripts\activate.bat

pip install -r requirements.txt

# ── Frontend ───────────────────────────────────────────────────────────────
cd ../frontend
npm install

# ── Environment ────────────────────────────────────────────────────────────
cd ..
cp .env.example .env          # Windows cmd: copy .env.example .env
# Edit .env — add at minimum: GEMINI_API_KEY

# ── (One-time) Telegram authentication ────────────────────────────────────
cd backend
python login_telegram.py

# ── Start backend (Terminal 1) ─────────────────────────────────────────────
cd backend
# Activate venv (see above), then:
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# ── Start frontend (Terminal 2) ────────────────────────────────────────────
cd frontend
npm run dev
```

| Service       | URL                         |
|---------------|-----------------------------|
| Frontend      | http://localhost:5173        |
| Backend API   | http://localhost:8000        |
| API docs      | http://localhost:8000/docs   |
