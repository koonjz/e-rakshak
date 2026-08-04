# Multilingual NLP Threat Classifier

This document provides documentation on the hybrid NLP classifier pipeline, its ensemble architecture, cross-validation metrics, and inherent limitations.

## Approach

The threat analyzer uses a hybrid classification model:
1. **Machine Learning Layer (Ensemble Classifier)**: Incorporates three base CPU-only models combined via soft voting (averaging predicted class probabilities):
   * **Model A**: Multinomial Naive Bayes (`MultinomialNB`) on word-level TF-IDF (1-2 grams) features.
   * **Model B**: Logistic Regression (`LogisticRegression`) on the same word-level TF-IDF features.
   * **Model C**: Logistic Regression (`LogisticRegression`) on character-level TF-IDF (3-5 grams) features (specifically helping capture spelling variants and code-mixed Hinglish/Gujlish slang that word-level features miss).
2. **Rule-Based Override Layer**: A heuristic regex pattern-matcher that intercepts predictions. If a known high-risk keyword or phrase is matched (such as specific incitement terms in English, Hinglish, Gujlish, Hindi, or Gujarati), the classification is overridden to a high-severity threat category with a standard `0.90` confidence.

---

## 5-Fold Stratified Cross-Validation Evaluation

To ensure an honest generalization estimate, the model was evaluated using **5-Fold Stratified Cross-Validation** (rather than simply reporting performance on the same dataset the models were trained on). Below is a comparison between the single-model baseline and the soft-voting ensemble model:

### Overall Results

* **Baseline Single Model (Word-level Naive Bayes)**: `0.9863 ± 0.0100` accuracy
* **Ensemble Model (Word MNB + Word LR + Char LR)**: `0.9922 ± 0.0073` accuracy (representing a **+0.0059** improvement in generalization accuracy and a decrease in standard deviation, proving that the ensemble effectively reduces model variance).

### Per-Language Accuracy Comparison

| Language | Baseline Acc | Ensemble Acc | Delta |
| :--- | :--- | :--- | :--- |
| **English** | 0.9905 | 0.9905 | +0.0000 |
| **Hindi** | 0.9889 | 0.9889 | +0.0000 |
| **Gujarati** | 0.9623 | 0.9837 | **+0.0213** |
| **Hinglish** | 1.0000 | 1.0000 | +0.0000 |
| **Gujlish** | 0.9913 | 1.0000 | **+0.0087** |

### Per-Category Accuracy Comparison

| Category | Baseline Acc | Ensemble Acc | Delta |
| :--- | :--- | :--- | :--- |
| **Neutral** | 0.9840 | 0.9840 | +0.0000 |
| **Inflammatory** | 0.9840 | 1.0000 | **+0.0160** |
| **Incitement to Violence** | 0.9846 | 0.9923 | **+0.0077** |
| **Fake News** | 0.9923 | 0.9923 | +0.0000 |

---

## Limitations and Training Bias

> [!IMPORTANT]
> The direct-threat and language-specific override layers (e.g. English "I will destroy you" patterns, Hinglish "block the" rules, and Gujarati "બ્લોક" roadblock rules) are **targeted patches added in response to specific test failures, not a systemic fix to underlying training-data vocabulary bias**.

### Vocabulary Bias Evidence

While the ensemble reduces variance errors, it **does not resolve systemic vocabulary bias** present in the dataset. This is proven by testing the edge cases with **rule overrides disabled**:

1. **"I will destroy you"**
   * *Baseline Prediction*: `incitement` (Confidence: 0.7886)
   * *Ensemble Prediction*: `incitement` (Confidence: 0.7169)
2. **"આવતીકાલે સવારે હાઇવે બ્લોક કરવામાં આવશે" (Gujarati Roadblock)**
   * *Baseline Prediction*: `fake_news` (Confidence: 0.4450)
   * *Ensemble Prediction*: `fake_news` (Confidence: 0.3743)
   * *Analysis*: Both models still misclassify this incitement-like warning as `Fake News` when rules are disabled. This occurs because the word `ચેતવણી` (Warning) appears in 10 posts in the dataset, 100% of which are labeled as `Fake News`, creating a strong feature bias that Naive Bayes and Logistic Regression cannot contextually bypass.
3. **"modi sarkar ne sab barbaad kar diya"**
   * *Baseline Prediction*: `inflammatory` (Confidence: 0.7235)
   * *Ensemble Prediction*: `inflammatory` (Confidence: 0.6450)

---

## Production Mitigation Path

To achieve true contextual understanding and eliminate vocabulary-based bias, the pipeline should be upgraded to use a **multilingual transformer model** (e.g., fine-tuned `mBERT`, `XLM-RoBERTa`, or `IndicBERT`) instead of TF-IDF Bag-of-Words:
* Transformers evaluate words contextually rather than independently.
* Shared multilingual subword embeddings allow the model to generalize threat patterns across Indic and code-mixed scripts without requiring extensive manual regex rulesets.
