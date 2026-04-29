from domain import AttendanceRow, AttendanceReport
from exceptions import TransformationError


def _time_to_minutes(time_text: str) -> int:
    if not time_text or ':' not in time_text.replace('.', ':'):
        return 480  # ברירת מחדל: 08:00 בבוקר (8*60)
    try:
        hours, minutes = [int(part) for part in time_text.replace('.', ':').split(':')]
        return hours * 60 + minutes
    except Exception:
        return 480

def _minutes_to_time(minutes: int) -> str:
    hours = minutes // 60
    minutes = minutes % 60
    hours = hours % 24
    return f"{hours:02d}:{minutes:02d}"


def _parse_break_minutes(break_text: str) -> int:
    try:
        hours, minutes = [int(part) for part in break_text.replace('.', ':').split(':')]
        return hours * 60 + minutes
    except Exception:
        return 30


def _compute_total(entry: str, exit: str, break_text: str) -> str:
    entry_min = _time_to_minutes(entry)
    exit_min = _time_to_minutes(exit)
    break_min = _parse_break_minutes(break_text or "00:30")
    worked = exit_min - entry_min - break_min
    if worked < 0:
        worked += 24 * 60
    return f"{worked / 60:.2f}"


def _deterministic_offset(row: AttendanceRow) -> int:
    if not row.date:
        return 5
    values = [int(ch) for ch in row.date if ch.isdigit()]
    return (sum(values) % 11) + 1


class BaseTransformationStrategy:
    def transform_row(self, row: AttendanceRow) -> AttendanceRow:
        raise NotImplementedError


class TypeATransformationStrategy(BaseTransformationStrategy):
    """
    Type A: דוח עם שעות 100%/125%/150%/שבת.
    מזיז כניסה ויציאה ב-offset דטרמיניסטי, ומחשב h100 בלבד (אין OT בפורמט זה).
    """

    def transform_row(self, row: AttendanceRow) -> AttendanceRow:
        offset = _deterministic_offset(row)
        entry_minutes = _time_to_minutes(row.entry)
        exit_minutes  = _time_to_minutes(row.exit)

        new_entry = min(entry_minutes + offset, 23 * 60)
        new_exit  = min(exit_minutes  + offset, 24 * 60)
        if new_exit <= new_entry:
            new_exit = new_entry + 60

        entry_text = _minutes_to_time(new_entry)
        exit_text  = _minutes_to_time(new_exit)
        total      = _compute_total(entry_text, exit_text, row.break_minutes or "00:30")

        return AttendanceRow(
            date=row.date, day=row.day, location=row.location,
            entry=entry_text, exit=exit_text,
            break_minutes=row.break_minutes,
            total=total, h100=total,
            h125=None, h150=None, shabbat=row.shabbat,
        )


class TypeBTransformationStrategy(BaseTransformationStrategy):
    """
    Type B: דוח עם שעות רגילות בלבד (ללא עמודות OT).
    מזיז כניסה ויציאה ב-offset דטרמיניסטי, ומחשב גם h125 לשעות מעל 8 ביום.
    """
    _STANDARD_DAY = 8 * 60  # 8 שעות = יום עבודה רגיל

    def transform_row(self, row: AttendanceRow) -> AttendanceRow:
        offset = _deterministic_offset(row) + 1
        entry_minutes = _time_to_minutes(row.entry)
        exit_minutes  = _time_to_minutes(row.exit)
        break_minutes = _parse_break_minutes(row.break_minutes or "00:30")

        new_entry = min(entry_minutes + offset, 23 * 60)
        new_exit  = min(exit_minutes  + offset, 24 * 60)
        if new_exit <= new_entry:
            new_exit = new_entry + 60

        entry_text = _minutes_to_time(new_entry)
        exit_text  = _minutes_to_time(new_exit)
        total      = _compute_total(entry_text, exit_text, row.break_minutes or "00:30")

        worked_min = new_exit - new_entry - break_minutes
        if worked_min > self._STANDARD_DAY:
            h100 = f"{self._STANDARD_DAY / 60:.2f}"
            h125 = f"{(worked_min - self._STANDARD_DAY) / 60:.2f}"
        else:
            h100 = total
            h125 = None

        return AttendanceRow(
            date=row.date, day=row.day, location=row.location,
            entry=entry_text, exit=exit_text,
            break_minutes=row.break_minutes,
            total=total, h100=h100, h125=h125,
            h150=None, shabbat=None,
        )


class ValidatingStrategyDecorator(BaseTransformationStrategy):
    def __init__(self, strategy: BaseTransformationStrategy):
        self._strategy = strategy

    def transform_row(self, row: AttendanceRow) -> AttendanceRow:
        transformed = self._strategy.transform_row(row)
        if not self._is_valid(transformed):
            raise TransformationError("Transformed row failed validation")
        return transformed

    def _is_valid(self, row: AttendanceRow) -> bool:
        try:
            entry = _time_to_minutes(row.entry)
            exit = _time_to_minutes(row.exit)
            if exit <= entry:
                return False
            total = float(row.total or "0")
            if total < 0 or total > 24:
                return False
            if row.break_minutes:
                break_minutes = _parse_break_minutes(row.break_minutes)
                if break_minutes < 0 or break_minutes > 360:
                    return False
            return True
        except TransformationError:
            return False
        except Exception:
            return False


class TransformationService:
    def __init__(self, strategy_registry: dict[str, BaseTransformationStrategy]):
        self._strategy_registry = strategy_registry

    def transform_report(self, report_type: str, report: AttendanceReport) -> AttendanceReport:
        strategy = self._strategy_registry.get(report_type)
        if strategy is None:
            raise TransformationError(f"No transformation strategy configured for {report_type}")

        transformed_rows = []
        for row in report.rows:
            try:
                transformed_rows.append(strategy.transform_row(row))
            except TransformationError:
                transformed_rows.append(row)

        return AttendanceReport(
            rows=transformed_rows,
            report_type=report.report_type,
            employee_name=report.employee_name,
            summary=report.summary,
        )
