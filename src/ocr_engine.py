import io
import os
import pytesseract
import fitz  # PyMuPDF
from PIL import Image, ImageFilter, ImageOps

# הגדרת נתיב לטסרקט
tesseract_path = os.environ.get('TESSERACT_CMD', '/usr/bin/tesseract')
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

def _enhance_image(img: Image.Image) -> Image.Image:
    img = img.convert('L')
    img = ImageOps.autocontrast(img, cutoff=3)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    return img.resize((img.width * 2, img.height * 2), Image.LANCZOS)

def _reconstruct_lines(data) -> str:
    """Reconstruct newline-separated text from OCR data using line_num grouping."""
    from collections import defaultdict
    lines: dict = defaultdict(list)
    for i, text in enumerate(data.get('text', [])):
        word = str(text or '').strip()
        if not word:
            continue
        try:
            conf = int(data.get('conf', [])[i])
        except Exception:
            conf = -1
        if conf < 15:
            continue
        block = data.get('block_num', [])[i]
        line = data.get('line_num', [])[i]
        top = int(data.get('top', [])[i] or 0)
        lines[(block, line, top)].append(word)
    return '\n'.join(' '.join(words) for _, words in sorted(lines.items()))


def _layout_from_ocr_data(data, page_number: int):
    layout = []
    for i, text in enumerate(data.get('text', [])):
        word = str(text or '').strip()
        if not word: continue
        try:
            conf = int(data.get('conf', [])[i])
        except: conf = -1
        if conf < 15: continue
        layout.append({
            'page': page_number, 'text': word,
            'left': int(data.get('left', [])[i] or 0),
            'top': int(data.get('top', [])[i] or 0),
            'width': int(data.get('width', [])[i] or 0),
            'height': int(data.get('height', [])[i] or 0),
            'conf': conf,
        })
    return layout

def get_pdf_text_and_layout(pdf_path: str):
    try:
        doc = fitz.open(pdf_path)
        pages_text, layout = [], []
        for page_number, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
            img = _enhance_image(Image.open(io.BytesIO(pix.tobytes('png'))))
            ocr_data = pytesseract.image_to_data(img, lang='heb+eng', config='--oem 1 --psm 6', output_type=pytesseract.Output.DICT)
            page_text = _reconstruct_lines(ocr_data)
            if page_text.strip():
                pages_text.append(page_text)
            layout.extend(_layout_from_ocr_data(ocr_data, page_number))
        doc.close()
        return '\n'.join(pages_text), layout
    except Exception as e:
        print(f'Error: {e}')
        return '', []