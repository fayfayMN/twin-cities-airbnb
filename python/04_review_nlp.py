"""
TRACK A - STEP 5b: Review text mining (Python / VADER + word frequencies).

  1. VADER sentiment per review, then average sentiment by month (are winter
     reviews worse? — a Twin Cities question about snow/parking/shoveling).
  2. Word frequencies, and Twin-Cities keyword hit rates (snow, parking, lake...).

To keep it fast we SAMPLE reviews; raise SAMPLE for the full 319K.

Run:  python 04_review_nlp.py
Needs: pandas, vaderSentiment, matplotlib
"""
import re
import sys
from collections import Counter
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import config as C

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SAMPLE = 40000          # set to None to use every review

STOP = set("""the a an and or but to of in on for with is are was were be been it
this that i we you they he she my our your at as so if from by not have has had
very great place stay host home really nice good was were had would will can just
us all had also get got very much so were are""".split())

TC_KEYWORDS = ["snow", "winter", "cold", "shovel", "ice", "parking", "airport",
               "lake", "mall of america", "stadium", "downtown", "quiet", "noise"]


def tokenize(text):
    return [w for w in re.findall(r"[a-z']+", str(text).lower())
            if w not in STOP and len(w) > 2]


def main():
    rev = pd.read_csv(C.REVIEWS_CLEAN, parse_dates=["date"])
    rev = rev.dropna(subset=["comments"])
    if SAMPLE and len(rev) > SAMPLE:
        rev = rev.sample(SAMPLE, random_state=0)
    print(f"Scoring {len(rev):,} reviews...")

    an = SentimentIntensityAnalyzer()
    rev["sentiment"] = rev["comments"].astype(str).apply(
        lambda t: an.polarity_scores(t)["compound"])

    # sentiment by calendar month-of-year (seasonality of guest happiness)
    by_month = rev.groupby(rev["date"].dt.month)["sentiment"].mean()
    fig, ax = plt.subplots(figsize=(9, 4))
    by_month.plot(kind="bar", ax=ax, color="teal")
    ax.set_title("Mean review sentiment by month (1=Jan ... 12=Dec)")
    ax.set_xlabel("month"); ax.set_ylabel("VADER compound")
    fig.tight_layout(); fig.savefig(C.FIGURES / "08_sentiment_by_month.png", dpi=130)
    plt.close(fig)
    print("  saved 08_sentiment_by_month.png")
    print("  lowest-sentiment months:", by_month.nsmallest(3).round(3).to_dict())

    # top words in the most positive vs most negative reviews
    pos = rev[rev["sentiment"] > 0.6]["comments"]
    neg = rev[rev["sentiment"] < 0]["comments"]
    pos_words = Counter(w for t in pos for w in tokenize(t)).most_common(20)
    neg_words = Counter(w for t in neg for w in tokenize(t)).most_common(20)
    print("\nTop words in POSITIVE reviews:", [w for w, _ in pos_words])
    print("Top words in NEGATIVE reviews:", [w for w, _ in neg_words])

    # Twin Cities keyword hit rates
    print("\nTwin-Cities keyword hit rate (share of reviews mentioning):")
    low = rev["comments"].astype(str).str.lower()
    # \b word boundaries so "ice" doesn't match "nice"/"price"/"office"
    hits = {k: low.str.contains(rf"\b{re.escape(k)}\b").mean() for k in TC_KEYWORDS}
    for k, v in sorted(hits.items(), key=lambda x: -x[1]):
        print(f"  {k:16s} {v*100:5.2f}%")

    pd.Series(hits).sort_values().plot(
        kind="barh", figsize=(8, 5), color="indigo",
        title="Share of reviews mentioning each Twin-Cities term")
    plt.tight_layout(); plt.savefig(C.FIGURES / "09_tc_keywords.png", dpi=130)
    plt.close()
    print("  saved 09_tc_keywords.png")


if __name__ == "__main__":
    main()
