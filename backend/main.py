from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import asyncio
import os
import sys
from typing import Dict, Any, List

# Ensure parent directory is in sys.path so we can import the ml module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crawler.mock import MockCrawler
from crawler.social_stubs import YouTubeCrawler, InstagramCrawler, FacebookCrawler, TelegramCrawler
from ml.classifier import MultilingualThreatClassifier
from ml.image_analyzer import analyze_image

app = FastAPI(title="Social Threat Analyzer API")

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev stack verification
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Classifier, Crawler, and In-Memory Post Store State
class AppState:
    def __init__(self):
        self.task: asyncio.Task = None
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=2000)
        self.crawler = MockCrawler()
        self.active = False
        self.mode = "mock"  # Current active crawler mode: "mock" or "youtube"
        # Instantiate the TF-IDF hybrid classifier once
        self.classifier = MultilingualThreatClassifier()
        # In-memory database of all classified posts (pre-populated & real-time)
        self.posts_db: List[Dict[str, Any]] = []
        
        # Prepopulate db with mock posts on startup
        self.prepopulate_db()

    def prepopulate_db(self):
        print("Pre-populating in-memory database...")
        posts = self.crawler.posts
        for post in posts:
            try:
                # Classify and enrich at startup
                classification = self.classifier.predict(post["text"])
                post["language"] = classification["language"]
                post["threat_category"] = classification["threat_category"]
                post["classification_meta"] = classification
                self.posts_db.append(post)
            except Exception as e:
                print(f"Error pre-populating post {post.get('id')}: {e}")
        print(f"In-memory database pre-populated with {len(self.posts_db)} posts.")

state = AppState()

# Pydantic request models
class ClassifyRequest(BaseModel):
    text: str

async def crawler_worker(keywords: List[str] = None):
    """
    Background worker that streams posts from the crawler and pushes them to the queue.
    """
    try:
        print(f"Crawler worker task started with keywords: {keywords}")
        async for post in state.crawler.stream_posts(keywords=keywords):
            # If the queue gets completely full, discard the oldest to avoid memory leaks
            if state.queue.full():
                try:
                    state.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            
            # Enrich dynamic stream posts with model classification in real-time
            try:
                classification = state.classifier.predict(post["text"])
                post["language"] = classification["language"]
                post["threat_category"] = classification["threat_category"]
                post["classification_meta"] = classification
            except Exception as ml_err:
                print(f"Error classifying live stream post: {ml_err}")
                
            # Add to in-memory store for historical analytics
            state.posts_db.append(post)
            
            await state.queue.put(post)
    except asyncio.CancelledError:
        print("Crawler worker task cancelled by manager.")
    except Exception as e:
        print(f"Error in crawler worker task: {e}")
    finally:
        state.active = False
        state.task = None
        print("Crawler worker task shut down.")

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "social-threat-analyzer-backend",
        "version": "0.1.0"
    }

@app.post("/api/classify")
def classify_text(request: ClassifyRequest):
    """
    Classify a single piece of social media text for language, sentiment, threat category, and confidence.
    """
    try:
        return state.classifier.predict(request.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classifier error: {str(e)}")

@app.get("/api/trends")
def get_trends(threat_category: str = None, interval: str = "day"):
    """
    Query real-time and historical trends including keywords, spikes, and geo-breakdowns.
    """
    try:
        from analytics.trends import compute_trends
        return compute_trends(state.posts_db, threat_category=threat_category, interval=interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute trends: {str(e)}")

@app.get("/api/coordination")
def get_coordination():
    """
    Detect likely coordinated bot-like amplification clusters.
    """
    try:
        from analytics.coordination import detect_coordinated_behavior
        return detect_coordinated_behavior(state.posts_db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect coordinated behavior: {str(e)}")

@app.get("/api/incidents")
def get_incidents():
    """
    Get persistent incident records generated from incitement to violence or coordination clusters.
    """
    try:
        from analytics.incidents import get_all_incidents
        return get_all_incidents(state.posts_db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compile incidents: {str(e)}")

async def stop_crawler_helper():
    if state.active and state.task:
        state.task.cancel()
        for _ in range(10):
            if state.task is None or state.task.done():
                break
            await asyncio.sleep(0.1)
        state.active = False
        state.task = None

@app.post("/api/crawler/start")
async def start_crawler():
    if state.active:
        if state.mode == "mock":
            return {
                "status": "already_running",
                "message": "Crawler background worker is already active.",
                "queue_size": state.queue.qsize()
            }
        else:
            await stop_crawler_helper()
    
    state.crawler = MockCrawler()
    state.mode = "mock"
    state.active = True
    state.task = asyncio.create_task(crawler_worker())
    return {
        "status": "started",
        "message": "Mock Crawler started successfully."
    }

@app.post("/api/crawler/start-live")
async def start_live_crawler(platform: str = "youtube", keywords: str = "Gujarat"):
    # Enforce access checks for Meta platforms
    meta_access_token = os.getenv("META_ACCESS_TOKEN")
    
    if platform.lower() in ("instagram", "facebook"):
        if not meta_access_token:
            return {
                "status": "pending_meta_review",
                "message": f"Awaiting Meta App Review approval for public content access (Permission: {platform.lower()}_basic)"
            }
            
    # Enforce access checks for Telegram
    if platform.lower() == "telegram":
        telegram_api_id = os.getenv("TELEGRAM_API_ID")
        telegram_api_hash = os.getenv("TELEGRAM_API_HASH")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        session_file = os.path.abspath(os.path.join(current_dir, "..", "telegram_session.session"))
        session_exists = os.path.exists(session_file)
        
        if not telegram_api_id or not telegram_api_hash or not session_exists:
            return {
                "status": "pending_auth",
                "message": "Telegram API credentials not configured or session not authenticated. Run login flow first."
            }
            
    # If active, stop the current worker before switching modes
    await stop_crawler_helper()
    
    if platform.lower() == "instagram":
        state.crawler = InstagramCrawler()
        state.mode = "instagram"
    elif platform.lower() == "facebook":
        state.crawler = FacebookCrawler()
        state.mode = "facebook"
    elif platform.lower() == "telegram":
        state.crawler = TelegramCrawler()
        state.mode = "telegram"
    else:
        state.crawler = YouTubeCrawler()
        state.mode = "youtube"
        
    state.active = True
    
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    state.task = asyncio.create_task(crawler_worker(keywords=kw_list))
    return {
        "status": "started",
        "message": f"Live {platform.upper()} Crawler started for keywords: {keywords}."
    }

@app.post("/api/crawler/stop")
async def stop_crawler():
    if not state.active:
        return {
            "status": "not_running",
            "message": "Crawler background worker is not currently active."
        }
    
    await stop_crawler_helper()
    return {
        "status": "stopped",
        "message": "Crawler background worker stopped successfully."
    }

@app.get("/api/crawler/status")
def get_crawler_status():
    crawler_name = type(state.crawler).__name__
    if crawler_name == "MockCrawler":
        dataset_path = state.crawler.data_path
        dataset_exists = os.path.exists(dataset_path)
    else:
        dataset_path = f"{crawler_name} API Connection"
        dataset_exists = True
        
    current_dir = os.path.dirname(os.path.abspath(__file__))
    session_file = os.path.abspath(os.path.join(current_dir, "..", "telegram_session.session"))
    session_exists = os.path.exists(session_file)
        
    return {
        "active": state.active,
        "mode": state.mode,
        "queue_size": state.queue.qsize(),
        "dataset_path": dataset_path,
        "dataset_exists": dataset_exists,
        "youtube_key_loaded": bool(os.getenv("YOUTUBE_API_KEY")),
        "meta_token_loaded": bool(os.getenv("META_ACCESS_TOKEN")),
        "telegram_auth_loaded": bool(os.getenv("TELEGRAM_API_ID") and os.getenv("TELEGRAM_API_HASH") and session_exists)
    }

@app.get("/api/crawler/posts", response_model=List[Dict[str, Any]])
def get_crawled_posts(limit: int = 50):
    posts = []
    # Drain posts from queue up to the specified limit
    qsize = state.queue.qsize()
    drain_count = min(limit, qsize)
    
    for _ in range(drain_count):
        try:
            post = state.queue.get_nowait()
            posts.append(post)
        except asyncio.QueueEmpty:
            break
            
    return posts

@app.post("/api/analyze-image")
async def analyze_image_route(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        result = analyze_image(contents)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
