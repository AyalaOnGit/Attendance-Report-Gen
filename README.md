# ReportGen - אוטומציה של דוחות נוכחות

כלי חכם מבוסס Python לעיבוד דוחות נוכחות סרוקים (PDF), שינוי נתונים ליצירת דוח "אמין" חדש וייצוא תוצאות מעוצבות ל-PDF ו-Excel.

## 🏗️ ארכיטקטורה

הפרויקט מבוסס על דפוסי תוכנה ממוסים:

- Template Method (Parser):
  - `BaseParser` מגדיר את השלד של ניתוח הטקסט.
  - `TypeAParser` ו-`TypeBParser` מממשים את `_parse_summary()`, `_parse_row()` ו-`_is_header_line()`.
- Strategy (Transformation):
  - `BaseTransformationStrategy` מגדיר את הממשק.
  - `TypeATransformationStrategy` ו-`TypeBTransformationStrategy` מממשים לוגיקה שונה לפי סוג הדוח.
- Decorator (Validation):
  - `ValidatingStrategyDecorator` עוטף את האסטרטגיה ובודק שהשורה המאומצת תקינה.
- Renderer:
  - `HtmlRenderer` ממיר את `AttendanceReport` ל-HTML באמצעות תבניות Jinja2.
  - `PdfRenderer` מייצר PDF באמצעות `wkhtmltopdf`.

## 🚀 יכולות
- OCR דו-לשוני עברית/אנגלית באמצעות `tesseract` ו-PyMuPDF.
- זיהוי פורמט דו"ח (Type A / Type B) באמצעות `classifier.py`.
- ניתוח טקסט ל-`AttendanceReport` עם שורות נוכחות מובנות.
- יישום שינויים לוגיים בשעות ושמירה על תקינות באמצעות דקורטור.
- ייצוא ל-PDF ו-Excel עם מבנה דוח שמרני.

## 📦 דרישות

התקן את התלויות:

```bash
pip install -r requirements.txt
```

## 🐳 Docker

### בנייה

```bash
docker build -t attendance-report .
```

### הרצה

ברירת המחדל של המכולה מעבדת את כל קבצי ה-PDF שבתיקייה `data/inputs/` ושומרת את התוצאות ב-`data/outputs/`.

```bash
docker run --rm \
  -v "$(pwd)/data/inputs:/app/data/inputs" \
  -v "$(pwd)/data/outputs:/app/data/outputs" \
  attendance-report
```

ב-PowerShell של Windows:

```powershell
docker run --rm `
  -v "${PWD}/data/inputs:/app/data/inputs" `
  -v "${PWD}/data/outputs:/app/data/outputs" `
  attendance-report
```

ניתן גם לעבד קובץ ספציפי:

```bash
docker run --rm \
  -v "$(pwd)/data/inputs:/app/data/inputs" \
  -v "$(pwd)/data/outputs:/app/data/outputs" \
  attendance-report /app/data/inputs/n_r_10_n.pdf -o /app/data/outputs
```

### הערות

- המכולה מתקינה את `tesseract-ocr`, `tesseract-ocr-heb`, `poppler-utils` ו-`wkhtmltopdf`.
- היישום משתמש ב-`/usr/bin/tesseract` ו-`/usr/bin/wkhtmltopdf` בתוך המכולה.

## 📂 מבנה התיקיות
- `src/`: קבצי המקור.
- `templates/`: תבניות HTML לייצוא.
- `data/inputs/`: קלטים מקומיים כאשר מריצים ללא ארגומנטים.
- `data/outputs/`: פלט ברירת מחדל.

## 💻 שימוש מקומי

ניתן להריץ גם מחוץ לדוקר:

```bash
python src/main.py data/inputs/sample.pdf -o data/outputs
```

## ⚖️ רישיון
MIT License
