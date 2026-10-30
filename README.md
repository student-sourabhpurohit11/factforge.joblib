# 🔨 FactForge — Forging truth from the noise.

> An AI-powered news credibility & fake news detector combining machine learning (scikit-learn TF-IDF + Logistic Regression), live Google News cross-referencing, Wikipedia fact-checks, ChatGPT verification, and in-browser paragraph image OCR.

http://127.0.0.1:5001 <br>
https://factforge.de2.netrun.io

---

## 🌟 Key Features

- **Decisive Truth Verification:** No confusing "ambiguity" scores — gives a clear **Authenticity Score** (Verified Real News) or **Misinformation Risk** (Fake/Hoax).
- **Live Google News & Fact-Check Matching:** Automatically searches Google News, Reuters, AP News, PBS, and fact-checking databases (Snopes, FactCheck.org) to corroborate claims in real time.
- **Image & Screenshot OCR:** Upload or paste (`Cmd + V`) photos of news paragraphs, newspaper clippings, or social media screenshots; in-browser OCR (Tesseract.js) extracts the text automatically.
- **ChatGPT Cross-Examination:** Optional OpenAI integration (`gpt-4o-mini`) for deep contextual analysis and fact-checking.
- **Anti-Leakage NLP Preprocessing:** Custom cleaners strip wire datelines (e.g. `(Reuters) -`), URLs, and formatting traps to prevent shortcut learning.

---

## 🚀 Quickstart

### 1. Clone & Set Up
```bash
git clone https://github.com/student-sourabhpurohit11/factforge.joblib.git
cd factforge.joblib
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Train the Model
```bash
python train.py
```
*(Automatically loads local ISOT CSVs or falls back to downloading the Hugging Face fake news dataset).*

### 3. Run the App
```bash
python app.py
```

open [http://127.0.0.1:5001](http://127.0.0.1:5001) in your browser. <br>
Open https://factforge.de2.netrun.io in your browser.

---

## 🛠️ Tech Stack
- **Backend:** Python, Flask
- **Machine Learning:** scikit-learn (TF-IDF Vectorizer + Logistic Regression), joblib
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, Tesseract.js (Client-side OCR)
- **Knowledge Sources:** Google News RSS, Wikipedia API, OpenAI ChatGPT (optional)
