import sys
import os

# Add target 't' and root path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "t")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from PIL import Image, ImageDraw
import io
from ml.image_analyzer import analyze_image

def create_crowd_protest_image() -> bytes:
    img = Image.new("RGB", (300, 300), color=(200, 200, 200))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 250, 300, 300], fill=(100, 100, 100))
    for x in range(30, 280, 40):
        draw.ellipse([x-10, 150, x+10, 170], fill=(0, 0, 0))
        draw.line([x, 170, x, 220], fill=(0, 0, 0), width=2)
        draw.line([x, 220, x-10, 250], fill=(0, 0, 0), width=2)
        draw.line([x, 220, x+10, 250], fill=(0, 0, 0), width=2)
        draw.line([x, 190, x-15, 160], fill=(0, 0, 0), width=2)
        draw.line([x, 190, x+15, 160], fill=(0, 0, 0), width=2)
        draw.rectangle([x-25, 130, x+25, 150], fill=(255, 255, 200), outline=(0, 0, 0))
        draw.line([x, 150, x, 170], fill=(0, 0, 0), width=2)
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def create_neutral_image() -> bytes:
    img = Image.new("RGB", (300, 300), color=(240, 230, 200))
    draw = ImageDraw.Draw(img)
    draw.ellipse([130, 130, 170, 170], fill=(255, 100, 100))
    for angle in range(0, 360, 45):
        import math
        rad = math.radians(angle)
        px = 150 + int(math.cos(rad) * 35)
        py = 150 + int(math.sin(rad) * 35)
        draw.ellipse([px-10, py-10, px+10, py+10], fill=(255, 200, 100))
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def create_text_only_threat_image() -> bytes:
    img = Image.new("RGB", (400, 200), color=(10, 10, 10))
    draw = ImageDraw.Draw(img)
    draw.text((20, 80), "KILL ALL TRAITORS AND BURN THEIR HOUSES!", fill=(255, 255, 255))
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def create_combined_threat_image() -> bytes:
    img = Image.new("RGB", (300, 300), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.polygon([(50, 300), (100, 100), (150, 200), (200, 50), (250, 300)], fill=(255, 69, 0))
    draw.polygon([(80, 300), (130, 150), (180, 220), (220, 120), (240, 300)], fill=(255, 165, 0))
    draw.text((20, 20), "PROTEST IN PEACE", fill=(255, 255, 255))
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def run_tests():
    scenarios = {
        "Protest Scene Image": create_crowd_protest_image(),
        "Neutral Flower Image": create_neutral_image(),
        "Text-Only High Threat Image": create_text_only_threat_image(),
        "Combined Threat (Fire Visual + Peaceful Text)": create_combined_threat_image()
    }
    
    print("====================================================")
    print("STARTING CLIP IMAGE ANALYSIS SYSTEM VERIFICATION TESTS")
    print("====================================================\n")
    
    for name, img_bytes in scenarios.items():
        print(f"--- Scenario: {name} ---")
        res = analyze_image(img_bytes)
        print(f"OCR Extracted Text: {repr(res.get('extracted_text'))}")
        print(f"Text Threat Category: {res.get('threat_category')}")
        print(f"CLIP Visual Labels:")
        for label_info in res.get("visual_labels", []):
            print(f"  - {label_info['label']}: {label_info['score']}")
        print(f"Overall Assessment: {res.get('overall_assessment')}")
        print("-" * 50 + "\n")

if __name__ == "__main__":
    run_tests()
