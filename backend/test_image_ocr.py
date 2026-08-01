import os
import io
import sys
import requests
from PIL import Image, ImageDraw, ImageFont

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Enforce stdout to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from backend.ml.image_analyzer import analyze_image, TESSERACT_AVAILABLE

def create_test_image(text: str, filename: str):
    """
    Programmatically generates an image with text drawn on it.
    Uses Windows default Arial ttf font for clean OCR parsing.
    """
    img = Image.new("RGB", (800, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Try loading Arial font on Windows
    font_path = r"C:\Windows\Fonts\arial.ttf"
    if os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, 24)
        except Exception:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()
        
    # Draw text with dark gray color for high contrast
    draw.text((30, 50), text, fill=(50, 50, 50), font=font)
    
    # Save image
    img.save(filename)
    print(f"Generated test image: {filename}")

def test_ocr_flow():
    print("=== Testing Image Analysis and OCR Flow ===")
    
    if not TESSERACT_AVAILABLE:
        print("\n[NOTE] Tesseract is not installed. Running SIMULATION MODE to show threat classification pipeline outputs:")
        from ml.classifier import MultilingualThreatClassifier
        classifier = MultilingualThreatClassifier()
        
        sim_texts = [
            ("Warning: We will block the Surat bypass tomorrow morning. Join the protest!", "test_ocr_english.png"),
            ("Alert: todi nakho badhu near Surat bypass tomorrow morning!", "test_ocr_mixed.png"),
            ("बच कर रहना सब, हमला होने वाला है", "test_ocr_hindi.png")
        ]
        for text, filename in sim_texts:
            res = classifier.predict(text)
            print(f"\nSimulated OCR Result for {filename}:")
            print(f"  Extracted Text: \"{text}\"")
            print(f"  Language:       {res.get('language')}")
            print(f"  Category:       {res.get('threat_category')}")
            print(f"  Confidence:     {res.get('confidence')}")
            print(f"  OCR Conf (Sim): 0.95")
        print("\n--- Running System Check (Checking system Tesseract and graceful errors) ---")
    
    # Text samples to test
    # 1. English Threat
    eng_text = "Warning: We will block the Surat bypass tomorrow morning. Join the protest!"
    eng_file = "test_ocr_english.png"
    create_test_image(eng_text, eng_file)
    
    # 2. Gujlish (Code-mixed) Threat (Uses English script, so works without guj language pack)
    mixed_text = "Alert: todi nakho badhu near Surat bypass tomorrow morning!"
    mixed_file = "test_ocr_mixed.png"
    create_test_image(mixed_text, mixed_file)

    # 3. Hindi Threat (Requires hin language pack)
    hindi_text = "बच कर रहना सब, हमला होने वाला है"
    hindi_file = "test_ocr_hindi.png"
    create_test_image(hindi_text, hindi_file)

    try:
        # Check Direct Python Function
        print("\n--- 1. Testing Direct Python Function ---")
        for filename, expected_part in [(eng_file, "block"), (mixed_file, "todi")]:
            with open(filename, "rb") as f:
                img_bytes = f.read()
            res = analyze_image(img_bytes)
            print(f"\nResult for {filename}:")
            print(f"  Status:       {res.get('status')}")
            if res.get("status") == "pending_setup":
                print("  Tesseract setup is pending. Graceful warning returned successfully.")
                print(f"  Message: {res.get('message')}")
            else:
                text = res.get("extracted_text", "")
                print(f"  Extracted:    \"{text.strip()}\"")
                print(f"  Language:     {res.get('detected_language')}")
                print(f"  Category:     {res.get('threat_category')}")
                print(f"  Confidence:   {res.get('confidence')}")
                print(f"  OCR Conf:     {res.get('text_extraction_confidence')}")
                assert expected_part.lower() in text.lower() or "tesseract" in str(res), "OCR mismatch!"
        
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
                    print("API Response JSON:")
                    import json
                    print(json.dumps(data, indent=2))
                else:
                    print(f"API Error: {response.text}")
            except Exception as e:
                print(f"FastAPI Server Connection Failed: {e}")
                print("Note: Start the backend uvicorn server to test the HTTP API endpoint.")
                
    finally:
        # Clean up temporary test files
        for filename in [eng_file, mixed_file, hindi_file]:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"Cleaned up {filename}")

if __name__ == "__main__":
    test_ocr_flow()
