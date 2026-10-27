"""
voting/chat_sentiment.py
────────────────────────
Stateless sentiment analysis for parsed chat messages (SCRUM-27).

Uses VADER (vaderSentiment), a lexicon/rule-based analyzer tuned for short,
social-media style English text. Each message is classified by its compound
score:

    compound >= 0.05  -> positive
    compound <= -0.05 -> negative
    otherwise         -> neutral

    analyze_sentiment(messages) -> dict

Media-only messages ("<Media omitted>") and empty messages carry no text and are
skipped. The analyzer is created once and reused. No DB access.
"""

from collections import defaultdict

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# ─── Configuración y analizador (singleton) ────────────────────────────────────
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05

_analyzer = None


def _get_analyzer():
    # Se crea una sola vez y se reutiliza (instanciar VADER carga su lexicon,
    # no es gratis hacerlo en cada mensaje).
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentIntensityAnalyzer()
    return _analyzer


# ─── Clasificación de un mensaje individual ────────────────────────────────────
def classify(text: str) -> str:
    """Return 'positive', 'negative', or 'neutral' for a single message."""
    if not text or not text.strip():
        return "neutral"
    compound = _get_analyzer().polarity_scores(text)["compound"]  # float entre -1.0 y 1.0
    if compound >= POSITIVE_THRESHOLD:
        return "positive"
    if compound <= NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"   # zona muerta entre los 2 umbrales


# ─── Helpers de agregación ──────────────────────────────────────────────────────
def _overall_label(counts: dict) -> str:
    """Pick the dominant tone; ties fall back to neutral."""
    if not any(counts.values()):
        return "neutral"
    best = max(counts, key=lambda k: counts[k])
    top = counts[best]
    if list(counts.values()).count(top) > 1:   # empate entre 2+ categorías -> neutral
        return "neutral"
    return best


def _pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


# ─── Función principal: analyze_sentiment() ────────────────────────────────────
def analyze_sentiment(messages: list) -> dict:
    """Classify every (non-media) message and aggregate overall / per author."""
    overall = {"positive": 0, "negative": 0, "neutral": 0}
    per_author = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})

    for m in messages:
        if m.get("is_media"):
            continue   # fotos/videos no tienen texto real que analizar
        label = classify(m.get("text", ""))
        overall[label] += 1
        per_author[m["author"]][label] += 1

    analyzed = sum(overall.values())   # total NO-media; es el denominador de los %

    per_participant_sentiment = []
    for author in sorted(per_author):
        counts = per_author[author]
        per_participant_sentiment.append({
            "name": author,
            "positive": counts["positive"],
            "negative": counts["negative"],
            "neutral": counts["neutral"],
            "overall": _overall_label(counts),
        })

    return {
        "sentiment": {
            "positive": overall["positive"],
            "negative": overall["negative"],
            "neutral": overall["neutral"],
            "analyzed": analyzed,
            "positive_pct": _pct(overall["positive"], analyzed),
            "negative_pct": _pct(overall["negative"], analyzed),
            "neutral_pct": _pct(overall["neutral"], analyzed),
            "overall": _overall_label(overall),
        },
        "per_participant_sentiment": per_participant_sentiment,
    }
