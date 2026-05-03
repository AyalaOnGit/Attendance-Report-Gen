TYPE_A = 'TYPE_A'
TYPE_B = 'TYPE_B'

_KEYWORDS_A = ['125%', '150%', 'שבת', 'הפסקה', 'סה"כ', 'נ.ע. הנשר', '100%', 'היציאה', 'כניסה']
_KEYWORDS_B = ['attendance report', 'total days', 'total hours', 'date', 'location', 'break', 'day']


def identify_report_type(text: str) -> str:
    if not text or not text.strip():
        return TYPE_B

    content_lines = [l for l in text.splitlines() if l.strip()]
    pipe_lines = [l for l in content_lines if '|' in l]
    if content_lines and len(pipe_lines) / len(content_lines) >= 0.4:
        return TYPE_B

    normalized = text.lower()
    score_a = sum(normalized.count(k.lower()) for k in _KEYWORDS_A)
    score_b = sum(normalized.count(k.lower()) for k in _KEYWORDS_B)

    if score_a == score_b:
        return TYPE_A if any(k in normalized for k in ['125%', '150%', 'שבת', 'נ.ע. הנשר']) else TYPE_B
    return TYPE_A if score_a > score_b else TYPE_B
