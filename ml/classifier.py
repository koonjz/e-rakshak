import os
import json
import re
from typing import Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
import numpy as np

# ==============================================================================
# PRODUCTION UPGRADE PATH NOTE:
# For production deployment, a fine-tuned multilingual transformer model 
# (e.g., mBERT, IndicBERT, or XLM-RoBERTa) should be used instead of this TF-IDF model.
# Transformers provide superior semantic understanding, context awareness, and 
# generalization over code-mixed languages (Hinglish/Gujlish) by leveraging shared 
# multilingual subword embeddings.
# ==============================================================================

class MultilingualThreatClassifier:
    """
    Hybrid Multilingual Threat Classifier using scikit-learn TF-IDF Naive Bayes
    combined with a rule-based override layer for Hinglish and Gujlish slang.
    """
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Expected data folder location: root/data/sample_posts.json
            self.data_path = os.path.abspath(os.path.join(current_dir, "..", "data", "sample_posts.json"))
        else:
            self.data_path = data_path
            
        self.lang_model = None
        self.threat_model_word_nb = None
        self.threat_model_word_lr = None
        self.threat_model_char_lr = None
        
        # Complete language-specific threat rules & override keywords
        self.threat_rules = {
            "english": {
                "incitement": [
                    r"\bi will (destroy|kill|hurt|murder|find|stalk|attack|track|drag|end) you\b",
                    r"\byou will pay\b", r"\bwatch your back\b", r"\bgoing to end you\b",
                    r"\bburn (your|their) (house|office|shop|cars)\b", r"\bslash (your|their) throat\b",
                    r"\bkill (him|her|them)\b", r"\bbeat (him|her|them) up\b", r"\bdeserves to die\b",
                    r"\btake matters into our own hands\b"
                ],
                "inflammatory": [
                    r"\bcomplete fraud\b", r"\bbrain-dead\b", r"\bgarbage\b", r"\bpaid sellouts\b",
                    r"\bshameless trash\b", r"\bidiots\b", r"\bhypocrites\b", r"\bruining this city\b"
                ],
                "fake_news": [
                    r"\bbreaking\b", r"\binternet shutdown\b", r"\bchemical leak\b", r"\bsecret government\b",
                    r"\bgo bankrupt\b", r"\bscientific research confirms\b"
                ]
            },
            "hindi": {
                "incitement": [
                    r"बर्बाद कर दू", r"बच कर रहना", r"जान से मार", r"मार देना", r"तोड़फोड़", r"सड़क पर खींच",
                    r"सबक सिखा", r"आग लगा", r"हमला कर", r"हथियार उठा", r"फूंक दो"
                ],
                "inflammatory": [
                    r"भ्रष्ट", r"धोखेबाज़", r"महामूर्ख", r"कामचोर", r"बिकाऊ", r"बकवास", r"घटिया", r"बदतमीઝ",
                    r"पाखंडी", r"कायर"
                ],
                "fake_news": [
                    r"ब्रेकिंग", r"गुप्त दस्तावेज़", r"ज़हरीला रसायन", r"दिवालिया होने", r"नकली दवा",
                    r"भूकंप आने वाला", r"सत्य लीक"
                ]
            },
            "gujarati": {
                "incitement": [
                    r"બરબાદ કરી", r"મારી નાખ", r"પૂરો કરી", r"પતાવી દો", r"હુમલો કરી", r"સળગાવી દો",
                    r"તોડી નાખ", r"પથ્થરમારો", r"બ્લોક", r"રોડ બ્લોક", r"હાઇવે બ્લોક"
                ],
                "inflammatory": [
                    r"નકામા", r"વાયદા કરી", r"ભ્રષ્ટ", r"ગંદકી ફેલાવ", r"બિકાઉ", r"ભંગાર", r"ઢોંગી", r"કાયર"
                ],
                "fake_news": [
                    r"બ્રેકિંગ ન્યૂઝ", r"ગુપ્ત આદેશ", r"કેમિકલનું ઈન્જેક્શન", r"તિરાડ પડી", r"ધરતીકંપ આવશે",
                    r"નકલી કીટ", r"તોફાનો કરાવવા"
                ]
            },
            "hinglish": {
                "incitement": [
                    r"\bm+a{1,3}r+o*\b", r"\bm+a{1,3}r+\s*d+a{1,2}l+o*\b", r"\bp+e{1,2}t+o*\b",
                    r"\ba+g+\s*l+a+g+a*\b", r"\bt+o+d+\s*f+o+d+\b", r"\bt+o+d+\s*p+h+o+d+\b",
                    r"\bp+a+t+t?h+a+r+\b", r"\bp+a+t+t?h+a+r+b+a{1,2}z+i*\b", r"\bsabak sikh\b",
                    r"\bdestroy kar\b", r"\bkill kar\b", r"\bbadla lenge\b", r"\bgadiyon ko aag\b",
                    r"\bblock the\b", r"\br+a+s+t+a+\s*r+o+k+o*\b", r"\bh+i+g+h+w+a+y+\s*j+a+m+\b",
                    r"\br+o+a+d+\s*j+a+m+\b", r"\bd+a+n+g+a*\b", r"\bg+h+e+r+a+o*\b",
                    r"i will (destroy|kill|hurt|murder|find|stalk) you"
                ],
                "inflammatory": [
                    r"\bchor\b", r"\bbakwas\b", r"\bkamchor\b", r"\bmurkh\b", r"\bghatiya\b",
                    r"\bcorrupt\b", r"\bbarbaad kar\b", r"\bbarbaad kiya\b",
                    r"\bc+h+u+t+i+y+a*\b", r"\bk+a+m+i+n+a*\b", r"\bh+a+r+a+m+i*\b",
                    r"\bg+a+n+d+u+\b", r"\bg+a+d+d+a+r+\b", r"\bd+e+s+h+d+r+o+h+i*\b",
                    r"\bk+u+t+t+a*\b", r"\bs+a+a+l+a*\b", r"\ba+n+d+o+l+a+n+\b", r"\bidiot\b"
                ],
                "fake_news": [
                    r"\bleak\b", r"\bbreaking\b", r"\bshut down\b", r"\bban hone\b", r"\bplastic ke\b",
                    r"\bpoison\b", r"\bwater in\b", r"\bcooperative bank\b"
                ]
            },
            "gujlish": {
                "incitement": [
                    r"\bm+a{1,2}r+i+\s*n+a+k+h+o*\b", r"\bp+u+r+o+\s*k+a+r+i*\b", r"\bp+a+t+a+v+i+\s*d+o*\b",
                    r"\bs+a+l+g+a+v+i*\b", r"\bs+a+l+g+a+w+i*\b", r"\bs+ળ+g+a+v+i*\b",
                    r"\bt+o+d+p+h+o+d+\b", r"\bt+o+d+f+o+d+\b", r"\bp+a+t+t?h+a+r+m+a+r+o*\b",
                    r"\br+o+a+d+\s*b+l+o+c+k+\b", r"\bh+i+g+h+w+a+y+\s*b+l+o+c+k+\b",
                    r"\bv+e+h+i+c+l+e+s*\s*r+o+k+o*\b", r"\bdanga\b", r"\bdhoka\b", r"\bhulo\b",
                    r"\bthoki\b", r"\bpeeto\b"
                ],
                "inflammatory": [
                    r"\bn+a+k+a+m+o*\b", r"\bn+k+a+a+m+o*\b", r"\bb+h+r+a+s+h+t+a*\b", r"\bb+h+r+a+s+t+a*\b",
                    r"\bb+a+d+t+a+m+e+e+z+\b", r"\bb+a+d+t+a+m+e+z+\b", r"\bg+a+n+d+a*\b", r"\bm+u+r+k+h+\b",
                    r"\buse-less\b", r"\bkamchor\b", r"\bloako ne murkh\b", r"\bcorrupt\b", r"\bhaters\b"
                ],
                "fake_news": [
                    r"\bblackout\b", r"\bbimari faili\b", r"\bbandh thavana\b", r"\bexpired\b",
                    r"\bcrash\b", r"\brupture\b"
                ]
            }
        }
        
        # Train models on import/initialization if dataset is available
        self.train()

    def train(self):
        """
        Loads dataset from sample_posts.json and trains TF-IDF pipelines.
        """
        if not os.path.exists(self.data_path):
            print(f"Classifier Warning: Training file not found at {self.data_path}")
            return
            
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Classifier Error loading dataset: {e}")
            return
            
        texts = [post["text"] for post in data]
        languages = [post["language"] for post in data]
        categories = [post["threat_category"] for post in data]
        
        # 1. Train Language Identification Pipeline (Char N-Grams perform best for language ID)
        self.lang_model = make_pipeline(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), max_features=10000),
            MultinomialNB()
        )
        self.lang_model.fit(texts, languages)
        
        # 2. Train Ensemble Threat Category Pipelines (Soft voting base models)
        self.threat_model_word_nb = make_pipeline(
            TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=8000),
            MultinomialNB()
        )
        self.threat_model_word_lr = make_pipeline(
            TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=8000),
            LogisticRegression(max_iter=1000)
        )
        self.threat_model_char_lr = make_pipeline(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=15000),
            LogisticRegression(max_iter=1000)
        )
        
        self.threat_model_word_nb.fit(texts, categories)
        self.threat_model_word_lr.fit(texts, categories)
        self.threat_model_char_lr.fit(texts, categories)
        
        print("Threat classifier pipelines trained successfully.")

    def _apply_rules(self, text: str, detected_lang: str) -> str:
        """
        Heuristic rule-based override layer for code-mixed and plain threat languages.
        """
        text_lower = text.lower()
        
        # 1. High-priority direct threat checks globally (matches English incitement keywords)
        for regex in self.threat_rules["english"]["incitement"]:
            if re.search(regex, text_lower):
                return "incitement"
                
        # 2. Language specific rules
        lang_key = detected_lang.lower()
        if lang_key in self.threat_rules:
            for category, regex_list in self.threat_rules[lang_key].items():
                for regex in regex_list:
                    if re.search(regex, text_lower):
                        return category
                        
        # 3. Cross-language incitement fallback
        for lang_name, categories in self.threat_rules.items():
            for regex in categories["incitement"]:
                if re.search(regex, text_lower):
                    return "incitement"
                    
        return None

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predicts language, sentiment, threat category, and confidence.
        """
        if not text or not text.strip():
            return {
                "language": "english",
                "sentiment_score": 1.0,
                "threat_category": "neutral",
                "confidence": 1.0
            }
            
        # Fallback if model not trained
        if self.lang_model is None or self.threat_model_word_nb is None:
            return {
                "language": "english",
                "sentiment_score": 0.5,
                "threat_category": "neutral",
                "confidence": 0.5
            }
            
        # 1. Predict Language
        lang = self.lang_model.predict([text])[0]
        
        # 2. Predict Threat Category (Ensemble Average Model probabilities)
        p_word_nb = self.threat_model_word_nb.predict_proba([text])[0]
        p_word_lr = self.threat_model_word_lr.predict_proba([text])[0]
        p_char_lr = self.threat_model_char_lr.predict_proba([text])[0]
        
        threat_probs = (p_word_nb + p_word_lr + p_char_lr) / 3.0
        classes = self.threat_model_word_nb.classes_
        prob_map = dict(zip(classes, threat_probs))
        
        predicted_category = max(prob_map, key=prob_map.get)
        confidence = float(prob_map[predicted_category])
        
        # 3. Rule-Based Fallback Override Layer for Hinglish / Gujlish code-mixed languages
        rule_category = self._apply_rules(text, lang)
        if rule_category:
            predicted_category = rule_category
            confidence = 0.90  # High confidence override
            
        # 4. Calculate continuous sentiment score from predicted threat probabilities
        # Neutral maps to positive (1.0), Incitement to highly negative (0.05), etc.
        p_neutral = prob_map.get("neutral", 0.0)
        p_fake = prob_map.get("fake_news", 0.0)
        p_infl = prob_map.get("inflammatory", 0.0)
        p_inc = prob_map.get("incitement", 0.0)
        
        if rule_category:
            # Shift probabilities to match override
            if rule_category == "incitement":
                p_inc, p_neutral = 0.9, 0.05
            elif rule_category == "inflammatory":
                p_infl, p_neutral = 0.9, 0.05
            elif rule_category == "fake_news":
                p_fake, p_neutral = 0.9, 0.05
                
        sentiment_score = (p_neutral * 0.95) + (p_fake * 0.45) + (p_infl * 0.25) + (p_inc * 0.05)
        sentiment_score = float(max(0.0, min(1.0, sentiment_score)))
        
        # Map output category standard name
        category_mapping = {
            "neutral": "Neutral",
            "inflammatory": "Inflammatory",
            "incitement": "Incitement to Violence",
            "fake_news": "Fake News"
        }
        
        return {
            "language": lang.capitalize(),
            "sentiment_score": round(sentiment_score, 3),
            "threat_category": category_mapping.get(predicted_category, "Neutral"),
            "confidence": round(confidence, 3)
        }
