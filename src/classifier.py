TYPE_A = "TYPE_A"
TYPE_B = "TYPE_B"

_KEYWORDS_A = [
    "125%",
    "150%",
    "שבת",
    "הפסקה",
    "סה\"כ",
    "נ.ע. הנשר",
    "100%",
    "היציאה",
    "כניסה",
]

_KEYWORDS_B = [
    "attendance report",
    "total days",
    "total hours",
    "date",
    "location",
    "break",
    "day",
]


def identify_report_type(text):
    """Identify the report type from raw OCR text using keyword scoring."""
    if not text or not text.strip():
        return TYPE_B

    # אם רוב השורות עם תוכן הן שורות טבלאיות עם | — זה TYPE_B בלי קשר לניקוד מילות
    content_lines = [l for l in text.splitlines() if l.strip()]
    pipe_lines = [l for l in content_lines if '|' in l]
    if len(content_lines) > 0 and len(pipe_lines) / len(content_lines) >= 0.4:
        return TYPE_B

    normalized = text.lower()
    score_a = sum(normalized.count(keyword.lower()) for keyword in _KEYWORDS_A)
    score_b = sum(normalized.count(keyword.lower()) for keyword in _KEYWORDS_B)

    if score_a == score_b:
        if any(keyword in normalized for keyword in ["125%", "150%", "שבת", "נ.ע. הנשר"]):
            return TYPE_A
        return TYPE_B

    return TYPE_A if score_a > score_b else TYPE_B
