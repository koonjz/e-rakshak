import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Enforce stdout to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ml.image_analyzer import analyze_image

def create_complex_meme(text: str, filename: str, font_name: str = "arial.ttf"):
    """
    Generates a visually complex meme-style image:
    1. Colorful, noisy, gradient background with circular patterns.
    2. Overlaid text using classic meme styling (white text with a thick black outline).
    """
    # 1. Create a colorful gradient background to simulate a complex image background
    width, height = 800, 300
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    
    # Fill with a gradient + abstract shapes
    for y in range(height):
        r = int(100 + (y / height) * 100)
        g = int(50 + (y / height) * 50)
        b = int(150 - (y / height) * 50)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
        
    # Draw some distracting shapes/noise lines
    draw.ellipse([50, 20, 200, 170], fill=(120, 80, 220))
    draw.rectangle([500, 60, 750, 240], fill=(60, 40, 110))
    draw.line([0, 0, width, height], fill=(180, 180, 180), width=3)
    draw.line([0, height, width, 0], fill=(180, 180, 180), width=3)
    
    # Add simple noise
    import random
    for _ in range(1000):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

    # Apply a light blur to the background to simulate photographic depth of field
    img = img.filter(ImageFilter.GaussianBlur(1))
    draw = ImageDraw.Draw(img)

    # 2. Draw classic meme text (white with black border/outline for readability)
    font_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", font_name)
    if os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, 32)
        except Exception:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()
        
    # Position text centered
    text_pos = (50, 120)
    
    # Draw text outline (8-directional offset stroke)
    stroke_color = (0, 0, 0)
    stroke_width = 3
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx != 0 or dy != 0:
                draw.text((text_pos[0] + dx, text_pos[1] + dy), text, fill=stroke_color, font=font)
                
    # Draw main text in bright white
    draw.text(text_pos, text, fill=(255, 255, 255), font=font)
    
    img.save(filename)
    print(f"Generated complex meme image: {filename} containing: '{text}'")

def run_complex_meme_test():
    print("=== Testing Visually Complex Meme Image OCR ===")
    
    # 1. Complex English Meme
    text_eng = "WE WILL BLOCK THE ROADS TOMORROW MORNING!"
    file_eng = "complex_meme_eng.png"
    create_complex_meme(text_eng, file_eng, "arialbd.ttf") # Arial Bold
    
    # 2. Complex Gujarati Meme
    text_guj = "આવતીકાલે હાઇવે બ્લોક કરવામાં આવશે"
    file_guj = "complex_meme_guj.png"
    create_complex_meme(text_guj, file_guj, "Nirmala.ttc")
    
    try:
        for filename in [file_eng, file_guj]:
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
    finally:
        # Clean up
        for filename in [file_eng, file_guj]:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"Cleaned up {filename}")

if __name__ == "__main__":
    run_complex_meme_test()
