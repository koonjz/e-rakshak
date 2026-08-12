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

---

## 👁️ CLIP Zero-Shot Visual Classification

To complement text-based OCR threat analysis, we integrated a zero-shot visual classification pipeline using the pre-trained `openai/clip-vit-base-patch32` model. This runs on-demand (lazy-loaded on the first API call) to provide pictorial understanding of the image content without requiring explicit training on specific threat classes.

### 1. Candidate Labels & Visual Scope
The model compares visual image embeddings against a text-defined set of candidate labels mapping to common threat-monitoring domains:
*   `"a crowd of people protesting"`
*   `"a burning building or fire"`
*   `"property damage or vandalism"`
*   `"a weapon or armed person"`
*   `"a peaceful gathering"`
*   `"a natural disaster or flood"`
*   `"an ordinary photo with no threat content"`

The top 3 matches are returned with normalized confidence scores.

### 2. Multi-Modal Unified Assessment
OCR text outputs and CLIP visual outputs are evaluated together at the API level:
*   **Agreement (Both Threatening)**: When both the extracted text and the visual elements present active threat signals.
*   **Agreement (Both Neutral)**: When no threats are detected in either text or visual elements.
*   **Disagreement (Threatening Text on Innocent Image)**: Highlighted when text contains a threat (e.g. violent caption) overlaying an innocuous photo.
*   **Disagreement (Threatening Visual with Neutral Text)**: Highlighted when the visual scene is alarming (e.g. protest or weapon) but contains no threat text.

---

## 🧪 CLIP System Verification & Real-World Limitations

To evaluate the pipeline's real performance, we ran a verification suite across 4 programmatic image scenarios:

| Scenario | OCR Text Output | Top Visual Label (CLIP) | CLIP Score | Overall Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **Protest Scene** | `''` | `a burning building or fire` | 36.4% | *Disagreement: Visually alarming scene detected with neutral/no text.* |
| **Neutral Flower** | `''` | `an ordinary photo with no threat content` | 37.8% | *Agreement: No threat content detected in either text or visual elements.* |
| **Text-Only Threat** | `'KILLALL TRAITORS...'` | `a burning building or fire` | 98.8% | *Agreement: Both text and visual content present active threat indicators.* |
| **Combined Threat** | `'PROTESTIN PEACE.'` | `a burning building or fire` | 89.8% | *Agreement: Both text and visual content present active threat indicators.* |

### ⚠️ Critical Limitations of Zero-Shot CLIP Classification

An analyst utilizing the Social Threat Analyzer must remain aware of several inherent limitations of CLIP zero-shot classification:

1. **Inherently Approximate (Zero-Shot Uncertainty)**: 
   As observed in the **Protest Scene** scenario, CLIP can get confused by abstract drawings or stylized shapes, predicting `"a burning building or fire"` (36.4%) instead of `"a crowd of people protesting"` (27.5%). It is a statistical pattern matching tool, not a human reasoning engine.
2. **Text Leakage into Visual Embeddings**: 
   In the **Text-Only Threat** scenario, despite the image having *only text* and zero actual picture content, CLIP predicted `"a burning building or fire"` with **98.8% confidence**. This happens because CLIP's visual encoder was pre-trained to read written text embedded in images. The word `"BURN"` in the image text leaked into the image embedding, heavily biasing the prediction.
3. **Uncalibrated Confidence Scores**: 
   The CLIP confidence scores are the result of a softmax layer over a closed set of candidate labels. They represent *relative probability distribution across the chosen candidates*, not calibrated, absolute probabilities of the event occurring. An 89.8% confidence score does not mean there is an 89.8% absolute chance of a fire being present.
4. **Context Blindness**: 
   CLIP lacks real-world contextual understanding. It can misidentify a peaceful protest sign, a training exercise, or a film set as a high-threat situation.
5. **Analyst Signal Recommendation**: 
   Because of these limitations, CLIP visual classifications should always be treated as a **preliminary signal to highlight files for manual human review**, rather than a definitive automated decision-maker.

