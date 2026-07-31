# Social Threat Analyzer

A platform for analyzing social media threat levels (toxicity, hate speech, doxxing, harassment, and violence) using advanced NLP models.

## Project Structure

```
social-threat-analyzer/
├── backend/            # FastAPI (Python) server
│   ├── main.py         # Application entrypoint & health endpoints
│   ├── requirements.txt# Python dependency list
│   └── venv/           # Python virtual environment
├── frontend/           # React + Vite (TypeScript) application
│   ├── src/            # App components & styles (Tailwind CSS v4)
│   └── index.html      # Dashboard entrypoint
├── data/               # Directory for raw and processed datasets (e.g. threats corpora)
└── ml/                 # Machine learning scripts, fine-tuning notebooks, and NLP models
```

## Getting Started

### 1. Run the Backend Server
Prerequisites: `Python 3.10+` and `uv` package manager (optional, but recommended).

Using `uv` (recommended):
```bash
cd backend
uv venv venv
uv pip install -r requirements.txt
.\venv\Scripts\uvicorn main:app --reload --port 8000
```

Or using standard Python:
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
The health check endpoint is available at `http://127.0.0.1:8000/api/health`.

### 2. Run the Frontend Dev Server
Prerequisites: `NodeJS` (v18+).

```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173/` in your browser. The frontend dashboard automatically verifies backend connectivity, monitors latency, and displays a reactive threat evaluation console.
