import os
from dataclasses import asdict
import pandas as pd
import pdfkit
from jinja2 import Environment, FileSystemLoader
from domain import AttendanceReport

# הגדרות נתיב עבור wkhtmltopdf בסביבת Docker
WKHTMLTOPDF_PATH = os.environ.get('WKHTMLTOPDF_PATH', '/usr/bin/wkhtmltopdf')
PDFKIT_CONFIG = None
if os.path.exists(WKHTMLTOPDF_PATH):
    PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

class HtmlRenderer:
    def __init__(self, templates_dir='templates'):
        self.env = Environment(loader=FileSystemLoader(templates_dir))

    def render(self, report: AttendanceReport) -> str:
        # בחירת תבנית לפי סוג הדו"ח
        template_name = 'format_a.html' if report.report_type == 'TYPE_A' else 'format_b.html'
        template = self.env.get_template(template_name)
        
        rows = []
        for row in report.rows:
            row_dict = asdict(row)
            
            # --- תיקון לוגי: הבטחה שהטבלה תתמלא גם אם ה-OCR היה חלקי ---
            # אם שדה ה-total ריק או אפס, אנחנו שמים ערך בולט כדי שהשורה תוצג
            if not row_dict.get('total') or str(row_dict['total']) == "0.0":
                row_dict['total'] = "0.00 (נדרש אימות)"
            
            # התאמת שמות שדות עבור התבנית (Jinja2)
            row_dict['break'] = row_dict.pop('break_minutes', '00:30')
            rows.append(row_dict)

        total_hours = self._calculate_total_hours(rows)
        
        return template.render(
            rows=rows,
            employee_name=report.employee_name or 'לא זוהה',
            total_days=len(rows),
            total_hours=total_hours,
            report_type=report.report_type,
        )

    @staticmethod
    def _calculate_total_hours(rows):
        total = 0.0
        for row in rows:
            try:
                # ניקוי הטקסט "נדרש אימות" אם קיים לצורך החישוב
                val = str(row.get('total', '0')).split(' ')[0]
                total += float(val)
            except (ValueError, TypeError, Exception):
                continue
        return f"{total:.2f}"

class PdfRenderer:
    def __init__(self, config=PDFKIT_CONFIG):
        self.config = config

    def render_to_file(self, html: str, output_path: str):
        options = {
            'encoding': 'UTF-8',
            'enable-local-file-access': None,
            'margin-top': '10mm',
            'margin-bottom': '10mm',
            'margin-left': '10mm',
            'margin-right': '10mm',
            'quiet': ''
        }
        try:
            pdfkit.from_string(html, output_path, configuration=self.config, options=options)
        except Exception as e:
            print(f"❌ Error generating PDF: {e}")

def export_results(report: AttendanceReport, base_name: str, output_dir: str = 'data/outputs'):
    os.makedirs(output_dir, exist_ok=True)

    # 1. יצירת HTML וייצוא ל-PDF
    renderer = HtmlRenderer()
    html_out = renderer.render(report)
    pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
    PdfRenderer().render_to_file(html_out, pdf_path)

    # 2. ייצוא לאקסל (Excel)
    rows_for_excel = []
    for row in report.rows:
        row_dict = asdict(row)
        # וידוא שקיימת עמודת הפסקה
        row_dict['break'] = row_dict.get('break_minutes') or '00:30'
        rows_for_excel.append(row_dict)

    if rows_for_excel:
        df = pd.DataFrame(rows_for_excel)
        excel_path = os.path.join(output_dir, f"{base_name}.xlsx")
        df.to_excel(excel_path, index=False)
    
    print(f"✅ Created outputs for: {base_name} (Employee: {report.employee_name or 'לא זוהה'})")