import os
import joblib
from flask import Flask, request, jsonify, send_from_directory
from utils import clean, evaluate_credibility

app = Flask(__name__, static_folder="static")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "factforge.joblib")
model = None


def get_model():
    """Lazily load or reload model if available."""
    global model
    if model is None and os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            print(f"[INFO] Model successfully loaded from {MODEL_PATH}")
        except Exception as e:
            print(f"[ERROR] Failed to load model from {MODEL_PATH}: {e}")
            model = None
    return model


# Pre-load model on startup if present
get_model()


@app.route("/")
def index():
    """Serve the single-page frontend."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/predict", methods=["POST"])
def predict():
    """
    Decisive verification endpoint:
    Eliminates ambiguity percentages and verifies every claim against Google News and ChatGPT.
    Expects JSON: {"text": "...", "openai_api_key": "(optional)"}
    """
    # 1. Validate JSON presence
    if not request.is_json:
        return jsonify({
            "error": "Invalid request content-type. Please send JSON with 'Content-Type: application/json'."
        }), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "error": "Malformed JSON body. Expected a JSON object containing a 'text' field."
        }), 400

    raw_text = data.get("text")
    openai_api_key = data.get("openai_api_key") or os.getenv("OPENAI_API_KEY")

    if raw_text is None or not isinstance(raw_text, str) or not raw_text.strip():
        return jsonify({
            "error": "The 'text' field is required and cannot be empty."
        }), 400

    # 2. Check word count (minimum 10 words)
    words = raw_text.strip().split()
    if len(words) < 10:
        return jsonify({
            "error": f"Input text is too short ({len(words)} words). Please provide at least 10 words for an accurate analysis."
        }), 400

    # 3. Check model availability
    current_model = get_model()
    if current_model is None:
        return jsonify({
            "error": "Model file 'models/factforge.joblib' is not found. Please train the model first by running 'python train.py' in your terminal."
        }), 503

    # 4. Clean text and run integrated inference
    try:
        cleaned_text = clean(raw_text)
        probs = current_model.predict_proba([cleaned_text])[0]
        classes = list(current_model.classes_)

        idx_fake = classes.index(1)
        ml_prob_fake = float(probs[idx_fake])

        # Decisive verification (Google News + Wikipedia + ChatGPT)
        (
            label,
            confidence,
            score_label,
            verdict_title,
            signals,
            explanation,
            verification,
        ) = evaluate_credibility(
            raw_text,
            ml_prob_fake,
            openai_api_key=openai_api_key,
        )

        return jsonify({
            "label": label,
            "confidence": confidence,
            "score_label": score_label,
            "verdict_title": verdict_title,
            "signals": signals,
            "explanation": explanation,
            "verification": verification,
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"An unexpected error occurred during prediction: {str(e)}"
        }), 500


if __name__ == "__main__":
    port = 5001
    print("\n" + "=" * 60)
    print("🔨 FactForge Web Server (Decisive Real/Fake Answer + Image OCR)")
    print(f"👉 Local URL: http://127.0.0.1:{port}")
    if model is None:
        print("⚠️  Warning: Model not found. Run 'python train.py' to generate 'models/factforge.joblib'.")
    else:
        print("✅ Model loaded and ready for predictions.")
    print("=" * 60 + "\n")

    app.run(host="127.0.0.1", port=port, debug=True)
