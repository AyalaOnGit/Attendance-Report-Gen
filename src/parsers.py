import datetime
import re
from typing import Optional, Any
from domain import AttendanceReport, AttendanceRow
from logic import extract_employee_name, get_day_of_week
from rules import PARSER_RULES

DATE_PATTERN = re.compile(r'\b(\d{1,2}[/.]\d{1,2}[/.]\d{2,4})\b')
TIME_PATTERN = re.compile(r'\b(\d{1,2}[:.](?:[0-5]\d))\b')


# ---------------------------------------------------------------------------
# Parsing helpers — strings → typed values (done ONCE at the boundary)
# ---------------------------------------------------------------------------

def _parse_date(raw: str) -> Optional[datetime.date]:
    parts = re.split(r'[/.]', raw)
    if len(parts) != 3:
        return None
    d, m, y = parts
    if len(y) == 2:
        y = '20' + y
    try:
        return datetime.date(int(y), int(m), int(d))
    except ValueError:
        return None


def _parse_time(raw: str) -> Optional[datetime.time]:
    try:
        h, m = map(int, raw.replace('.', ':').split(':'))
        return datetime.time(h, m)
    except (ValueError, AttributeError):
        return None


def _is_valid_entry(t: datetime.time) -> bool:
    return PARSER_RULES.min_entry <= t <= PARSER_RULES.max_entry


def _is_valid_exit(t: datetime.time) -> bool:
    return PARSER_RULES.min_exit <= t <= PARSER_RULES.max_exit


def _shift_minutes(entry: datetime.time, exit_: datetime.time) -> int:
    return (exit_.hour * 60 + exit_.minute) - (entry.hour * 60 + entry.minute)


def _extract_location(text: str, pipe_rows_only: bool = False) -> str:
    """
    Scans lines for a recurring Hebrew word that is likely a location name.
    pipe_rows_only=True: only considers pipe-delimited rows with a date (TYPE B).
    pipe_rows_only=False: scans all text (TYPE A).
    """
    DAYS = {'ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת'}
    stop = {
        'יום', 'שעות', 'שעת', 'סהכ', 'תאריך', 'כניסה', 'יציאה', 'הפסקה',
        'עובד', 'שם', 'בעמ', 'אדם', 'כח', 'הנשר', 'נוכחות', 'דוח',
        'ימים', 'שעה', 'סהכימי', 'לחודש', 'בשבוע', 'הערות', 'מספר',
        'עבודה', 'השנה', 'העובד', 'חודש',
    } | DAYS

    counts: dict = {}
    for line in text.splitlines():
        if pipe_rows_only and ('|' not in line or not DATE_PATTERN.search(line)):
            continue
        for word in re.findall(r'[\u05d0-\u05ea]{3,}', line):
            if word not in stop:
                counts[word] = counts.get(word, 0) + 1

    if counts:
        best = max(counts, key=lambda w: counts[w])
        if counts[best] >= 2:
            return best
    return ''


# ---------------------------------------------------------------------------
# Template Method — BaseParser defines the algorithm skeleton
# ---------------------------------------------------------------------------

class BaseParser:
    """
    Template Method: parse() defines the fixed sequence of steps.
    Subclasses override only _is_header_line(), _parse_row(), _parse_summary().
    """

    def __init__(self, text: str, layout: Any = None):
        self.text = text
        self.layout = layout
        self.lines = [line.strip() for line in text.splitlines() if line.strip()]

    # --- algorithm skeleton (do not override) ---

    def parse(self) -> AttendanceReport:
        location = self._get_location(self.text)
        seen: set = set()
        rows = []
        current_date: Optional[datetime.date] = None

        for line in self.lines:
            if self._is_header_line(line):
                continue

            # Data sanitization happens ONCE here, before subclass logic sees the line
            clean = self._clean_line(line)
            row, current_date = self._parse_row(clean, current_date, location)
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
            rows=tuple(rows),
            report_type=getattr(self, 'report_type', 'GENERIC'),
            employee_name=emp_name,
            summary=summary,
        )

    @staticmethod
    def _clean_line(line: str) -> str:
        """Sanitize OCR noise once, at the boundary, before any parsing logic."""
        clean = re.sub(r'[\[\]{}]', ' ', line)
        return ' '.join(clean.split())

    # --- methods subclasses must override ---

    def _is_header_line(self, line: str) -> bool:
        raise NotImplementedError

    def _parse_row(
        self, line: str,
        current_date: Optional[datetime.date],
        location: str,
    ) -> tuple[Optional[AttendanceRow], Optional[datetime.date]]:
        """Receives a pre-cleaned line. Returns (row_or_None, updated_current_date)."""
        raise NotImplementedError

    def _parse_summary(self) -> dict:
        raise NotImplementedError

    def _get_location(self, text: str) -> str:
        raise NotImplementedError

    # --- shared helpers ---

    def _extract_employee_name(self) -> str:
        name = extract_employee_name(self.text)
        if not name or name == 'לא זוהה':
            m = re.search(r'שם העובד[:\s]+([^\n\r|,]{2,30})', self.text)
            if m:
                name = m.group(1).strip()
        return name or 'עובד כללי'

    @staticmethod
    def _pick_entry_exit(
        raw_times: list[str],
    ) -> tuple[Optional[datetime.time], Optional[datetime.time]]:
        times = [t for raw in raw_times if (t := _parse_time(raw)) is not None]
        entries = [t for t in times if _is_valid_entry(t)]
        exits   = [t for t in times if _is_valid_exit(t)]
        if not entries or not exits:
            return None, None
        entry = min(entries)
        exit_ = max(exits)
        shift = _shift_minutes(entry, exit_)
        if not (PARSER_RULES.min_shift_minutes <= shift <= PARSER_RULES.max_shift_minutes):
            return None, None
        return entry, exit_

    @staticmethod
    def _build_row(
        date: datetime.date,
        entry: datetime.time,
        exit_: datetime.time,
        location: str,
    ) -> AttendanceRow:
        return AttendanceRow(
            date=date,
            day=get_day_of_week(date),
            location=location,
            entry=entry,
            exit=exit_,
            break_minutes=PARSER_RULES.break_minutes,
        )


# ---------------------------------------------------------------------------
# TypeAParser — free-form lines, date propagates forward
# ---------------------------------------------------------------------------

_HEADER_KEYWORDS_A = {
    'תאריך', 'כניסה', 'יציאה', 'הפסקה', 'סהכ', 'שבת', '100%', '125%', '150%',
}


class TypeAParser(BaseParser):
    report_type = 'TYPE_A'

    def _get_location(self, text: str) -> str:
        return _extract_location(text, pipe_rows_only=False)

    def _is_header_line(self, line: str) -> bool:
        words = set(re.sub(r'[|%"\'()]', ' ', line).split())
        return bool(words & _HEADER_KEYWORDS_A)

    def _parse_row(
        self, line: str,
        current_date: Optional[datetime.date],
        location: str,
    ) -> tuple[Optional[AttendanceRow], Optional[datetime.date]]:
        date_match = DATE_PATTERN.search(line)
        if date_match:
            candidate = _parse_date(date_match.group(1))
            if candidate is not None:
                current_date = candidate

        if current_date is None:
            return None, current_date

        raw_times = [t.replace('.', ':') for t in TIME_PATTERN.findall(line)]
        entry, exit_ = self._pick_entry_exit(raw_times)
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
# TypeBParser — pipe-delimited table, date in first cell
# ---------------------------------------------------------------------------

_HEADER_KEYWORDS_B = {
    'date', 'day', 'entry', 'exit', 'break', 'location',
    'תאריך', 'כניסה', 'יציאה', 'הפסקה', 'מקום',
}


class TypeBParser(BaseParser):
    report_type = 'TYPE_B'

    def _get_location(self, text: str) -> str:
        return _extract_location(text, pipe_rows_only=True)

    def _is_header_line(self, line: str) -> bool:
        if '|' not in line:
            return False
        words = {w.lower().strip() for w in line.split('|')}
        return bool(words & _HEADER_KEYWORDS_B)

    def _parse_row(
        self, line: str,
        current_date: Optional[datetime.date],
        location: str,
    ) -> tuple[Optional[AttendanceRow], Optional[datetime.date]]:
        if '|' not in line:
            return None, current_date

        cells = [c.strip() for c in line.split('|')]

        for cell in cells:
            m = DATE_PATTERN.search(cell)
            if m:
                candidate = _parse_date(m.group(1))
                if candidate is not None:
                    current_date = candidate
                    break

        if current_date is None:
            return None, current_date

        raw_times = []
        for cell in cells:
            raw_times.extend(t.replace('.', ':') for t in TIME_PATTERN.findall(cell))

        entry, exit_ = self._pick_entry_exit(raw_times)
        if entry is None:
            return None, current_date

        return self._build_row(current_date, entry, exit_, location), current_date

    def _parse_summary(self) -> dict:
        summary = {}
        m = re.search(r'סה"כ\s+ימי\s+עבודה[:\s]+(\d+)', self.text)
        if m:
            summary['total_days'] = m.group(1)
        m = re.search(r'סה"כ\s+שעות\s+חודשיות[:\s]+([\d.]+)', self.text)
        if m:
            summary['total_hours'] = m.group(1)
        return summary
