import os
import sys

# Ensure parent directory and backend are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Force UTF-8 console encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from ml.classifier import MultilingualThreatClassifier

def run_slang_test():
    print("=== Testing Slang and Transliteration Expansion ===")
    classifier = MultilingualThreatClassifier()
    
    test_cases = [
        "usko pakdo aur maaaro, bahot bada deshdrohi hai",
        "road jam karenge kal subah se, rasta roko morcha chalu hoga",
        "aaj to patharbaazi chalu ho chuki hai, police pe patthar maro",
        "chutiya log gaddar hain, desh ko barbaad kar rahe hain",
        "bhrasht netao ko desh mathi kadhi nakho, mari nakho aakhri var",
        "aa badha bhrasht nakama ane badtameez che",
        "highway block kari do, badhi vehicles roko",
        "chalo aeni dukano ne salgaavi daiye, badla lenge",
        "vo harami dalal hai, pura fraud hai"
    ]
    
    for idx, sentence in enumerate(test_cases):
        res = classifier.predict(sentence)
        print(f"\nTest #{idx+1}: '{sentence}'")
        print(f"  - Language:        {res['language']}")
        print(f"  - Threat Category: {res['threat_category']}")
        print(f"  - Confidence:      {res['confidence']:.4f}")
        print(f"  - Sentiment Score: {res['sentiment_score']:.4f}")

if __name__ == "__main__":
    run_slang_test()
