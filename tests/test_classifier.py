from application.classifier import identify_report_type


def test_classify_type_a():
    text = "נ.ע. הנשר כח אדם 125% 150% שבת הפסקה סה\"כ"
    assert identify_report_type(text) == 'TYPE_A'


def test_classify_type_b():
    text = "| 1/1/23 | שני | 8:00 | 11:00 |\n| 2/1/23 | שלישי | 8:00 | 11:00 |"
    assert identify_report_type(text) == 'TYPE_B'
