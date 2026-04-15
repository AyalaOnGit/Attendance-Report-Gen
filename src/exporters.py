import pdfkit
import os
import pandas as pd  # חובה לייבא כדי לחשב שעות
from jinja2 import Environment, FileSystemLoader

# נתיב למנוע ה-PDF
PATH_WKHTML = r'C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=PATH_WKHTML)

def export_results(df, base_name, report_type, employee_name="לא זוהה"):
    output_dir = 'data/outputs'
    os.makedirs(output_dir, exist_ok=True)
    
    # טעינת תיקיית ה-Templates
    env = Environment(loader=FileSystemLoader('templates'))
    
    # בחירת התבנית לפי סוג הדו"ח שזוהה ב-OCR
    if report_type == "FORMAT_WIDE_A":
        template = env.get_template('format_a.html')
    else:
        template = env.get_template('format_b.html')
    
    # הכנת הנתונים למילוי (הפיכת הטבלה לרשימת מילונים)
    rows = df.to_dict(orient='records')
    
    # חישוב שעות אמיתי מהטבלה
    try:
        total_val = pd.to_numeric(df['total'], errors='coerce').sum()
        total_hours = "{:.2f}".format(total_val)
    except:
        total_hours = "0.00"
    
    # הזרקת הנתונים לתוך ה-HTML (כולל שם העובד!)
    html_out = template.render(
        rows=rows, 
        report_type=report_type,
        employee_name=employee_name, 
        total_days=len(df),
        total_hours=total_hours
    )
    
    # הגדרות ייצוא ל-PDF
    pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
    options = {
        'encoding': "UTF-8",
        'enable-local-file-access': None,
        'margin-top': '10mm',
        'margin-bottom': '10mm',
        'margin-left': '10mm',
        'margin-right': '10mm',
        'quiet': ''
    }
    
    try:
        # יצירת ה-PDF מה-HTML המרונדר
        pdfkit.from_string(html_out, pdf_path, configuration=config, options=options)
        
        # שמירה לאקסל לגיבוי ובדיקה
        df.to_excel(os.path.join(output_dir, f"{base_name}.xlsx"), index=False)
        
        print(f"✅ Created outputs for: {base_name} (Employee: {employee_name})")
    except Exception as e:
        print(f"❌ Error creating PDF for {base_name}: {e}")