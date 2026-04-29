import pytest
from parsers import TypeAParser, TypeBParser, BaseParser
from domain import AttendanceReport


def test_base_parser_is_abstract():
    """BaseParser._parse_row, _is_header_line, _parse_summary must be overridden."""
    parser = BaseParser("some text")
    with pytest.raises(NotImplementedError):
        parser._is_header_line("line")
    with pytest.raises(NotImplementedError):
        parser._parse_row("line", "", "loc")
    with pytest.raises(NotImplementedError):
        parser._parse_summary()


def test_type_a_parser_extracts_row():
    raw_text = "02/02/2023 08:00 16:00"
    parser = TypeAParser(raw_text)
    report = parser.parse()

    assert isinstance(report, AttendanceReport)
    assert len(report.rows) == 1
    assert report.rows[0].entry == "08:00"
    assert report.rows[0].exit == "16:00"
    assert report.rows[0].date == "02/02/2023"


def test_type_a_parser_propagates_date():
    """תאריך מהשורה הראשונה מופץ לשורה הבאה שאין לה תאריך."""
    raw_text = "02/02/2023 08:00 16:00\n08:30 15:30"
    parser = TypeAParser(raw_text)
    report = parser.parse()
    assert len(report.rows) == 2
    assert report.rows[1].date == "02/02/2023"


def test_type_a_parser_deduplicates():
    raw_text = "02/02/2023 08:00 16:00\n02/02/2023 08:00 16:00"
    parser = TypeAParser(raw_text)
    report = parser.parse()
    assert len(report.rows) == 1


def test_type_a_parser_skips_header():
    raw_text = "תאריך כניסה יציאה הפסקה\n02/02/2023 08:00 16:00"
    parser = TypeAParser(raw_text)
    report = parser.parse()
    assert len(report.rows) == 1


def test_type_a_parser_filters_invalid_times():
    raw_text = "02/02/2023 00:01 01:00"
    parser = TypeAParser(raw_text)
    report = parser.parse()
    assert len(report.rows) == 0


def test_type_b_parser_extracts_row():
    raw_text = "| 02/02/2023 | שני | 08:00 | 16:00 |"
    parser = TypeBParser(raw_text)
    report = parser.parse()
    assert isinstance(report, AttendanceReport)
    assert len(report.rows) == 1
    assert report.rows[0].date == "02/02/2023"


def test_type_b_parser_propagates_date():
    raw_text = "| 02/02/2023 | שני | 08:00 | 16:00 |\n| | שלישי | 08:00 | 16:00 |"
    parser = TypeBParser(raw_text)
    report = parser.parse()
    assert len(report.rows) == 1  # שורה שנייה כפולה (אותה כניסה) — מסוננת


def test_type_b_parser_skips_header():
    raw_text = "| תאריך | יום | כניסה | יציאה |\n| 02/02/2023 | שני | 08:00 | 16:00 |"
    parser = TypeBParser(raw_text)
    report = parser.parse()
    assert len(report.rows) == 1
