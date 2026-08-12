import os
import io
import sys
import random
from typing import Dict, Any
from PIL import Image
import pytesseract
from pytesseract import Output, TesseractError

# Add parent directory and workspace root to sys.path to enable correct imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Insert custom path target 't' to sys.path to load torch/transformers on Windows
t_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "t"))
if t_dir not in sys.path:
    sys.path.insert(0, t_dir)

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

# Lazy loading variables for CLIP
clip_model = None
clip_processor = None

CANDIDATE_LABELS = [
    "a crowd of people protesting",
    "a burning building or fire",
    "property damage or vandalism",
    "a weapon or armed person",
    "a peaceful gathering",
    "a natural disaster or flood",
    "an ordinary photo with no threat content"
]

def load_clip_model():
    global clip_model, clip_processor
    if clip_model is None or clip_processor is None:
        try:
            from transformers import CLIPProcessor, CLIPModel
            print("ImageAnalyzer: Loading CLIP model (openai/clip-vit-base-patch32) on demand...")
            clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            print("ImageAnalyzer: CLIP model loaded successfully.")
        except Exception as e:
            print(f"ImageAnalyzer ERROR: Failed to load CLIP model: {e}")

def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Given raw image bytes, runs OCR text extraction via Tesseract,
    routes extracted text through threat classifier, classifies visual
    content using CLIP zero-shot classification, and constructs a unified
    combined assessment response.
    """
    try:
        # Load image from bytes
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        return {
            "status": "error",
            "message": f"Invalid image format or failed to read image bytes: {e}"
        }

    # 1. OCR Stage
    extracted_text = ""
    text_extraction_confidence = 0.0
    lang_used = "eng"
    ocr_status = "success"

    if not TESSERACT_AVAILABLE:
        ocr_status = "tesseract_not_found"
    else:
        try:
            # Try multi-language OCR (English + Hindi + Gujarati)
            extracted_text = pytesseract.image_to_string(img, lang="eng+hin+guj")
            lang_used = "eng+hin+guj"
        except TesseractError:
            # Fall back to English-only OCR
            try:
                extracted_text = pytesseract.image_to_string(img, lang="eng")
                lang_used = "eng"
            except Exception as e:
                ocr_status = f"ocr_failed: {e}"
        except Exception as e:
            ocr_status = f"ocr_failed: {e}"

        if ocr_status == "success":
            try:
                data = pytesseract.image_to_data(img, lang=lang_used, output_type=Output.DICT)
                confidences = [int(c) for c in data.get("conf", []) if c != -1]
                if confidences:
                    text_extraction_confidence = sum(confidences) / len(confidences) / 100.0
            except Exception:
                text_extraction_confidence = 0.50 if extracted_text.strip() else 0.0

    cleaned_text = extracted_text.strip()

    # 2. Text Threat Classification Stage
    threat_category = "Neutral"
    detected_language = "Unknown"
    confidence = 1.0
    if cleaned_text:
        classification = classifier.predict(cleaned_text)
        threat_category = classification.get("threat_category", "Neutral")
        detected_language = classification.get("language", "English")
        confidence = classification.get("confidence", 0.0)

    # 3. CLIP Stage
    visual_labels = []
    try:
        load_clip_model()
        if clip_model is not None and clip_processor is not None:
            import torch
            with torch.no_grad():
                rgb_img = img.convert("RGB")
                inputs = clip_processor(text=CANDIDATE_LABELS, images=rgb_img, return_tensors="pt", padding=True)
                outputs = clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=-1).squeeze().tolist()
                
                labeled_scores = list(zip(CANDIDATE_LABELS, probs))
                labeled_scores.sort(key=lambda x: x[1], reverse=True)
                visual_labels = [{"label": label, "score": round(score, 3)} for label, score in labeled_scores[:3]]
    except Exception as e:
        print(f"ImageAnalyzer: CLIP inference failed: {e}")

    # 4. Overall Assessment Stage
    top_visual = visual_labels[0]["label"] if visual_labels else None
    neutral_visual_labels = {"a peaceful gathering", "an ordinary photo with no threat content"}
    visual_is_threatening = top_visual is not None and top_visual not in neutral_visual_labels
    
    text_is_threatening = cleaned_text != "" and threat_category != "Neutral"
    
    if text_is_threatening and visual_is_threatening:
        overall_assessment = "Agreement: Both text and visual content present active threat indicators."
    elif text_is_threatening and not visual_is_threatening:
        overall_assessment = "Disagreement: Threatening text detected over an innocuous image."
    elif not text_is_threatening and visual_is_threatening:
        overall_assessment = "Disagreement: Visually alarming scene detected with neutral/no text."
    else:
        overall_assessment = "Agreement: No threat content detected in either text or visual elements."

    return {
        "status": "success",
        "extracted_text": cleaned_text,
        "detected_language": detected_language,
        "threat_category": threat_category,
        "confidence": confidence,
        "text_extraction_confidence": round(text_extraction_confidence, 3),
        "visual_labels": visual_labels,
        "overall_assessment": overall_assessment,
        "ocr_status": ocr_status
    }
