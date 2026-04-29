import pytest
from transformation import TransformationService, TypeATransformationStrategy
from domain import AttendanceReport, AttendanceRow

def test_service_applies_strategy():
    row = AttendanceRow(date="01/01/2025", day="רביעי", location="נ.ע. הנשר", entry="08:00", exit="16:00")
    report = AttendanceReport(rows=[row], report_type="TYPE_A")
    
    # יצירת ה-Service עם ה-Registry[cite: 11, 7]
    service = TransformationService({"TYPE_A": TypeATransformationStrategy()})
    transformed_report = service.transform_report("TYPE_A", report)
    
    # בדיקה שהשורה אכן השתנתה (ה-offset הופעל)[cite: 11, 14]
    assert transformed_report.rows[0].entry != "08:00"