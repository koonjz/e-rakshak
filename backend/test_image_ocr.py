import os
import io
import sys
import requests
from PIL import Image, ImageDraw, ImageFont

# Add workspace root and parent directory to sys.path to enable correct imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Enforce stdout to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from backend.ml.image_analyzer import analyze_image, TESSERACT_AVAILABLE

def create_test_image(text: str, filename: str, font_name: str = "Nirmala.ttc"):
    """
    Programmatically generates an image with text drawn on it.
    Uses Windows system font for clean OCR parsing.
    """
    # Create image with padding
    img = Image.new("RGB", (1200, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Try loading specific Windows system fonts
    font_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", font_name)
    if os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, 28)
        except Exception:
            font = ImageFont.load_default()
    else:
        # Fallback to general Arial or default
        arial_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "arial.ttf")
        if os.path.exists(arial_path):
            try:
                font = ImageFont.truetype(arial_path, 28)
            except Exception:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()
        
    # Draw text with dark gray color for high contrast
    draw.text((30, 45), text, fill=(20, 20, 20), font=font)
    
    # Save image
    img.save(filename)
    print(f"Generated test image: {filename} containing: '{text}'")

def test_ocr_flow():
    print("=== Testing Real Image OCR and Threat Analysis Pipeline ===")
    print(f"Tesseract OCR Available on Host: {TESSERACT_AVAILABLE}")
    
    if not TESSERACT_AVAILABLE:
        print("CRITICAL ERROR: Tesseract is not detected. Cannot run real test.")
        sys.exit(1)
        
    # Text samples to test
    # 1. English Threat
    eng_text = "Warning: We will block the Surat bypass tomorrow morning. Join the protest!"
    eng_file = "real_ocr_english.png"
    create_test_image(eng_text, eng_file, "arial.ttf")
    
    # 2. Hindi Threat (using Nirmala UI font)
    hindi_text = "बच कर रहना सब, हमला होने वाला है"
    hindi_file = "real_ocr_hindi.png"
    create_test_image(hindi_text, hindi_file, "Nirmala.ttc")

    # 3. Gujarati Threat (using Nirmala UI font)
    guj_text = "ચેતવણી: આવતીકાલે સવારે હાઇવે બ્લોક કરવામાં આવશે"
    guj_file = "real_ocr_gujarati.png"
    create_test_image(guj_text, guj_file, "Nirmala.ttc")

    try:
        # Check Direct Python Function
        print("\n--- 1. Running Direct Python OCR Extraction ---")
        for filename in [eng_file, hindi_file, guj_file]:
            with open(filename, "rb") as f:
                img_bytes = f.read()
            res = analyze_image(img_bytes)
            print(f"\nResult for {filename}:")
            print(f"  Status:       {res.get('status')}")
            if res.get("status") == "success":
                print(f"  Raw Extracted Text:")
                print(f"  --------------------------------------------------")
                print(res.get("extracted_text", "").strip())
                print(f"  --------------------------------------------------")
                print(f"  Detected Language:     {res.get('detected_language')}")
                print(f"  Threat Category:       {res.get('threat_category')}")
                print(f"  Confidence:            {res.get('confidence')}")
                print(f"  OCR Confidence:        {res.get('text_extraction_confidence')}")
            else:
                print(f"  Error/Warning: {res.get('message')}")
        
        # Check FastAPI Route via HTTP request
        print("\n--- 2. Testing FastAPI Endpoint (POST /api/analyze-image) ---")
        url = "http://127.0.0.1:8000/api/analyze-image"
        
        # We test eng_file
        with open(eng_file, "rb") as f:
            files = {"file": (eng_file, f, "image/png")}
            try:
                response = requests.post(url, files=files)
                print(f"HTTP Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"FastAPI Response for {eng_file}:")
                    print(f"  Extracted:  \"{data.get('extracted_text', '').strip()}\"")
                    print(f"  Language:   {data.get('detected_language')}")
                    print(f"  Category:   {data.get('threat_category')}")
                    print(f"  OCR Conf:   {data.get('text_extraction_confidence')}")
                else:
                    print(f"API Error: {response.text}")
            except Exception as e:
                print(f"FastAPI Server Connection Failed: {e}")
                print("Note: Start the backend uvicorn server to test the HTTP API endpoint.")
                
    finally:
        # Clean up temporary test files
        for filename in [eng_file, hindi_file, guj_file]:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"Cleaned up {filename}")

if __name__ == "__main__":
    test_ocr_flow()
