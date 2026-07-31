import os
import sys
import json
import urllib.request
import urllib.parse
from dotenv import load_dotenv

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Reconfigure stdout to UTF-8 to support emojis
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def dump_real_comments():
    print("=== DUMPING REAL YOUTUBE COMMENTS FOR MANUAL VERIFICATION ===")
    
    # Load .env variables
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.abspath(os.path.join(current_dir, "..", ".env"))
    load_dotenv(dotenv_path=dotenv_path)
    
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("ERROR: YOUTUBE_API_KEY is not defined in .env.")
        return
        
    keyword = "Gujarat news"
    print(f"Searching YouTube videos for: '{keyword}'...")
    
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(keyword)}&type=video&maxResults=3&key={api_key}"
    try:
        req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as res:
            search_data = json.loads(res.read().decode())
    except Exception as e:
        print(f"YouTube Search failed: {e}")
        return

    items = search_data.get("items", [])
    if not items:
        print("No videos found.")
        return
        
    for item in items:
        video_id = item["id"]["videoId"]
        video_title = item["snippet"]["title"]
        print(f"\n🎥 Video Title: {video_title}")
        print(f"🔗 Video URL:   https://www.youtube.com/watch?v={video_id}")
        
        comment_url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={video_id}&maxResults=3&key={api_key}"
        try:
            comment_req = urllib.request.Request(comment_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(comment_req, timeout=10) as res:
                comment_data = json.loads(res.read().decode())
                comments = comment_data.get("items", [])
                
                if not comments:
                    print("  (No comments found on this video or comments disabled)")
                    continue
                    
                for idx, c_item in enumerate(comments):
                    snippet = c_item["snippet"]["topLevelComment"]["snippet"]
                    author = snippet["authorDisplayName"]
                    text = snippet["textDisplay"]
                    timestamp = snippet["publishedAt"]
                    print(f"  💬 Comment #{idx+1} by {author} ({timestamp}):")
                    print(f"     \"{text.strip()}\"")
        except Exception as e:
            print(f"  ❌ Error loading comments: {e}")

if __name__ == "__main__":
    dump_real_comments()
