# Multilingual NLP Threat Classifier

This document provides documentation on the hybrid NLP classifier pipeline and its inherent limitations.

## Approach

The threat analyzer uses a hybrid classification model:
1. **Machine Learning Layer**: A TF-IDF vectorizer paired with a Multinomial Naive Bayes (`MultinomialNB`) classifier trained on the `sample_posts.json` dataset. It handles general language identification and basic threat category predictions.
2. **Rule-Based Override Layer**: A heuristic regex pattern-matcher that intercepts predictions. If a known high-severity keyword or phrase is matched (such as specific incitement terms in English, Hinglish, Gujlish, Hindi, or Gujarati), the classification is overridden to a high-severity threat category with a standard `0.90` confidence.

---

## Limitations and Training Bias

> [!IMPORTANT]
> The direct-threat and language-specific override layers (e.g. English "I will destroy you" patterns, Hinglish "block the" rules, and Gujarati "બ્લોક" roadblock rules) are **targeted patches added in response to specific test failures, not a systemic fix to underlying training-data vocabulary bias in the Naive Bayes model**.

### Vocabulary Bias

Because the Naive Bayes model predicts categories based on bag-of-words token frequencies, any vocabulary imbalances in the dataset will cause biased predictions on unseen posts:
* For example, the term `ચેતવણી` (Warning) only appeared in 10 posts within `sample_posts.json`—all of which were labeled as `fake_news`. Consequently, any unseen Gujarati post containing `ચેતવણી` is strongly biased to be predicted as `Fake News`, even if the actual semantic context is incitement or safety warning.
* Other untested phrases, words, and semantic structures will exhibit the same vocabulary bias where non-threat words heavily skew the Naive Bayes probability estimates.

### Production Mitigation Path

To achieve true contextual understanding and eliminate vocabulary-based bias, the pipeline should be upgraded to use a **multilingual transformer model** (e.g., fine-tuned `mBERT`, `XLM-RoBERTa`, or `IndicBERT`) instead of TF-IDF Bag-of-Words:
* Transformers evaluate words contextually rather than independently.
* Shared multilingual subword embeddings allow the model to generalize threat patterns across Indic and code-mixed scripts without requiring extensive manual regex rulesets.
