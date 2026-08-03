# Meme & Image Threat Analysis (OCR)

This document provides a detailed technical overview and performance evaluation of the image threat analysis feature integrated into the Social Threat Analyzer.

## Approach

The image analysis pipeline coordinates optical character recognition (OCR) and multilingual text classification:
1. **OCR Ingestion**: Raw image bytes are ingested via `POST /api/analyze-image`. 
2. **Text Extraction**: The image is parsed using `pytesseract` (Tesseract 5.5.3 system binary). The engine attempts to segment and read text using a multi-language configuration (`lang="eng+hin+guj"`). If Indic language packs are missing, it gracefully falls back to English (`lang="eng"`).
3. **OCR Confidence Scoring**: Average word-level extraction confidence is calculated using Tesseract's `image_to_data` confidence metrics, filtering out structural layout boundaries.
4. **Threat Classification**: Extracted text is routed through the hybrid `MultilingualThreatClassifier` (TF-IDF + Naive Bayes + heuristic overrides) to determine language, threat category, and confidence.
5. **Graceful Failures**: If Tesseract is not installed on the system, the endpoint returns a `pending_setup` status with clear installation guidelines, preventing backend crashes.

---

## Clean-Image Performance

On high-contrast, plain-background images, the OCR engine exhibits near-perfect character segmentation and word extraction.

### Raw Extraction Results (Clean Images)

*   **English Test Image**
    *   *Input text*: `"Warning: We will block the Surat bypass tomorrow morning. Join the protest!"`
    *   *Raw Extracted Output*: `"Warning: We will block the Surat bypass tomorrow morning. Join the protest!"`
    *   *Average OCR Word Confidence*: **95.9%**
    *   *Pipeline Classification*: `Incitement to Violence` (Confidence: 0.90)

*   **Hindi Test Image**
    *   *Input text*: `"बच कर रहना सब, हमला होने वाला है"`
    *   *Raw Extracted Output*: `"बच कर रहना सब, हमला होने वाला है"`
    *   *Average OCR Word Confidence*: **95.4%**
    *   *Pipeline Classification*: `Incitement to Violence` (Confidence: 0.90)

*   **Gujarati Test Image**
    *   *Input text*: `"ચેતવણી: આવતીકાલે સવારે હાઇવે બ્લોક કરવામાં આવશે"`
    *   *Raw Extracted Output*: `"ચેતવણી: આવતીકાલે સવારે હાઇવે બ્લોક કરવામાં આવશે"`
    *   *Average OCR Word Confidence*: **95.1%**
    *   *Pipeline Classification*: `Incitement to Violence` (Confidence: 0.90)

---

## Real-World / Noisy-Meme Performance

Testing with visually complex images—simulating actual social media memes with bold outline text overlaid on noisy, blurred gradient backgrounds and shapes—shows a clear divergence in resilience between Latin-based and Indic-based scripts.

### Raw Extraction Results (Noisy/Complex Memes)

*   **English Complex Meme**
    *   *Input text*: `"WE WILL BLOCK THE ROADS TOMORROW MORNING!"`
    *   *Raw Extracted Output*: `"i WILE BLOCKSTHE:.ROADS TOMORROW MOR"`
    *   *Average OCR Word Confidence*: **47.6%**
    *   *Performance Analysis*: Despite character distortion and spelling corruption (e.g. `WE` -> `i`, `WILL` -> `WILE`), the **core threat keywords (`BLOCK`, `ROADS`, `TOMORROW`) successfully survived**. The classifier pipeline was still able to categorize the text as `Inflammatory`.

*   **Gujarati Complex Meme**
    *   *Input text*: `"આવતીકાલે હાઇવે બ્લોક કરવામાં આવશે"`
    *   *Raw Extracted Output*: `"है. dlsiqlelsdicalsyszaqni આવશે"`
    *   *Average OCR Word Confidence*: **47.7%**
    *   *Performance Analysis*: **The extraction failed significantly.** Only the final word (`આવશે`) was parsed correctly; the rest of the Gujarati script was converted into illegible Latin and Devanagari gibberish.

> [!WARNING]
> **Indic-script OCR on stylized/low-contrast memes is currently highly unreliable**, whereas Latin-script OCR is comparatively robust. Indic scripts have complex glyph shapes, loops, and diacritics (matras) that fail to segment when subjected to outline fonts or background noise.

---

## Scoped-Out Fix Path (Image Preprocessing)

To make Indic OCR viable for social media memes in production, a pre-processing layer must be introduced before text extraction. The following techniques were scoped out of this build due to time constraints:
1. **Sauvola Binarization**: Adaptive thresholding designed to isolate text by converting color images to clean black-and-white, stripping background gradients.
2. **Text Region Localization**: Using deep learning detectors (e.g. CRAFT or DBNet) to locate text bounding boxes, cropping out the background before passing the text region to Tesseract.
3. **Contrast Enhancement**: Histogram equalization to sharpen glyph edges.
