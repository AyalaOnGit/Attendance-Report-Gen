import datetime
import random
from domain import AttendanceRow, AttendanceReport
from rules import TYPE_A_TRANSFORM, TYPE_B_TRANSFORM, TransformationRules


# ---------------------------------------------------------------------------
# Helpers — operate on datetime.time, never on strings
# ---------------------------------------------------------------------------

def _to_minutes(t: datetime.time) -> int:
    return t.hour * 60 + t.minute


def _from_minutes(total: int) -> datetime.time:
    total = total % (24 * 60)
    return datetime.time(total // 60, total % 60)


def _compute_total(entry: datetime.time, exit_: datetime.time, break_min: int) -> float:
    worked = _to_minutes(exit_) - _to_minutes(entry) - break_min
    if worked < 0:
        worked += 24 * 60
    return round(worked / 60, 2)


def _row_seed(row: AttendanceRow) -> int:
    """Deterministic seed derived from the row's date — no global RNG state."""
    d = row.date
    return d.year * 10000 + d.month * 100 + d.day


def _deterministic_offset(row: AttendanceRow, rules: TransformationRules) -> int:
    rng = random.Random(_row_seed(row))
    return (rng.randint(0, rules.offset_modulus - 1)) + 1


# ---------------------------------------------------------------------------
# Strategy base
# ---------------------------------------------------------------------------

class BaseTransformationStrategy:
    def transform_row(self, row: AttendanceRow) -> AttendanceRow:
        return row


# ---------------------------------------------------------------------------
# Type A — shifts entry/exit, fills h100 only (no OT columns in this format)
# ---------------------------------------------------------------------------

class TypeATransformationStrategy(BaseTransformationStrategy):
    """
    Type A report: columns 100%/125%/150%/shabbat.
    Shifts entry and exit by a per-row deterministic offset.
    Only h100 is populated; OT columns remain None.
    """

    def transform_row(self, row: AttendanceRow) -> AttendanceRow:
        rules = TYPE_A_TRANSFORM
        offset = _deterministic_offset(row, rules)

        new_entry = _from_minutes(min(_to_minutes(row.entry) + offset, 23 * 60))
        new_exit  = _from_minutes(min(_to_minutes(row.exit)  + offset, 24 * 60 - 1))
        if new_exit <= new_entry:
            new_exit = _from_minutes(_to_minutes(new_entry) + 60)

        total = _compute_total(new_entry, new_exit, rules.break_minutes)

        return AttendanceRow(
            date=row.date, day=row.day, location=row.location,
            entry=new_entry, exit=new_exit,
            break_minutes=rules.break_minutes,
            total=total, h100=total,
            h125=None, h150=None, shabbat=row.shabbat,
        )


# ---------------------------------------------------------------------------
# Type B — shifts entry/exit, splits worked hours into h100 + h125
# ---------------------------------------------------------------------------

class TypeBTransformationStrategy(BaseTransformationStrategy):
    """
    Type B report: regular hours only (no OT columns in source).
    Shifts entry and exit, then splits worked time into h100 (≤8 h) and h125 (>8 h).
    """

    def transform_row(self, row: AttendanceRow) -> AttendanceRow:
        rules = TYPE_B_TRANSFORM
        offset = _deterministic_offset(row, rules) + 1

        new_entry = _from_minutes(min(_to_minutes(row.entry) + offset, 23 * 60))
        new_exit  = _from_minutes(min(_to_minutes(row.exit)  + offset, 24 * 60 - 1))
        if new_exit <= new_entry:
            new_exit = _from_minutes(_to_minutes(new_entry) + 60)

        total      = _compute_total(new_entry, new_exit, rules.break_minutes)
        worked_min = _to_minutes(new_exit) - _to_minutes(new_entry) - rules.break_minutes
        standard   = int(rules.standard_day_hours * 60)

        if worked_min > standard:
            h100 = round(standard / 60, 2)
            h125 = round((worked_min - standard) / 60, 2)
        else:
            h100 = total
            h125 = None

        return AttendanceRow(
            date=row.date, day=row.day, location=row.location,
            entry=new_entry, exit=new_exit,
            break_minutes=rules.break_minutes,
            total=total, h100=h100, h125=h125,
            h150=None, shabbat=None,
        )


# ---------------------------------------------------------------------------
# Decorator — validates the transformed row, falls back on failure
# ---------------------------------------------------------------------------

class ValidatingStrategyDecorator(BaseTransformationStrategy):
    """
    Wraps any strategy and validates the result.
    Returns the original row when the transformed result is invalid.
    """

    def __init__(self, strategy: BaseTransformationStrategy):
        self._strategy = strategy

    def transform_row(self, row: AttendanceRow) -> AttendanceRow:
        transformed = self._strategy.transform_row(row)
        if not self._is_valid(transformed):
            return row
        return transformed

    @staticmethod
    def _is_valid(row: AttendanceRow) -> bool:
        if row.exit <= row.entry:
            return False
        if row.total is not None and not (0 < row.total <= 24):
            return False
        if not (0 <= row.break_minutes <= 360):
            return False
        return True


# ---------------------------------------------------------------------------
# Service — registry-based dispatch, no if/else on report type
# ---------------------------------------------------------------------------

class TransformationService:
    def __init__(self, strategy_registry: dict[str, BaseTransformationStrategy]):
        self._registry = strategy_registry

    def transform_report(self, report_type: str, report: AttendanceReport) -> AttendanceReport:
        strategy = self._registry.get(report_type)
        if strategy is None:
            return report

        transformed = [strategy.transform_row(row) for row in report.rows]
        return AttendanceReport(
            rows=tuple(transformed),
            report_type=report.report_type,
            employee_name=report.employee_name,
            summary=report.summary,
        )


def create_transformation_service() -> TransformationService:
    """Factory — main.py calls this without knowing the concrete strategy classes."""
    registry = {
        'TYPE_A': ValidatingStrategyDecorator(TypeATransformationStrategy()),
        'TYPE_B': ValidatingStrategyDecorator(TypeBTransformationStrategy()),
    }
    return TransformationService(registry)
