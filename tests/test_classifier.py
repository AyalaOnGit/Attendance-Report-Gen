from classifier import identify_report_type

def test_classify_type_a():
    text = "דוח ריכוז שעות נ.ע. הנשר בעמ 125% 150%"
    assert identify_report_type(text) == "TYPE_A"

def test_classify_type_b():
    text = "Attendance Report Total Hours Break"
    assert identify_report_type(text) == "TYPE_B"