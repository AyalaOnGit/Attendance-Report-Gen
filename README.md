# ReportGen — אוטומציה של דוחות נוכחות

כלי Python לעיבוד דוחות נוכחות סרוקים (PDF): קריאת OCR, זיהוי פורמט, שינוי שעות דטרמיניסטי וייצוא ל-PDF ו-Excel.

---

## 🏗️ ארכיטקטורה

### זרימת נתונים

```
PDF (pixels)
    │
    ▼  infrastructure/ocr_engine.py — Tesseract → raw text + layout
    │
    ▼  application/classifier.py — keyword scoring → "TYPE_A" / "TYPE_B"
    │
    ▼  application/parser_factory.py — maps type → concrete parser
    │
    ▼  application/parsers.py — builds domain objects
         AttendanceReport(rows=(AttendanceRow, ...))
    │
    ▼  application/transformation.py — shifts times → new AttendanceReport
    │
    ▼  infrastructure/exporters.py — serializes to PDF + Excel
```

`cli/main.py` הוא ה-orchestrator היחיד. הוא מקבל את כל התלויות מ-`container.py` ולא יודע על אף class קונקרטי.

### שכבות (Layered Architecture)

```
domain/          ← לא מייבא כלום מבחוץ
application/     ← מייבא רק מ-domain
infrastructure/  ← מייבא מ-domain ו-application
cli/             ← מייבא רק Container
container.py     ← Composition Root — כל ה-wiring במקום אחד
```

---

### דפוסי עיצוב

**Template Method** — `application/parsers.py`
`BaseParser.parse()` מגדיר את שלד האלגוריתם:
`_clean_line` → `_is_header_line` → `_parse_row` → `_parse_summary`.
`TypeAParser` ו-`TypeBParser` עוקפים רק את ארבע השיטות האלה.

**Strategy** — `application/transformation.py`
`TransformationService` מחזיק registry של `{type: strategy}` ומפעיל `strategy.transform_row()` ללא `if/else`.
`TypeATransformationStrategy` — מחשב `h100` בלבד.
`TypeBTransformationStrategy` — מחשב `h100` + `h125` לשעות מעל 8 ביום.

**Decorator** — `application/transformation.py`
`ValidatingStrategyDecorator` עוטף כל strategy, מפעיל אותה, ואז מוודא `exit > entry`, total בטווח, break תקין. כישלון → `TransformationError` → fallback לשורה המקורית.

**Factory Method** — `application/parser_factory.py`
`create_parser(report_type, text, layout)` מחזיר את ה-parser הנכון. `main.py` לא יודע על הסוגים הקונקרטיים.

**Observer** — `application/observers.py`
`TransformationService` מקבל רשימת `TransformationObserver` ב-constructor ומודיע להם על כל transformation ו-fallback — ללא coupling.
`LoggingObserver` — מתעד כל שינוי.
`ValidationObserver` — סופר הצלחות וכישלונות (שימושי לטסטים).

**Dependency Injection / Composition Root** — `container.py`
`Container` מגדיר את `_PARSER_REGISTRY` ו-`_STRATEGY_REGISTRY` ובונה את כל ה-instances. `cli/main.py` קורא רק `build_container()`. הוספת TYPE_C = שתי שורות ב-`container.py` בלבד, ללא שינוי בשום קובץ אחר.

---

### Domain Model — `domain/domain.py`

```python
@dataclass(frozen=True)
class AttendanceRow:
    date: datetime.date
    entry: datetime.time   # typed — not a string
    exit: datetime.time    # typed — not a string
    ...

    def __post_init__(self):
        if self.exit <= self.entry:
            raise ValueError(...)  # model enforces its own invariants
```

- `frozen=True` — אי-אפשר לשנות שורה אחרי יצירתה; transformation מחזיר אובייקט חדש.
- `datetime.time` — זמנים מומרים מ-string **פעם אחת** בפרסר. serialization חזרה ל-string קורה רק ב-`exporters.py`.
- `__post_init__` — ה-model מגן על עצמו; לא ניתן לבנות שורה לא תקינה.

---

### Exception Hierarchy — `domain/exceptions.py`

```
ReportGenError
├── ParseError
├── TransformationError
└── OutputError
```

---

### קבועים — `domain/rules.py`

כל "magic numbers" מרוכזים ב-frozen dataclasses:

```python
PARSER_RULES      # min_entry, max_entry, min_exit, max_exit, shift bounds, break
TYPE_A_TRANSFORM  # offset_modulus, standard_day_hours, break_minutes
TYPE_B_TRANSFORM  # same fields
```

---

## 📂 מבנה התיקיות

```
ReportGen/
├── src/
│   ├── container.py           # Composition Root — שני registries + כל ה-wiring. הוספת TYPE_C = שתי שורות כאן בלבד
│   ├── domain/
│   │   ├── domain.py          # frozen dataclasses: AttendanceRow, AttendanceReport
│   │   ├── rules.py           # all business-rule constants (frozen dataclasses)
│   │   └── exceptions.py      # ReportGenError hierarchy
│   ├── application/
│   │   ├── parsers.py         # BaseParser (Template Method), TypeAParser, TypeBParser
│   │   ├── parser_factory.py  # factory: type token → parser instance
│   │   ├── classifier.py      # keyword scoring → TYPE_A / TYPE_B
│   │   ├── transformation.py  # strategies, decorator, service
│   │   ├── observers.py       # TransformationObserver, LoggingObserver, ValidationObserver
│   │   └── logic.py           # get_day_of_week, extract_employee_name
│   ├── infrastructure/
│   │   ├── ocr_engine.py      # PDF → raw text via Tesseract + PyMuPDF
│   │   └── exporters.py       # HtmlRenderer, PdfRenderer, export_results()
│   └── cli/
│       └── main.py            # CLI entry point — orchestrator
├── templates/
│   ├── format_a.html          # Jinja2 template for Type A reports
│   └── format_b.html          # Jinja2 template for Type B reports
├── tests/
│   ├── test_domain.py
│   ├── test_classifier.py
│   ├── test_parsers.py
│   └── test_transformation_service.py
├── data/
│   ├── inputs/                # place input PDFs here
│   └── outputs/               # generated PDF + Excel files land here
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

---

## 🐳 הרצה עם Docker (מומלץ)

### בנייה

```bash
docker build -t attendance-report .
```

### עיבוד כל הקבצים בתיקייה

```bash
# Linux / macOS
docker run --rm \
  -v "$(pwd)/data/inputs:/app/data/inputs" \
  -v "$(pwd)/data/outputs:/app/data/outputs" \
  attendance-report
```

```powershell
# Windows PowerShell
docker run --rm `
  -v "${PWD}/data/inputs:/app/data/inputs" `
  -v "${PWD}/data/outputs:/app/data/outputs" `
  attendance-report
```

### עיבוד קובץ ספציפי

```bash
docker run --rm \
  -v "$(pwd)/data/inputs:/app/data/inputs" \
  -v "$(pwd)/data/outputs:/app/data/outputs" \
  attendance-report /app/data/inputs/my_report.pdf -o /app/data/outputs
```

---

## 💻 הרצה מקומית

דורש Tesseract ו-wkhtmltopdf מותקנים על המכונה.

```bash
pip install -r requirements.txt
python src/cli/main.py data/inputs/my_report.pdf -o data/outputs
```

### הרצת טסטים

```bash
python -m pytest tests/ -v
```

---

## 🔧 משתני סביבה

| משתנה | ברירת מחדל | תיאור |
|---|---|---|
| `TESSERACT_CMD` | `/usr/bin/tesseract` | נתיב ל-Tesseract |
| `WKHTMLTOPDF_PATH` | `/usr/bin/wkhtmltopdf` | נתיב ל-wkhtmltopdf |

---

## ⚖️ רישיון
MIT License
