import datetime
from transformation import (
    TransformationService, TypeATransformationStrategy,
    TypeBTransformationStrategy, ValidatingStrategyDecorator,
)
from domain import AttendanceReport, AttendanceRow


def _make_row(entry='08:00', exit_='16:00', date='2023-02-02'):
    d = datetime.date.fromisoformat(date)
    e = datetime.time.fromisoformat(entry)
    x = datetime.time.fromisoformat(exit_)
    return AttendanceRow(date=d, day='חמישי', location='גונן', entry=e, exit=x)


def test_transform_returns_new_object():
    row = _make_row()
    result = TypeATransformationStrategy().transform_row(row)
    assert result is not row


def test_transform_preserves_immutability():
    row = _make_row()
    TypeATransformationStrategy().transform_row(row)
    assert row.entry == datetime.time(8, 0)  # original unchanged


def test_exit_always_after_entry():
    for strategy in [TypeATransformationStrategy(), TypeBTransformationStrategy()]:
        result = strategy.transform_row(_make_row())
        assert result.exit > result.entry


def test_deterministic_same_seed():
    row = _make_row()
    r1 = TypeATransformationStrategy().transform_row(row)
    r2 = TypeATransformationStrategy().transform_row(row)
    assert r1.entry == r2.entry
    assert r1.exit == r2.exit


def test_type_b_h125_for_long_shift():
    row = _make_row(entry='07:00', exit_='17:00')
    result = TypeBTransformationStrategy().transform_row(row)
    assert result.h125 is not None
    assert result.h125 > 0


def test_type_b_no_h125_for_short_shift():
    row = _make_row(entry='08:00', exit_='14:00')
    result = TypeBTransformationStrategy().transform_row(row)
    assert result.h125 is None


def test_h100_plus_h125_equals_total():
    row = _make_row(entry='07:00', exit_='17:00')
    result = TypeBTransformationStrategy().transform_row(row)
    if result.h125 is not None:
        assert abs((result.h100 or 0) + result.h125 - (result.total or 0)) < 0.01


def test_validator_returns_original_on_bad_transform():
    """ValidatingStrategyDecorator returns the original row when strategy output is invalid."""
    row = _make_row()

    class ReturnsInvalidTime(TypeATransformationStrategy):
        """Returns a row where exit == entry, bypassing immutability via object.__setattr__."""
        def transform_row(self, r: AttendanceRow) -> AttendanceRow:
            bad = TypeATransformationStrategy.transform_row(self, r)
            object.__setattr__(bad, 'exit', bad.entry)
            return bad

    result = ValidatingStrategyDecorator(ReturnsInvalidTime()).transform_row(row)
    assert result is row


def test_service_falls_back_on_invalid_transform():
    row = _make_row()
    report = AttendanceReport(rows=(row,), report_type='TYPE_A')

    class ReturnsInvalidRow(TypeATransformationStrategy):
        def transform_row(self, r: AttendanceRow) -> AttendanceRow:
            bad = TypeATransformationStrategy.transform_row(self, r)
            object.__setattr__(bad, 'exit', bad.entry)
            return bad

    decorated = ValidatingStrategyDecorator(ReturnsInvalidRow())
    service = TransformationService({'TYPE_A': decorated})
    result = service.transform_report('TYPE_A', report)
    assert result.rows[0] is row  # original kept by decorator


def test_service_registry_no_if_else():
    row = _make_row()
    report = AttendanceReport(rows=(row,), report_type='TYPE_A')
    service = TransformationService({
        'TYPE_A': ValidatingStrategyDecorator(TypeATransformationStrategy()),
        'TYPE_B': ValidatingStrategyDecorator(TypeBTransformationStrategy()),
    })
    result = service.transform_report('TYPE_A', report)
    assert result.rows[0].entry != row.entry
