import sys
import os
import json

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.classifier import MultilingualThreatClassifier

def test_unseen():
    # Configure UTF-8 stdout console printing
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    classifier = MultilingualThreatClassifier()
    
    test_cases = [
        "I will destroy you",
        "kal un logo ko maar dena chahiye",
        "Today is a beautiful day.",
        "Aa loko ne desh mathi kadhi nakho.",
        "modi sarkar ne sab barbaad kar diya"
    ]
    
    print("=== Testing Unseen Sentences against Threat Classifier ===")
    for text in test_cases:
        result = classifier.predict(text)
        print(f"Text:       '{text}'")
        print(f"Language:   {result['language']}")
        print(f"Category:   {result['threat_category']}")
        print(f"Sentiment:  {result['sentiment_score']}")
        print(f"Confidence: {result['confidence']}")
        print("-" * 50)

if __name__ == "__main__":
    test_unseen()
