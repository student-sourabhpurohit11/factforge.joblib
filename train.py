import os
import sys
import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from utils import clean


def load_data() -> pd.DataFrame:
    """
    Loads dataset from local CSVs (ISOT dataset: data/Fake.csv and data/True.csv).
    If missing, automatically downloads a public fake-news dataset from Hugging Face.
    Labels: fake = 1, real = 0.
    """
    fake_csv = os.path.join("data", "Fake.csv")
    true_csv = os.path.join("data", "True.csv")

    if os.path.exists(fake_csv) and os.path.exists(true_csv):
        print("=" * 60)
        print(f"[INFO] Found local ISOT dataset in 'data/' folder.")
        print(f"       Loading {fake_csv} and {true_csv}...")
        print("=" * 60)

        df_fake = pd.read_csv(fake_csv)
        df_true = pd.read_csv(true_csv)

        # Label fake=1, real=0
        df_fake["label"] = 1
        df_true["label"] = 0

        df = pd.concat([df_fake, df_true], ignore_index=True)
        print(f"[INFO] Loaded {len(df_fake):,} fake articles and {len(df_true):,} real articles.")
        return df

    # Fallback to Hugging Face datasets library
    print("=" * 60)
    print("[INFO] 'data/Fake.csv' and/or 'data/True.csv' not found locally.")
    print("[INFO] Automatically falling back to downloading dataset from Hugging Face:")
    print("       Dataset: 'GonzaloA/fake_news' (public, no login or token needed).")
    print("       Downloading dataset now, please wait...")
    print("=" * 60)

    try:
        from datasets import load_dataset
        hf_ds = load_dataset("GonzaloA/fake_news", split="train")
        df = pd.DataFrame(hf_ds)

        # In GonzaloA/fake_news: 0 is fake, 1 is real.
        # We invert it so fake = 1, real = 0 to match requirements:
        df["label"] = 1 - df["label"]

        print(f"[INFO] Downloaded {len(df):,} articles successfully from Hugging Face.")
        return df
    except Exception as e:
        print(f"[ERROR] Failed to download dataset from Hugging Face: {e}", file=sys.stderr)
        print("[HINT] If you are offline, place 'Fake.csv' and 'True.csv' in the 'data/' directory.", file=sys.stderr)
        sys.exit(1)


def main():
    print("[1/5] Loading news dataset...")
    df = load_data()

    # Drop duplicates
    initial_count = len(df)
    df = df.dropna(subset=["title", "text"])
    df["combined"] = df["title"].astype(str) + " " + df["text"].astype(str)
    df = df.drop_duplicates(subset=["combined"])
    print(f"[2/5] Dropped {initial_count - len(df):,} duplicates. Remaining articles: {len(df):,}")

    # Clean text to eliminate source leakage (e.g. 'Reuters' wire tags)
    print("[3/5] Cleaning text (stripping source tags, URLs, and normalizing whitespace)...")
    df["cleaned"] = df["combined"].apply(clean)

    # Filter out empty texts after cleaning
    df = df[df["cleaned"].str.strip().str.len() > 0]

    # Stratified 80/20 train/test split
    print("[4/5] Splitting dataset (80% train, 20% test stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        df["cleaned"],
        df["label"],
        test_size=0.20,
        random_state=42,
        stratify=df["label"]
    )
    print(f"       Training set:   {len(X_train):,} samples")
    print(f"       Validation set: {len(X_test):,} samples")

    # Build Pipeline: TF-IDF Vectorizer + Logistic Regression
    print("[5/5] Training TF-IDF (max_features=50000, ngram_range=(1,2)) + Logistic Regression...")
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=50000,
            ngram_range=(1, 2),
            stop_words="english"
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            random_state=42
        ))
    ])

    pipeline.fit(X_train, y_train)

    # Evaluation
    print("\n" + "=" * 60)
    print("Classification Report on Test Data (20% holdout):")
    print("=" * 60)
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=["REAL", "FAKE"]))

    # Save model
    os.makedirs("models", exist_ok=True)
    model_path = os.path.join("models", "factforge.joblib")
    joblib.dump(pipeline, model_path)
    print(f"[SUCCESS] Model saved to '{model_path}'.")
    print("=" * 60)


if __name__ == "__main__":
    main()
