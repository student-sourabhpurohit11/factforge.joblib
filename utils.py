import os
import re
import ssl
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict, Any, Optional

# SSL Context for external requests
SSL_CTX = ssl._create_unverified_context()

# Common debunked conspiracy tropes, pseudoscientific myths, and known hoax signatures
CONSPIRACY_PATTERNS = [
    (r'\b(?:forged\s+birth\s+certificate|born\s+in\s+kenya|birther)\b', 'Debunked birther conspiracy claim'),
    (r'\b(?:flat\s+earth|earth\s+is\s+flat)\b', 'Flat earth pseudoscience claim'),
    (r'\b(?:moon\s+landing\s+(?:hoax|faked|staged)|faked\s+the\s+moon\s+landing)\b', 'Moon landing hoax claim'),
    (r'\b(?:microchips?\s+in\s+vaccines?|vaccines?\s+contain\s+microchips?|5g\s+causes?\s+covid)\b', 'Debunked medical / 5G conspiracy claim'),
    (r'\b(?:crisis\s+actors?|staged\s+shooting\s+hoax|false\s+flag\s+staged)\b', 'Crisis actor / false flag fabrication trope'),
    (r'\b(?:miracle\s+cure\s+suppressed|cancer\s+cure\s+hidden|doctors\s+hate\s+this|secret\s+cure\s+the\s+fda)\b', 'Suppressed miracle cure trope'),
    (r'\b(?:pizzagate|qanon|adrenochrome|reptilian\s+overlords?)\b', 'Disproven extremist conspiracy theory'),
    (r'\b(?:chemtrails?\s+poisoning|chemtrails?\s+are\s+spraying)\b', 'Chemtrail weather/chemical conspiracy'),
    (r'\b(?:cloned\s+politicians?|body\s+double\s+clone)\b', 'Political clone / body double conspiracy trope'),
    (r'\b(?:hacked\s+voting\s+machines?\s+flipped\s+millions|secret\s+watermarks?\s+on\s+ballots)\b', 'Debunked systemic election fraud trope'),
    (r'\b(?:green\s+cheese|aliens?\s+built\s+the\s+pyramids)\b', 'Mythological / pseudohistorical fabrication'),
]

# Sensationalist, urgency, and manipulative clickbait framing
SENSATIONAL_PATTERNS = [
    (r'\b(?:bombshell|shocking|unbelievable|mind-blowing|must-see|wake\s+up\s+people|wake\s+up\s+sheeple)\b', 'Sensationalist urgency framing'),
    (r'\b(?:share\s+before\s+(?:it\'?s\s+deleted|censored)|mainstream\s+media\s+won\'?t\s+tell\s+you|what\s+they\s+are\s+hiding)\b', 'Conspiratorial viral-bait framing'),
    (r'\b(?:guaranteed\s+secret|100%\s+undeniable\s+proof|whistleblower\s+exposes\s+everything)\b', 'Absolute hyperbole without verification'),
]

FACT_CHECK_KEYWORDS = ['fact check', 'false', 'debunked', 'hoax', 'misleading', 'conspiracy', 'claims', 'myth', 'unproven', 'debunk']
REPUTABLE_OUTLETS = [
    'reuters', 'associated press', 'ap news', 'bbc', 'bloomberg', 'wsj', 'wall street journal',
    'the new york times', 'washington post', 'npr', 'pbs', 'nbc news', 'cbs news', 'abc news',
    'cnn', 'the guardian', 'financial times', 'factcheck.org', 'politifact', 'snopes', 'lead stories'
]


def clean(text: str) -> str:
    """Cleans raw news text: removes wire headers, URLs, and collapses whitespaces."""
    if not isinstance(text, str):
        text = str(text or "")

    text = re.sub(
        r'^[A-Za-z\s,.-]+?\s*\([^)]*(?:reuters|ap|afp|cnn)[^)]*\)\s*[-—–:]\s*',
        '',
        text,
        flags=re.IGNORECASE
    )
    text = re.sub(
        r'^\s*\((?:reuters|ap|afp|cnn)\)\s*[-—–:]\s*',
        '',
        text,
        flags=re.IGNORECASE
    )
    text = re.sub(
        r'^\s*(?:reuters|associated press)\s*[-—–:]\s*',
        '',
        text,
        flags=re.IGNORECASE
    )
    text = re.sub(r'\b(?:reuters|associated press)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'<.*?>', '', text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_search_query(text: str) -> str:
    """Extracts high-signal entities and factual claim keywords for search verification."""
    for pattern, _ in CONSPIRACY_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            proper = re.findall(r'\b[A-Z][a-z0-9]+\b', text)
            subj = proper[0] if proper else ""
            return f"{subj} {match.group(0)} fact check".strip()

    proper_nouns = re.findall(r'\b[A-Z][a-z0-9]+\b', text)
    common_starters = {'The', 'This', 'That', 'These', 'Those', 'According', 'Yesterday', 'Today', 'Breaking', 'New', 'Officials', 'Watch', 'Alert', 'Exclusive'}
    filtered_proper = [w for w in proper_nouns if w not in common_starters]

    words = re.findall(r'[A-Za-z0-9]+', text)
    stopwords = {
        'the', 'a', 'an', 'is', 'was', 'were', 'are', 'been', 'be', 'have', 'has', 'had',
        'and', 'or', 'to', 'in', 'on', 'at', 'by', 'for', 'with', 'about', 'against',
        'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'from', 'up', 'down', 'of', 'off', 'over', 'under', 'again', 'further', 'then',
        'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both',
        'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
        'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just',
        'should', 'now', 'that', 'this', 'these', 'those', 'according', 'reported',
        'says', 'said', 'claim', 'claims', 'breaking', 'news', 'also'
    }
    topical = [w for w in words if w.lower() not in stopwords]

    combined = []
    for w in filtered_proper + topical:
        if w.lower() not in [x.lower() for x in combined]:
            combined.append(w)

    return ' '.join(combined[:6])


def search_google_news(query: str) -> List[Dict[str, str]]:
    """Live search on Google News RSS for real-world corroboration and fact-checks."""
    if not query.strip():
        return []
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
    items = []
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
            root = ET.fromstring(resp.read())
            for it in root.findall('.//item')[:5]:
                title = it.find('title').text if it.find('title') is not None else ''
                source = it.find('source').text if it.find('source') is not None else 'News Source'
                link = it.find('link').text if it.find('link') is not None else ''
                items.append({
                    'title': title,
                    'source': source,
                    'link': link
                })
    except Exception as e:
        print(f"[WARN] Google News live query failed: {e}")
    return items


def search_wikipedia(query: str) -> List[Dict[str, str]]:
    """Live search on Wikipedia for encyclopedia context and documented hoaxes/conspiracies."""
    if not query.strip():
        return []
    url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&utf8="
    req = urllib.request.Request(url, headers={'User-Agent': 'FactForge-Verifier/2.0 (contact@factforge.local)'})
    results = []
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            for item in data.get('query', {}).get('search', [])[:2]:
                title = item.get('title', '')
                snippet = re.sub(r'<.*?>', '', item.get('snippet', ''))
                results.append({
                    'title': title,
                    'snippet': snippet,
                    'url': f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                })
    except Exception as e:
        print(f"[WARN] Wikipedia live query failed: {e}")
    return results


def query_chatgpt(claim_text: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Queries OpenAI ChatGPT (gpt-4o-mini) to cross-verify the claim.
    Returns structured verification or None if no key is configured.
    """
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key or not key.strip():
        return None

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key.strip()}"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict, objective fact-checking assistant. "
                    "Analyze the given news claim or text for factual veracity. "
                    "Respond with a valid JSON object with keys: "
                    "'verdict' ('VERIFIED_TRUE', 'DEBUNKED_FALSE', or 'UNVERIFIED'), "
                    "'confidence' (number 0-100), "
                    "'summary' (1-2 sentence concise factual breakdown), "
                    "'sources_note' (mention accredited news outlets or fact-checkers)."
                )
            },
            {"role": "user", "content": claim_text}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }

    try:
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers=headers)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
            result = json.loads(resp.read().decode())
            content = result['choices'][0]['message']['content']
            parsed = json.loads(content)
            parsed["model"] = "ChatGPT (gpt-4o-mini)"
            return parsed
    except Exception as e:
        print(f"[WARN] ChatGPT API query failed: {e}")
        return {
            "verdict": "ERROR",
            "summary": f"ChatGPT verification error: {str(e)}",
            "model": "ChatGPT (Offline)"
        }


def verify_with_live_knowledge(
    raw_text: str,
    has_hard_conspiracy: bool = False,
    openai_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Matches input claim against live Google News, Wikipedia, and optional ChatGPT.
    Ensures real-world facts are verified before showing results to users.
    """
    query = extract_search_query(raw_text)
    google_news = search_google_news(query)
    wikipedia = search_wikipedia(query)
    chatgpt_result = query_chatgpt(raw_text, openai_api_key)

    # Analyze Google News matches
    fact_check_matches = []
    reputable_matches = []
    for item in google_news:
        t_low = item['title'].lower()
        s_low = item['source'].lower()
        if any(kw in t_low or kw in s_low for kw in FACT_CHECK_KEYWORDS):
            fact_check_matches.append(item)
        if any(out in s_low for out in REPUTABLE_OUTLETS):
            reputable_matches.append(item)

    # Check Wikipedia debunk signals
    wiki_debunk = False
    for w in wikipedia:
        comb = (w['title'] + " " + w['snippet']).lower()
        if any(term in comb for term in ['conspiracy theory', 'hoax', 'debunked', 'discredited', 'false claim', 'pseudoscience']):
            wiki_debunk = True
            break

    # Determine Knowledge Match Status with strict guardrails
    if has_hard_conspiracy or fact_check_matches or wiki_debunk or (chatgpt_result and chatgpt_result.get("verdict") == "DEBUNKED_FALSE"):
        live_status = "DEBUNKED"
        live_summary = "Refuted by live fact-checking networks, historical public records, or documented conspiracy databases."
    elif len(reputable_matches) >= 2 or (chatgpt_result and chatgpt_result.get("verdict") == "VERIFIED_TRUE"):
        live_status = "CORROBORATED"
        live_summary = "Corroborated by independent news coverage across accredited reporting organizations."
    elif len(google_news) == 0:
        live_status = "NO_SOURCES_FOUND"
        live_summary = "Zero mainstream coverage found for this claim across Google News. Classified as an unsubstantiated rumor."
    else:
        live_status = "UNVERIFIED"
        live_summary = "Limited or ambiguous news coverage found. Not verified by accredited journalism."

    return {
        "query_used": query,
        "live_status": live_status,
        "live_summary": live_summary,
        "google_news_matches": google_news,
        "wikipedia_matches": wikipedia,
        "chatgpt_result": chatgpt_result
    }


def evaluate_credibility(
    raw_text: str,
    ml_prob_fake: float,
    openai_api_key: Optional[str] = None
) -> Tuple[str, float, str, str, List[str], str, Dict[str, Any]]:
    """
    Decisive multi-source verification:
    Eliminates ambiguity percentages and returns a definitive REAL or FAKE verdict
    substantiated by Google News, Wikipedia, and ChatGPT.

    Returns:
        label (str): 'REAL' or 'FAKE'
        confidence (float): definite percentage (e.g., 94.5)
        score_label (str): 'Authenticity Score' or 'Misinformation Risk'
        verdict_title (str): 'VERIFIED REAL NEWS' or 'FAKE / MISINFORMATION'
        signals (List[str]): list of detected indicators
        explanation (str): authoritative breakdown
        knowledge (dict): Google & ChatGPT verification payload
    """
    signals: List[str] = []
    risk_boost = 0.0

    # 1. Scan for debunked conspiracy tropes
    has_hard_conspiracy = False
    for pattern, desc in CONSPIRACY_PATTERNS:
        if re.search(pattern, raw_text, re.IGNORECASE):
            signals.append(desc)
            risk_boost += 0.50
            has_hard_conspiracy = True

    # 2. Scan for sensational clickbait framing
    for pattern, desc in SENSATIONAL_PATTERNS:
        if re.search(pattern, raw_text, re.IGNORECASE):
            signals.append(desc)
            risk_boost += 0.20

    # 3. Formatting heuristics
    tokens = raw_text.split()
    caps_count = sum(1 for w in tokens if len(w) >= 4 and w.isupper())
    if caps_count >= 3:
        signals.append("Excessive uppercase formatting (emotional intensity)")
        risk_boost += 0.15

    if re.search(r'[!?]{2,}', raw_text):
        signals.append("Multiple dramatic punctuation marks (!/?)")
        risk_boost += 0.10

    # 4. Live Knowledge Source Verification (Google News + Wikipedia + ChatGPT)
    knowledge = verify_with_live_knowledge(raw_text, has_hard_conspiracy=has_hard_conspiracy, openai_api_key=openai_api_key)

    if knowledge["live_status"] == "DEBUNKED":
        signals.append("Live Fact-Check Match: Refuted by accredited fact-checkers / encyclopedia records")
        risk_boost += 0.60
    elif knowledge["live_status"] == "NO_SOURCES_FOUND":
        signals.append("Live Search Warning: Zero accredited news sources report this claim")
        risk_boost += 0.40

    # Synthesize hybrid probability
    hybrid_prob_fake = min(0.99, ml_prob_fake + risk_boost)

    # 5. Decisive Real Answer (No Ambiguity Percentages)
    # If corroborated by reputable news on Google News and no debunk flags -> REAL
    if knowledge["live_status"] == "CORROBORATED" and not has_hard_conspiracy and hybrid_prob_fake < 0.50:
        label = "REAL"
        confidence = round(max(0.85, 1.0 - hybrid_prob_fake) * 100, 1)
        score_label = "Authenticity Score"
        verdict_title = "VERIFIED REAL NEWS"
        explanation = (
            "Corroborated by live accredited news reporting and supported by standard journalistic writing style."
        )
    else:
        # If debunked, conspiracy, 0 sources found, or high fake probability -> FAKE
        label = "FAKE"
        confidence = round(max(0.85, hybrid_prob_fake) * 100, 1)
        score_label = "Misinformation Risk"
        verdict_title = "FAKE / MISINFORMATION"
        if has_hard_conspiracy or knowledge["live_status"] == "DEBUNKED":
            explanation = (
                "Identified as false information. Cross-referencing against Google News and "
                "fact-checking databases revealed documented hoaxes or debunked claims."
            )
        elif knowledge["live_status"] == "NO_SOURCES_FOUND":
            explanation = (
                "Unsubstantiated rumor. Zero accredited news outlets have reported this claim on Google News. "
                "In journalism, extraordinary claims lacking any reporting are classified as fabricated rumors."
            )
        else:
            explanation = (
                "Flagged as likely misinformation based on sensationalist rhetoric, unverified claims, "
                "and high linguistic risk markers."
            )

    return label, confidence, score_label, verdict_title, signals, explanation, knowledge
