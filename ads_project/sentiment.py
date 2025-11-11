import re
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

nltk.download('vader_lexicon', quiet=True)
sid = SentimentIntensityAnalyzer()

# Custom lexicon tweaks to better reflect movie review language
sid.lexicon.update({
    # Strong positive phrases mapped via preprocessing
    'deeply_moving': 3.0,
    'profoundly_touching': 3.0,
    'lasting_impact': 2.4,
    'rewatched': 1.5,
    'must_watch': 2.6,
    'all_time_favorite': 3.2,
    'masterpiece': 3.2,
    # Reduce negative pull from words that can appear in positive contexts
    'cry': 0.0,
})

PHRASE_MAP = [
    (r"\bnever fails to make me cry\b", 'deeply_moving'),
    (r"\bengraved in my soul\b", 'profoundly_touching'),
    (r"\bstayed with me\b", 'lasting_impact'),
    (r"\bre[- ]?watched\b", 'rewatched'),
    (r"\ball[- ]time favourite\b|\ball[- ]time favorite\b", 'all_time_favorite'),
    (r"\bmust[- ]watch\b", 'must_watch'),
]

def _preprocess(text: str) -> str:
    t = text.lower()
    for pat, token in PHRASE_MAP:
        t = re.sub(pat, token, t)
    return t

def analyze_sentiment(text):
    processed = _preprocess(text)
    score = sid.polarity_scores(processed)
    return score['compound']