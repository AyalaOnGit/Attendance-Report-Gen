from domain import AttendanceRow

def test_attendance_row_creation():
    row = AttendanceRow(date="10/10/2025", day="שישי", location="בית", entry="09:00", exit="12:00")
    assert row.total is None # ברירת המחדל ב-Dataclass[cite: 13]