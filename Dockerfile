FROM python:3.12-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV PYTHONIOENCODING=utf-8
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV WKHTMLTOPDF_PATH=/usr/bin/wkhtmltopdf

# התקנת תלויות מערכת ועדכון תעודות אבטחה
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-heb \
        poppler-utils \
        wkhtmltopdf \
        fonts-dejavu-core \
        libxrender1 \
        libxext6 \
        libx11-6 \
        fontconfig \
        ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# הוספת התיקייה src לנתיב החיפוש
ENV PYTHONPATH=/app/src:/app/src/domain:/app/src/application:/app/src/infrastructure:/app/src/cli

COPY requirements.txt .

# פתרון לנטפרי: הגדרת המארחים כ-trusted-host כדי לעקוף את שגיאת ה-SSL בהתקנה
RUN pip install --no-cache-dir --upgrade pip \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    && pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    -r requirements.txt

COPY . .

ENTRYPOINT ["python", "src/cli/main.py"]