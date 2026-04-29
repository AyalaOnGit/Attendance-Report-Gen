import re
from typing import Optional, Any
from domain import AttendanceReport, AttendanceRow
from logic import extract_employee_name, get_day_of_week

DATE_PATTERN = re.compile(r'\b(\d{1,2}[/.]\d{1,2}[/.]\d{2,4})\b')
TIME_PATTERN = re.compile(r'\b(\d{1,2}[:.](?:[0-5]\d))\b')

_MIN_ENTRY = 5 * 60
_MAX_ENTRY = 13 * 60
_MIN_EXIT  = 10 * 60
_MAX_EXIT  = 24 * 60
_MIN_SHIFT = 60
_MAX_SHIFT = 14 * 60


def _normalize_date(raw: str) -> str:
    parts = re.split(r'[/.]', raw)
    if len(parts) != 3:
        return raw
    d, m, y = parts
    if len(y) == 2:
        y = '20' + y
    return f"{d.zfill(2)}/{m.zfill(2)}/{y}"


def _is_valid_date(date_str: str) -> bool:
    try:
        import pandas as pd
        parts = date_str.split('/')
        if len(parts) != 3:
            return False
        d, m = int(parts[0]), int(parts[1])
        if not (1 <= d <= 31 and 1 <= m <= 12):
            return False
        pd.to_datetime(date_str, dayfirst=True)
        return True
    except Exception:
        return False


def _to_min(t: str) -> int:
    h, m = map(int, t.split(':'))
    return h * 60 + m


def _extract_location(text: str) -> str:
    hebrew_words = re.findall(r'[\u05d0-\u05ea]{3,}', text)
    stop = {
        'יום', 'שעות', 'סהכ', 'תאריך', 'כניסה', 'יציאה', 'הפסקה', 'ראשון',
        'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'חודש', 'עובד',
        'שם', 'בעמ', 'אדם', 'כח', 'הנשר', 'נוכחות', 'דוח', 'ימים', 'שעה',
    }
    counts: dict = {}
    for w in hebrew_words:
        if w not in stop:
            counts[w] = counts.get(w, 0) + 1
    if counts:
        best = max(counts, key=lambda w: counts[w])
        if counts[best] >= 2:
            return best
    return 'נ.ע. הנשר'


# ---------------------------------------------------------------------------
# Template Method – BaseParser מגדיר את שלד האלגוריתם
# ---------------------------------------------------------------------------

class BaseParser:
    """
    Template Method: parse() מגדיר את רצף השלבים הקבוע.
    Subclasses עוקפים את _is_header_line(), _parse_row(), ו-_parse_summary().
    """

    def __init__(self, text: str, layout: Any = None):
        self.text = text
        self.layout = layout
        self.lines = [line.strip() for line in text.splitlines() if line.strip()]

    # ------------------------------------------------------------------
    # שלד האלגוריתם – אין לעקוף
    # ------------------------------------------------------------------

    def parse(self) -> AttendanceReport:
        location = _extract_location(self.text)
        seen: set = set()
        rows = []
        current_date = ''

        for line in self.lines:
            if self._is_header_line(line):
                continue

            row, current_date = self._parse_row(line, current_date, location)
            if row is None:
                continue

            key = (row.date, row.entry)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

        summary = self._parse_summary()
        emp_name = self._extract_employee_name()
        return AttendanceReport(
            rows=rows,
            report_type=getattr(self, 'report_type', 'GENERIC'),
            employee_name=emp_name,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # שיטות שה-subclasses עוקפים
    # ------------------------------------------------------------------

    def _is_header_line(self, line: str) -> bool:
        raise NotImplementedError

    def _parse_row(self, line: str, current_date: str,
                   location: str) -> tuple[Optional[AttendanceRow], str]:
        """מחזיר (row_or_None, updated_current_date)."""
        raise NotImplementedError

    def _parse_summary(self) -> dict:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # עזר משותף
    # ------------------------------------------------------------------

    def _extract_employee_name(self) -> str:
        name = extract_employee_name(self.text)
        if not name or name == 'לא זוהה':
            m = re.search(r'שם העובד[:\s]+([^\n\r|,]{2,30})', self.text)
            if m:
                name = m.group(1).strip()
        return name or 'עובד כללי'

    @staticmethod
    def _pick_entry_exit(times: list[str]) -> tuple[Optional[str], Optional[str]]:
        valid_entries = [t for t in times if _MIN_ENTRY <= _to_min(t) <= _MAX_ENTRY]
        valid_exits   = [t for t in times if _MIN_EXIT  <= _to_min(t) <= _MAX_EXIT]
        if not valid_entries or not valid_exits:
            return None, None
        entry = min(valid_entries, key=_to_min)
        exit_ = max(valid_exits,   key=_to_min)
        shift = _to_min(exit_) - _to_min(entry)
        if not (_MIN_SHIFT <= shift <= _MAX_SHIFT):
            return None, None
        return entry, exit_

    @staticmethod
    def _build_row(date: str, entry: str, exit_: str,
                   location: str) -> Optional[AttendanceRow]:
        if not _is_valid_date(date):
            return None
        return AttendanceRow(
            date=date,
            day=get_day_of_week(date),
            location=location,
            entry=entry,
            exit=exit_,
            break_minutes='00:30',
            total='0.0',
            h100='0.0',
        )


# ---------------------------------------------------------------------------
# TypeAParser – שורות חופשיות, תאריך מופיע לסירוגין → מפיץ קדימה
# ---------------------------------------------------------------------------

_HEADER_KEYWORDS_A = {'תאריך', 'כניסה', 'יציאה', 'הפסקה', 'סהכ', 'שבת', '100%', '125%', '150%'}


class TypeAParser(BaseParser):
    report_type = 'TYPE_A'

    def _is_header_line(self, line: str) -> bool:
        words = set(re.sub(r'[|%"\']', ' ', line).split())
        return bool(words & _HEADER_KEYWORDS_A)

    def _parse_row(self, line: str, current_date: str,
                   location: str) -> tuple[Optional[AttendanceRow], str]:
        clean = re.sub(r'[|\[\]]', ' ', line)
        clean = ' '.join(clean.split())

        date_match = DATE_PATTERN.search(clean)
        if date_match:
            candidate = _normalize_date(date_match.group(1))
            if _is_valid_date(candidate):
                current_date = candidate

        if not current_date:
            return None, current_date

        times = [t.replace('.', ':') for t in TIME_PATTERN.findall(clean)]
        if len(times) < 2:
            return None, current_date

        entry, exit_ = self._pick_entry_exit(times)
        if entry is None:
            return None, current_date

        return self._build_row(current_date, entry, exit_, location), current_date

    def _parse_summary(self) -> dict:
        summary = {}
        m = re.search(r'סה"כ\s+שעות[:\s]+([\d.]+)', self.text)
        if m:
            summary['total_hours'] = m.group(1)
        m = re.search(r'(\d+)\s+ימים', self.text)
        if m:
            summary['total_days'] = m.group(1)
        return summary


# ---------------------------------------------------------------------------
# TypeBParser – טבלה עם מפרידי |, תאריך בתא ראשון
# ---------------------------------------------------------------------------

_HEADER_KEYWORDS_B = {'date', 'day', 'entry', 'exit', 'break', 'location',
                       'תאריך', 'כניסה', 'יציאה', 'הפסקה', 'מקום'}


class TypeBParser(BaseParser):
    report_type = 'TYPE_B'

    def _is_header_line(self, line: str) -> bool:
        if '|' not in line:
            return False
        words = {w.lower().strip() for w in line.split('|')}
        return bool(words & _HEADER_KEYWORDS_B)

    def _parse_row(self, line: str, current_date: str,
                   location: str) -> tuple[Optional[AttendanceRow], str]:
        if '|' not in line:
            return None, current_date

        cells = [c.strip() for c in line.split('|')]

        date_val = ''
        for cell in cells:
            m = DATE_PATTERN.search(cell)
            if m:
                candidate = _normalize_date(m.group(1))
                if _is_valid_date(candidate):
                    date_val = candidate
                    current_date = candidate
                    break

        if not date_val:
            date_val = current_date
        if not date_val:
            return None, current_date

        times = []
        for cell in cells:
            for t in TIME_PATTERN.findall(cell):
                times.append(t.replace('.', ':'))

        if len(times) < 2:
            return None, current_date

        entry, exit_ = self._pick_entry_exit(times)
        if entry is None:
            return None, current_date

        return self._build_row(date_val, entry, exit_, location), current_date

    def _parse_summary(self) -> dict:
        summary = {}
        m = re.search(r'סה"כ\s+ימי\s+עבודה[:\s]+(\d+)', self.text)
        if m:
            summary['total_days'] = m.group(1)
        m = re.search(r'סה"כ\s+שעות\s+חודשיות[:\s]+([\d.]+)', self.text)
        if m:
            summary['total_hours'] = m.group(1)
        return summary
