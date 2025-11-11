import argparse
import os
import csv
import time
from datetime import datetime
from collections import Counter, defaultdict

import pandas as pd

from scraper import get_reviews

STOPWORDS = set(
    "a an the and or but if in on to for with at by from of is are was were be been being as it its this that those these you your our we they them their i me my he she his her him what which who whom where when why how not no yes up down over under again further then once here there all any both each few more most other some such only own same so than too very can will just don don should now".split()
)

EMOJI_MAP = {
    'Positive': '😄',
    'Neutral': '😐',
    'Negative': '☹️',
}

# naive language detection without heavy deps (very rough)
# user can improve in Power BI or we can switch to langdetect if installed
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    def detect_lang(text: str) -> str:
        try:
            return detect(text)
        except Exception:
            return 'und'
except Exception:
    def detect_lang(text: str) -> str:
        return 'und'


def name_to_slug(name: str) -> str:
    return name.replace(" ", "-").lower()


def label_sentiment(score: float) -> str:
    if score > 0.05:
        return "Positive"
    elif score < -0.05:
        return "Negative"
    return "Neutral"


def build_sentiment():
    # Try to use VADER if available without downloads; otherwise fallback
    try:
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        try:
            sid = SentimentIntensityAnalyzer()
            return lambda text: sid.polarity_scores(text).get('compound', 0.0)
        except Exception:
            pass
    except Exception:
        pass
    # Heuristic fallback based on positive/negative word lists
    pos_words = set([
        'good','great','excellent','amazing','awesome','love','loved','like','liked','fantastic','wonderful','best','perfect','brilliant','masterpiece','enjoyed','positive'
    ])
    neg_words = set([
        'bad','terrible','awful','boring','hate','hated','dislike','disliked','worst','poor','mediocre','disappointing','slow','negative'
    ])
    def heuristic(text: str) -> float:
        t = text.lower()
        score = 0
        for w in pos_words:
            if w in t:
                score += 1
        for w in neg_words:
            if w in t:
                score -= 1
        # normalize to [-1,1]
        if score == 0:
            return 0.0
        return max(-1.0, min(1.0, score / 5.0))
    return heuristic


analyze_sentiment = build_sentiment()


def tokenize(text: str):
    # very simple tokenizer
    tokens = []
    word = []
    for ch in text.lower():
        if ch.isalpha():
            word.append(ch)
        else:
            if word:
                tokens.append(''.join(word))
                word = []
    if word:
        tokens.append(''.join(word))
    return [t for t in tokens if t and t not in STOPWORDS and len(t) > 2]


def export_powerbi(movies, max_reviews=50, out_dir='powerbi_export', genres_map=None, manual=False):
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

    reviews_rows = []
    movies_rows = []
    words_rows = []
    status_rows = []

    for movie in movies:
        genre = genres_map.get(movie, '') if genres_map else ''
        slug = name_to_slug(movie)
        status = 'success'
        err = ''
        try:
            texts = get_reviews(slug, max_reviews=max_reviews, delay=1, fast=True, debug=False)
        except Exception as e:
            texts = []
            status = 'failure'
            err = str(e)

        sentiments = []
        languages = []
        top_pos = ('', -1.0)
        top_neg = ('', 1.0)

        for t in texts:
            s = analyze_sentiment(t)
            lbl = label_sentiment(s)
            lang = detect_lang(t)
            languages.append(lang)
            sentiments.append(s)
            emoji = EMOJI_MAP.get(lbl, '')
            reviews_rows.append({
                'movie': movie,
                'slug': slug,
                'review': t,
                'sentiment_score': round(s, 4),
                'sentiment_label': lbl,
                'emoji': emoji,
                'language': lang,
                'platform': 'Letterboxd',
                'created_at': ts,
                'genre': genre,
                'is_manual_injection': bool(manual),
            })
            if s > top_pos[1]:
                top_pos = (t, s)
            if s < top_neg[1]:
                top_neg = (t, s)

        # movie aggregates
        total = len(texts)
        avg = round(sum(sentiments) / total, 4) if total else 0.0
        movies_rows.append({
            'movie': movie,
            'slug': slug,
            'total_reviews': total,
            'avg_sentiment': avg,
            'top_positive_review': top_pos[0],
            'top_negative_review': top_neg[0],
            'genre': genre,
            'platform': 'Letterboxd',
            'last_scraped_at': ts,
        })

        # words for word cloud
        word_counts = Counter()
        for t in texts:
            word_counts.update(tokenize(t))
        for w, c in word_counts.most_common(200):
            words_rows.append({
                'movie': movie,
                'slug': slug,
                'word': w,
                'count': c,
                'genre': genre,
            })

        status_rows.append({
            'movie': movie,
            'slug': slug,
            'status': status,
            'error': err,
            'scraped_count': len(texts),
            'timestamp': ts,
            'manual_injection': bool(manual),
        })

    # Save CSVs
    pd.DataFrame(reviews_rows).to_csv(os.path.join(out_dir, 'reviews.csv'), index=False)
    pd.DataFrame(movies_rows).to_csv(os.path.join(out_dir, 'movies.csv'), index=False)
    pd.DataFrame(words_rows).to_csv(os.path.join(out_dir, 'words.csv'), index=False)
    pd.DataFrame(status_rows).to_csv(os.path.join(out_dir, 'status_logs.csv'), index=False)

    return out_dir


def parse_genres(genres_str: str):
    # Format: "Movie A:Action, Movie B:Drama"
    result = {}
    if not genres_str:
        return result
    parts = [p.strip() for p in genres_str.split(',') if p.strip()]
    for p in parts:
        if ':' in p:
            name, gen = p.split(':', 1)
            result[name.strip()] = gen.strip()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Export CSV datasets for Power BI dashboard from scraped Letterboxd reviews.')
    parser.add_argument('--movies', type=str, nargs='+', required=False, help='List of movie names, e.g., --movies "The Dark Knight" "Barbie 2023"')
    parser.add_argument('--max-reviews', type=int, default=50, help='Max reviews per movie')
    parser.add_argument('--out', type=str, default='powerbi_export', help='Output directory for CSVs')
    parser.add_argument('--genres', type=str, default='', help='Optional mapping: "Movie:Genre, Movie2:Genre2"')
    parser.add_argument('--manual-injection', action='store_true', help='Mark data as manually injected')

    args = parser.parse_args()
    default_movies = ["The Dark Knight", "Barbie 2023", "Oppenheimer"]
    movies = args.movies if args.movies else default_movies
    out = export_powerbi(
        movies=movies,
        max_reviews=args.max_reviews,
        out_dir=args.out,
        genres_map=parse_genres(args.genres),
        manual=args.manual_injection,
    )
    print(f"Exported CSVs to: {out}")
