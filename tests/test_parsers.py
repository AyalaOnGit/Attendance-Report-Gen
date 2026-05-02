import datetime
import pytest
from parsers import TypeAParser, TypeBParser, BaseParser
from domain import AttendanceReport, AttendanceRow


def test_base_parser_is_abstract():
    parser = BaseParser("text")
    with pytest.raises(NotImplementedError):
        parser._is_header_line("line")
    with pytest.raises(NotImplementedError):
        parser._parse_row("line", None, "loc")
    with pytest.raises(NotImplementedError):
        parser._parse_summary()


def test_type_a_returns_typed_values():
    report = TypeAParser("02/02/2023 08:00 16:00").parse()
    row = report.rows[0]
    assert isinstance(row.date, datetime.date)
    assert isinstance(row.entry, datetime.time)
    assert isinstance(row.exit, datetime.time)


def test_type_a_exit_after_entry():
    report = TypeAParser("02/02/2023 08:00 16:00").parse()
    for row in report.rows:
        assert row.exit > row.entry


def test_type_a_propagates_date():
    report = TypeAParser("02/02/2023 08:00 16:00\n08:30 15:30").parse()
    assert len(report.rows) == 2
    assert report.rows[1].date == datetime.date(2023, 2, 2)


def test_type_a_deduplicates():
    report = TypeAParser("02/02/2023 08:00 16:00\n02/02/2023 08:00 16:00").parse()
    assert len(report.rows) == 1


def test_type_a_skips_header():
    report = TypeAParser("תאריך כניסה יציאה הפסקה\n02/02/2023 08:00 16:00").parse()
    assert len(report.rows) == 1


def test_type_a_filters_invalid_times():
    report = TypeAParser("02/02/2023 00:01 01:00").parse()
    assert len(report.rows) == 0


def test_type_a_report_is_immutable():
    report = TypeAParser("02/02/2023 08:00 16:00").parse()
    with pytest.raises(Exception):
        report.rows[0].entry = datetime.time(9, 0)  # type: ignore


def test_type_b_returns_typed_values():
    report = TypeBParser("| 02/02/2023 | שני | 08:00 | 16:00 |").parse()
    row = report.rows[0]
    assert isinstance(row.date, datetime.date)
    assert isinstance(row.entry, datetime.time)
    assert isinstance(row.exit, datetime.time)


def test_type_b_exit_after_entry():
    report = TypeBParser("| 02/02/2023 | שני | 08:00 | 16:00 |").parse()
    for row in report.rows:
        assert row.exit > row.entry


def test_type_b_skips_header():
    text = "| תאריך | יום | כניסה | יציאה |\n| 02/02/2023 | שני | 08:00 | 16:00 |"
    report = TypeBParser(text).parse()
    assert len(report.rows) == 1
