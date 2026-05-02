import os
import datetime
import pandas as pd
import pdfkit
from jinja2 import Environment, FileSystemLoader
from domain import AttendanceReport, AttendanceRow

WKHTMLTOPDF_PATH = os.environ.get('WKHTMLTOPDF_PATH', '/usr/bin/wkhtmltopdf')
PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH) if os.path.exists(WKHTMLTOPDF_PATH) else None


def _fmt_time(t: datetime.time) -> str:
    return t.strftime('%H:%M')


def _fmt_date(d: datetime.date) -> str:
    return d.strftime('%d/%m/%Y')


def _row_to_display(row: AttendanceRow) -> dict:
    """Serialize a frozen AttendanceRow to strings for templates/Excel."""
    return {
        'date':          _fmt_date(row.date),
        'day':           row.day,
        'location':      row.location,
        'entry':         _fmt_time(row.entry),
        'exit':          _fmt_time(row.exit),
        'break':         f"{row.break_minutes // 60:02d}:{row.break_minutes % 60:02d}",
        'total':         f"{row.total:.2f}" if row.total is not None else '',
        'h100':          f"{row.h100:.2f}" if row.h100 is not None else '',
        'h125':          f"{row.h125:.2f}" if row.h125 is not None else '',
        'h150':          f"{row.h150:.2f}" if row.h150 is not None else '',
        'shabbat':       f"{row.shabbat:.2f}" if row.shabbat is not None else '',
    }


class HtmlRenderer:
    def __init__(self, templates_dir: str = 'templates'):
        self.env = Environment(loader=FileSystemLoader(templates_dir))

    def render(self, report: AttendanceReport) -> str:
        template_name = 'format_a.html' if report.report_type == 'TYPE_A' else 'format_b.html'
        rows = [_row_to_display(r) for r in report.rows]
        total_hours = sum(r.total or 0.0 for r in report.rows)
        return self.env.get_template(template_name).render(
            rows=rows,
            employee_name=report.employee_name or 'לא זוהה',
            total_days=len(rows),
            total_hours=f"{total_hours:.2f}",
            report_type=report.report_type,
        )


class PdfRenderer:
    _OPTIONS = {
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
        'margin-top': '10mm', 'margin-bottom': '10mm',
        'margin-left': '10mm', 'margin-right': '10mm',
        'quiet': '',
    }

    def __init__(self, config=PDFKIT_CONFIG):
        self.config = config

    def render_to_file(self, html: str, output_path: str) -> None:
        try:
            pdfkit.from_string(html, output_path, configuration=self.config, options=self._OPTIONS)
        except Exception as exc:
            print(f"❌ PDF generation failed: {exc}")


def export_results(report: AttendanceReport, base_name: str, output_dir: str = 'data/outputs') -> None:
    os.makedirs(output_dir, exist_ok=True)

    html = HtmlRenderer().render(report)
    PdfRenderer().render_to_file(html, os.path.join(output_dir, f"{base_name}.pdf"))

    rows = [_row_to_display(r) for r in report.rows]
    if rows:
        pd.DataFrame(rows).to_excel(os.path.join(output_dir, f"{base_name}.xlsx"), index=False)

    print(f"✅ Created outputs for: {base_name} (Employee: {report.employee_name or 'לא זוהה'})")
