import datetime
from domain.domain import AttendanceRow


def test_attendance_row_creation():
    row = AttendanceRow(
        date=datetime.date(2023, 1, 1),
        day='ראשון',
        location='גונן',
        entry=datetime.time(8, 0),
        exit=datetime.time(16, 0),
    )
    assert row.entry == datetime.time(8, 0)
    assert row.exit == datetime.time(16, 0)
