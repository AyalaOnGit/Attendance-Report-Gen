import datetime
import pytest
from application.transformation import (
    TransformationService, TypeATransformationStrategy,
    TypeBTransformationStrategy, ValidatingStrategyDecorator,
)
from application.observers import ValidationObserver
from domain.domain import AttendanceReport, AttendanceRow
from domain.exceptions import TransformationError


def _make_row(entry='08:00', exit_='16:00', date='2023-02-02'):
    d = datetime.date.fromisoformat(date)
    return AttendanceRow(
        date=d, day='חמישי', location='גונן',
        entry=datetime.time.fromisoformat(entry),
        exit=datetime.time.fromisoformat(exit_),
    )


def test_transform_returns_new_object():
    row = _make_row()
    assert TypeATransformationStrategy().transform_row(row) is not row


def test_transform_preserves_immutability():
    row = _make_row()
    TypeATransformationStrategy().transform_row(row)
    assert row.entry == datetime.time(8, 0)


def test_exit_always_after_entry():
    for strategy in [TypeATransformationStrategy(), TypeBTransformationStrategy()]:
        result = strategy.transform_row(_make_row())
        assert result.exit > result.entry


def test_deterministic_same_seed():
    row = _make_row()
    r1 = TypeATransformationStrategy().transform_row(row)
    r2 = TypeATransformationStrategy().transform_row(row)
    assert r1.entry == r2.entry and r1.exit == r2.exit


def test_type_b_h125_for_long_shift():
    result = TypeBTransformationStrategy().transform_row(_make_row(entry='07:00', exit_='17:00'))
    assert result.h125 is not None and result.h125 > 0


def test_type_b_no_h125_for_short_shift():
    assert TypeBTransformationStrategy().transform_row(_make_row(entry='08:00', exit_='14:00')).h125 is None


def test_h100_plus_h125_equals_total():
    result = TypeBTransformationStrategy().transform_row(_make_row(entry='07:00', exit_='17:00'))
    if result.h125 is not None:
        assert abs((result.h100 or 0) + result.h125 - (result.total or 0)) < 0.01


def test_domain_rejects_exit_before_entry():
    with pytest.raises(ValueError, match="exit"):
        AttendanceRow(
            date=datetime.date(2023, 2, 2), day='חמישי', location='גונן',
            entry=datetime.time(16, 0), exit=datetime.time(8, 0),
        )


def test_validator_raises_on_bad_row():
    row = _make_row()

    class ReturnsInvalidTime(TypeATransformationStrategy):
        def transform_row(self, r: AttendanceRow) -> AttendanceRow:
            bad = TypeATransformationStrategy.transform_row(self, r)
            object.__setattr__(bad, 'exit', bad.entry)
            return bad

    with pytest.raises(TransformationError):
        ValidatingStrategyDecorator(ReturnsInvalidTime()).transform_row(row)


def test_service_falls_back_on_error():
    row = _make_row()
    report = AttendanceReport(rows=(row,), report_type='TYPE_A')

    class AlwaysFails(TypeATransformationStrategy):
        def transform_row(self, r):
            raise TransformationError("forced")

    service = TransformationService({'TYPE_A': AlwaysFails()})
    assert service.transform_report('TYPE_A', report).rows[0] is row


def test_observer_counts_successes_and_failures():
    obs = ValidationObserver()
    row = _make_row()
    report = AttendanceReport(rows=(row,), report_type='TYPE_A')

    class AlwaysFails(TypeATransformationStrategy):
        def transform_row(self, r):
            raise TransformationError("forced")

    good_service = TransformationService(
        {'TYPE_A': ValidatingStrategyDecorator(TypeATransformationStrategy())},
        observers=[obs],
    )
    good_service.transform_report('TYPE_A', report)
    assert obs.successes == 1

    bad_service = TransformationService({'TYPE_A': AlwaysFails()}, observers=[obs])
    bad_service.transform_report('TYPE_A', report)
    assert obs.failures == 1


def test_service_registry_no_if_else():
    row = _make_row()
    report = AttendanceReport(rows=(row,), report_type='TYPE_A')
    service = TransformationService({
        'TYPE_A': ValidatingStrategyDecorator(TypeATransformationStrategy()),
        'TYPE_B': ValidatingStrategyDecorator(TypeBTransformationStrategy()),
    })
    assert service.transform_report('TYPE_A', report).rows[0].entry != row.entry
