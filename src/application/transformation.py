import datetime
import random
from abc import ABC, abstractmethod
from typing import List
from domain.domain import AttendanceRow, AttendanceReport
from domain.exceptions import TransformationError
from domain.rules import TYPE_A_TRANSFORM, TYPE_B_TRANSFORM, TransformationRules
from application.observers import TransformationObserver


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
    d = row.date
    return d.year * 10000 + d.month * 100 + d.day


def _deterministic_offset(row: AttendanceRow, rules: TransformationRules) -> int:
    rng = random.Random(_row_seed(row))
    return rng.randint(0, rules.offset_modulus - 1) + 1


class BaseTransformationStrategy(ABC):
    @abstractmethod
    def transform_row(self, row: AttendanceRow) -> AttendanceRow: ...


class TypeATransformationStrategy(BaseTransformationStrategy):
    """Type A: shifts entry/exit, populates h100 only."""

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


class TypeBTransformationStrategy(BaseTransformationStrategy):
    """Type B: shifts entry/exit, splits into h100 + h125 above 8 h."""

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
            h100, h125 = total, None
        return AttendanceRow(
            date=row.date, day=row.day, location=row.location,
            entry=new_entry, exit=new_exit,
            break_minutes=rules.break_minutes,
            total=total, h100=h100, h125=h125,
            h150=None, shabbat=None,
        )


class ValidatingStrategyDecorator(BaseTransformationStrategy):
    """Wraps any strategy, validates output, raises TransformationError on failure."""

    def __init__(self, strategy: BaseTransformationStrategy):
        self._strategy = strategy

    def transform_row(self, row: AttendanceRow) -> AttendanceRow:
        transformed = self._strategy.transform_row(row)
        self._validate(transformed)
        return transformed

    @staticmethod
    def _validate(row: AttendanceRow) -> None:
        if row.exit <= row.entry:
            raise TransformationError(f"exit {row.exit} <= entry {row.entry}")
        if row.total is not None and not (0 < row.total <= 24):
            raise TransformationError(f"total hours out of range: {row.total}")
        if not (0 <= row.break_minutes <= 360):
            raise TransformationError(f"break_minutes out of range: {row.break_minutes}")


class TransformationService:
    """
    Registry-based dispatch — no if/else on report type.
    Notifies registered observers on each row transformation or fallback.
    """

    def __init__(
        self,
        strategy_registry: dict[str, BaseTransformationStrategy],
        observers: List[TransformationObserver] | None = None,
    ):
        self._registry = strategy_registry
        self._observers: List[TransformationObserver] = observers or []

    def transform_report(self, report_type: str, report: AttendanceReport) -> AttendanceReport:
        strategy = self._registry.get(report_type)
        if strategy is None:
            raise TransformationError(f"No strategy for report type: {report_type}")

        transformed = [self._safe_transform(strategy, row) for row in report.rows]
        return AttendanceReport(
            rows=tuple(transformed),
            report_type=report.report_type,
            employee_name=report.employee_name,
            summary=report.summary,
        )

    def _safe_transform(
        self, strategy: BaseTransformationStrategy, row: AttendanceRow
    ) -> AttendanceRow:
        try:
            result = strategy.transform_row(row)
            for obs in self._observers:
                obs.on_row_transformed(row, result)
            return result
        except TransformationError as exc:
            for obs in self._observers:
                obs.on_row_fallback(row, exc)
            return row
