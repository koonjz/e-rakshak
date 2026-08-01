import os
import io
import sys
import random
from typing import Dict, Any
from PIL import Image
import pytesseract
from pytesseract import Output, TesseractError

# Add parent directory to sys.path to enable relative imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ml.classifier import MultilingualThreatClassifier

# On Windows, try to auto-configure pytesseract if installed in default UB Mannheim location
if sys.platform.startswith("win"):
    default_win_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_win_tesseract):
        pytesseract.pytesseract.tesseract_cmd = default_win_tesseract

# Verify if Tesseract binary is accessible on system PATH or configured path
TESSERACT_AVAILABLE = False
TESSERACT_VERSION = None
try:
    TESSERACT_VERSION = pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
except Exception:
    print("ImageAnalyzer WARNING: Tesseract OCR is not installed or not found on system PATH.")

# Instantiate classifier globally for performance
classifier = MultilingualThreatClassifier()

def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Given raw image bytes, runs OCR text extraction via Tesseract,
    calculates extraction confidence, and routes extracted text
    through the threat classifier pipeline.
    """
    # Check if simulation mode is requested
    if os.getenv("SIMULATE_OCR", "false").lower() == "true":
        simulated_text = "Warning: We will block the Surat bypass tomorrow morning. Join the protest!"
        classification = classifier.predict(simulated_text)
        return {
            "status": "success",
            "extracted_text": simulated_text,
            "detected_language": classification.get("language", "English"),
            "threat_category": classification.get("threat_category", "Neutral"),
            "confidence": classification.get("confidence", 0.0),
            "text_extraction_confidence": 0.95,
            "is_simulated": True
        }

    if not TESSERACT_AVAILABLE:
        return {
            "status": "pending_setup",
            "error_code": "tesseract_not_found",
            "message": (
                "Tesseract OCR system binary was not found on this system.\n\n"
                "To resolve this, please install Tesseract on your host:\n"
                "1. Windows: Download the installer from UB Mannheim (https://github.com/UB-Mannheim/tesseract/wiki) "
                "and complete setup. The system will auto-detect 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'.\n"
                "2. Ubuntu/Debian: Run 'sudo apt-get install tesseract-ocr'\n"
                "3. macOS: Run 'brew install tesseract'\n\n"
                "Make sure to install English (eng), Hindi (hin), and Gujarati (guj) training files if testing multilingual memes."
            )
        }

    try:
        # Load image from bytes
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        return {
            "status": "error",
            "message": f"Invalid image format or failed to read image bytes: {e}"
        }

    extracted_text = ""
    text_extraction_confidence = 0.0
    lang_used = "eng"

    try:
        # Try multi-language OCR (English + Hindi + Gujarati)
        extracted_text = pytesseract.image_to_string(img, lang="eng+hin+guj")
        lang_used = "eng+hin+guj"
    except TesseractError:
        # If language packs are missing, fall back to English-only OCR
        try:
            extracted_text = pytesseract.image_to_string(img, lang="eng")
            lang_used = "eng"
        except Exception as e:
            return {
                "status": "error",
                "message": f"Tesseract OCR failed during execution: {e}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"OCR execution failed: {e}"
        }

    # Extract word-level data dictionary to calculate extraction confidence
    try:
        data = pytesseract.image_to_data(img, lang=lang_used, output_type=Output.DICT)
        # Filter out invalid confidences (-1 is returned for non-words / layout blocks)
        confidences = [int(c) for c in data.get("conf", []) if c != -1]
        if confidences:
            # Average word confidence normalized to a 0.0 - 1.0 range
            text_extraction_confidence = sum(confidences) / len(confidences) / 100.0
    except Exception:
        # Graceful fallback if image_to_data fails on complex structures
        text_extraction_confidence = 0.50 if extracted_text.strip() else 0.0

    # Clean text formatting
    cleaned_text = extracted_text.strip()

    # Route through threat classifier if text was found
    if cleaned_text:
        classification = classifier.predict(cleaned_text)
        return {
            "status": "success",
            "extracted_text": cleaned_text,
            "detected_language": classification.get("language", "English"),
            "threat_category": classification.get("threat_category", "Neutral"),
            "confidence": classification.get("confidence", 0.0),
            "text_extraction_confidence": round(text_extraction_confidence, 3)
        }
    else:
        return {
            "status": "success",
            "extracted_text": "",
            "detected_language": "Unknown",
            "threat_category": "Neutral",
            "confidence": 1.0,
            "text_extraction_confidence": 0.0
        }
