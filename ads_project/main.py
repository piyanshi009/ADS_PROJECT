import pandas as pd
from scraper import get_reviews
from sentiment import analyze_sentiment
import os
import argparse
import sys

def label_sentiment(score):
    if score >= 0.2:
        return "Positive"
    elif score <= -0.2:
        return "Negative"
    else:
        return "Neutral"

def name_to_slug(name):
    return name.replace(" ", "-").lower()

def process_reviews(movie_slug, max_reviews=20):
    reviews = get_reviews(movie_slug, max_reviews=max_reviews)
    
    if not reviews:
        print("WARNING: No reviews scraped. Check slug or scraping setup.")
        return pd.DataFrame()

    data = []
    for review in reviews:
        sentiment = analyze_sentiment(review)
        label = label_sentiment(sentiment)
        data.append({
            "Review": review,
            "Sentiment Score": sentiment,
            "Label": label
        })

    df = pd.DataFrame(data)
    os.makedirs("data", exist_ok=True)
    df.to_csv(f"data/{movie_slug}_reviews.csv", index=False)
    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Letterboxd reviews and analyze sentiment.")
    parser.add_argument("--movie", dest="movie", type=str, help="Movie name, e.g. 'The Dark Knight'", default=None)
    parser.add_argument("--max-reviews", dest="max_reviews", type=int, help="Maximum number of reviews to fetch", default=20)
    args = parser.parse_args()

    if args.movie:
        movie_name = args.movie
    else:
        try:
            movie_name = input("Enter movie name: ").strip()
        except EOFError:
            print("No interactive input available. Please pass --movie '<name>' on the command line.")
            sys.exit(1)

    if not movie_name:
        print("Movie name is required.")
        sys.exit(1)

    movie_slug = name_to_slug(movie_name)
    df = process_reviews(movie_slug, max_reviews=args.max_reviews)

    if df.empty:
        print("No data to display.")
    else:
        preview = df.copy()
        try:
            preview["Review"] = preview["Review"].str.encode("cp1252", errors="ignore").str.decode("cp1252")
        except Exception:
            pass
        print("Preview (first 5 rows):")
        try:
            print(preview.head().to_string(index=False))
        except Exception:
            print("(Could not render preview due to console encoding)")
        print("\nSentiment Summary:")
        try:
            print(df["Label"].value_counts().to_string())
        except Exception:
            print("(Could not render summary due to console encoding)")