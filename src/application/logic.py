import datetime
import re


def get_day_of_week(date: datetime.date) -> str:
    days = ['שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון']
    return days[date.weekday()]


def extract_employee_name(text: str) -> str:
    pattern = r'שם העובד\s*[:\-\s]\s*([^\n\r,;|]+)'
    match = re.search(pattern, text)
    if match:
        name = match.group(1).strip()
        for word in ['סהכימי', 'סה"כ', 'חודש', 'תאריך', 'מספר', 'שעת']:
            if word in name:
                name = name.split(word)[0].strip()
        return name if name else 'לא זוהה'
    return 'לא זוהה'
