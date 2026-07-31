import sys
import os
import json
import collections

# Ensure ml module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.classifier import MultilingualThreatClassifier

def run_evaluation():
    print("=== Threat Classifier Model Evaluation ===")
    
    # Configure UTF-8 stdout console printing
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
        
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sample_posts.json"))
    if not os.path.exists(data_path):
        print(f"FAIL: Dataset not found at {data_path}")
        sys.exit(1)
        
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} test items from ground-truth dataset.\n")
    
    # Instantiate and train classifier
    classifier = MultilingualThreatClassifier(data_path=data_path)
    
    # Ground truth threat categories standard mapping
    cat_mapping = {
        "neutral": "Neutral",
        "inflammatory": "Inflammatory",
        "incitement": "Incitement to Violence",
        "fake_news": "Fake News"
    }
    
    # Accumulate metrics
    correct_lang = 0
    correct_threat = 0
    
    lang_totals = collections.defaultdict(int)
    lang_correct_lang = collections.defaultdict(int)
    lang_correct_threat = collections.defaultdict(int)
    
    cat_totals = collections.defaultdict(int)
    cat_correct_threat = collections.defaultdict(int)
    
    for post in data:
        text = post["text"]
        true_lang = post["language"].lower()
        true_cat = cat_mapping[post["threat_category"]]
        
        # Predict
        pred = classifier.predict(text)
        pred_lang = pred["language"].lower()
        pred_cat = pred["threat_category"]
        
        # Track Lang Accuracy
        lang_totals[true_lang] += 1
        if pred_lang == true_lang:
            correct_lang += 1
            lang_correct_lang[true_lang] += 1
            
        # Track Threat Accuracy
        cat_totals[true_cat] += 1
        if pred_cat == true_cat:
            correct_threat += 1
            cat_correct_threat[true_cat] += 1
            lang_correct_threat[true_lang] += 1
            
    # Computations
    total_posts = len(data)
    overall_lang_acc = correct_lang / total_posts
    overall_threat_acc = correct_threat / total_posts
    
    print("-" * 50)
    print(f"Overall Language Classification Accuracy : {overall_lang_acc * 100:.2f}% ({correct_lang}/{total_posts})")
    print(f"Overall Threat Classification Accuracy   : {overall_threat_acc * 100:.2f}% ({correct_threat}/{total_posts})")
    print("-" * 50)
    
    print("\n--- Accuracy Breakdown Per Language ---")
    for lang in sorted(lang_totals.keys()):
        total = lang_totals[lang]
        c_lang = lang_correct_lang[lang]
        c_threat = lang_correct_threat[lang]
        
        lang_acc = (c_lang / total) * 100
        threat_acc = (c_threat / total) * 100
        
        print(f"{lang.capitalize():10} | Posts: {total:3} | Lang ID Acc: {lang_acc:6.2f}% | Threat Detection Acc: {threat_acc:6.2f}%")
        
    print("\n--- Accuracy Breakdown Per Threat Category ---")
    for cat in sorted(cat_totals.keys()):
        total = cat_totals[cat]
        c_threat = cat_correct_threat[cat]
        cat_acc = (c_threat / total) * 100
        print(f"{cat:25} | Posts: {total:3} | Threat Detection Acc: {cat_acc:6.2f}%")
        
    print("-" * 50)
    print("Evaluation Complete.")

if __name__ == "__main__":
    run_evaluation()
