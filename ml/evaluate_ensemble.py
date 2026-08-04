import os
import sys
import json
import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score

# Ensure stdout to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Constants
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sample_posts.json"))

def load_data():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Training data not found at {DATA_PATH}")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    texts = [post["text"] for post in data]
    languages = [post["language"] for post in data]
    categories = [post["threat_category"] for post in data]
    return texts, languages, categories, data

# Baseline Model: Word-level Naive Bayes
def get_baseline_model():
    return make_pipeline(
        TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=8000),
        MultinomialNB()
    )

# Ensemble Model wrapper for Stratified K-Fold CV
class EnsembleClassifier:
    def __init__(self):
        self.model_word_nb = make_pipeline(
            TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=8000),
            MultinomialNB()
        )
        self.model_word_lr = make_pipeline(
            TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=8000),
            LogisticRegression(max_iter=1000)
        )
        self.model_char_lr = make_pipeline(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=15000),
            LogisticRegression(max_iter=1000)
        )
        self.classes_ = None

    def fit(self, X, y):
        self.model_word_nb.fit(X, y)
        self.model_word_lr.fit(X, y)
        self.model_char_lr.fit(X, y)
        self.classes_ = self.model_word_nb.classes_

    def predict_proba(self, X):
        p_word_nb = self.model_word_nb.predict_proba(X)
        p_word_lr = self.model_word_lr.predict_proba(X)
        p_char_lr = self.model_char_lr.predict_proba(X)
        # Soft voting (average predicted probabilities)
        return (p_word_nb + p_word_lr + p_char_lr) / 3.0

    def predict(self, X):
        probs = self.predict_proba(X)
        indices = np.argmax(probs, axis=1)
        return self.classes_[indices]

def run_cross_validation():
    texts, languages, categories, data = load_data()
    X = np.array(texts)
    y = np.array(categories)
    langs = np.array(languages)
    
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # Store fold metrics
    baseline_accs = []
    ensemble_accs = []
    
    # Per language accuracies
    lang_list = sorted(list(set(languages)))
    baseline_lang_accs = {lang: [] for lang in lang_list}
    ensemble_lang_accs = {lang: [] for lang in lang_list}
    
    # Per category accuracies
    cat_list = sorted(list(set(categories)))
    baseline_cat_accs = {cat: [] for cat in cat_list}
    ensemble_cat_accs = {cat: [] for cat in cat_list}

    print("Running 5-Fold Stratified Cross-Validation...")
    for fold, (train_idx, test_idx) in enumerate(skf.split(X, y)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        langs_test = langs[test_idx]
        
        # Train baseline
        b_model = get_baseline_model()
        b_model.fit(X_train, y_train)
        b_preds = b_model.predict(X_test)
        
        # Train ensemble
        e_model = EnsembleClassifier()
        e_model.fit(X_train, y_train)
        e_preds = e_model.predict(X_test)
        
        # Overall Accuracy
        b_acc = accuracy_score(y_test, b_preds)
        e_acc = accuracy_score(y_test, e_preds)
        baseline_accs.append(b_acc)
        ensemble_accs.append(e_acc)
        
        # Per Language
        for lang in lang_list:
            mask = (langs_test == lang)
            if np.sum(mask) > 0:
                baseline_lang_accs[lang].append(accuracy_score(y_test[mask], b_preds[mask]))
                ensemble_lang_accs[lang].append(accuracy_score(y_test[mask], e_preds[mask]))
                
        # Per Category
        for cat in cat_list:
            mask = (y_test == cat)
            if np.sum(mask) > 0:
                baseline_cat_accs[cat].append(accuracy_score(y_test[mask], b_preds[mask]))
                ensemble_cat_accs[cat].append(accuracy_score(y_test[mask], e_preds[mask]))
                
    # Compile results
    print("\n==================================================")
    print("      EVALUATION SUMMARY: BASELINE VS ENSEMBLE    ")
    print("==================================================")
    print(f"Overall Baseline Accuracy: {np.mean(baseline_accs):.4f} ± {np.std(baseline_accs):.4f}")
    print(f"Overall Ensemble Accuracy: {np.mean(ensemble_accs):.4f} ± {np.std(ensemble_accs):.4f}")
    print("--------------------------------------------------")
    
    # Print Per-Language Side-by-Side
    print("PER-LANGUAGE GENERALIZATION ESTIMATES:")
    print(f"{'Language':<15} | {'Baseline Acc':<18} | {'Ensemble Acc':<18} | {'Delta':<8}")
    print("-" * 65)
    for lang in lang_list:
        b_mean = np.mean(baseline_lang_accs[lang])
        e_mean = np.mean(ensemble_lang_accs[lang])
        diff = e_mean - b_mean
        print(f"{lang.capitalize():<15} | {b_mean:.4f}            | {e_mean:.4f}            | {diff:+.4f}")
        
    print("\n--------------------------------------------------")
    # Print Per-Category Side-by-Side
    print("PER-CATEGORY GENERALIZATION ESTIMATES:")
    print(f"{'Category':<22} | {'Baseline Acc':<18} | {'Ensemble Acc':<18} | {'Delta':<8}")
    print("-" * 72)
    for cat in cat_list:
        b_mean = np.mean(baseline_cat_accs[cat])
        e_mean = np.mean(ensemble_cat_accs[cat])
        diff = e_mean - b_mean
        print(f"{cat.replace('_', ' ').title():<22} | {b_mean:.4f}            | {e_mean:.4f}            | {diff:+.4f}")
        
    print("==================================================")

def test_edge_cases_no_override():
    print("\n=== Testing Edge Cases (WITHOUT Rule Overrides) ===")
    texts, languages, categories, data = load_data()
    
    # Train full baseline and ensemble on all data
    b_model = get_baseline_model()
    b_model.fit(texts, categories)
    
    e_model = EnsembleClassifier()
    e_model.fit(texts, categories)
    
    edge_cases = [
        ("I will destroy you", "english"),
        ("આવતીકાલે સવારે હાઇવે બ્લોક કરવામાં આવશે", "gujarati"),
        ("modi sarkar ne sab barbaad kar diya", "hinglish")
    ]
    
    for phrase, lang in edge_cases:
        # Get baseline prediction + probs
        b_probs = b_model.predict_proba([phrase])[0]
        b_pred = b_model.classes_[np.argmax(b_probs)]
        b_conf = np.max(b_probs)
        
        # Get ensemble prediction + probs
        e_probs = e_model.predict_proba([phrase])[0]
        e_pred = e_model.classes_[np.argmax(e_probs)]
        e_conf = np.max(e_probs)
        
        print(f"\nPhrase: '{phrase}' (Language: {lang})")
        print(f"  - Baseline Prediction:  {b_pred:<22} (Conf: {b_conf:.4f})")
        print(f"  - Ensemble Prediction:  {e_pred:<22} (Conf: {e_conf:.4f})")
        
        # Print breakdown of probabilities
        classes = b_model.classes_
        print("  - Probability breakdown:")
        print(f"    {'Category':<22} | {'Baseline':<10} | {'Ensemble':<10}")
        for i, c in enumerate(classes):
            print(f"    {c:<22} | {b_probs[i]:.4f}   | {e_probs[i]:.4f}")

if __name__ == "__main__":
    run_cross_validation()
    test_edge_cases_no_override()
