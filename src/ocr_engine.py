import pytesseract
import fitz  # PyMuPDF
from PIL import Image
import io

# נתיב ל-Tesseract - וודא שזה הנתיב אצלך!
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def get_pdf_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # הגדלה לשיפור הדיוק
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        # קריאת עברית ואנגלית ביחד
        text = pytesseract.image_to_string(img, lang='heb+eng')
        doc.close()
        return text
    except Exception as e:
        print(f"Error in OCR: {e}")
        return ""

def identify_report_type(text):
    # זיהוי לפי המבנה שראינו בתמונות
    if any(x in text for x in ["125%", "150%", "שבת"]):
        return "FORMAT_WIDE_A" # הדו"ח הרחב (הנשר וכדומה)
    return "FORMAT_SUMMARY_B" # הדו"ח עם הריבועים למעלה