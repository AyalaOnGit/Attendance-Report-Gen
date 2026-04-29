import re
import pandas as pd

def get_day_of_week(date_str):
    try:
        clean_date = date_str.replace('|', '/').replace('.', '/')
        date_obj = pd.to_datetime(clean_date, dayfirst=True)
        days = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
        return days[date_obj.weekday()]
    except: return ""

def extract_employee_name(text: str) -> str:
    """
    מחלץ את שם העובד בצורה מדויקת יותר.
    """
    # חיפוש תבנית של שם עובד
    import re
    
    # מחפש "שם העובד:" ואז לוקח את הטקסט עד לסוף השורה או עד מילת מפתח של כותרת
    pattern = r"שם העובד\s*[:\-\s]\s*([^\n\r,;|]+)"
    match = re.search(pattern, text)
    
    if match:
        name = match.group(1).strip()
        
        # ניקוי "זנבות" של כותרות עמודות אם נדבקו לשם
        stop_words = ["סהכימי", "סה\"כ", "חודש", "תאריך", "מספר", "שעת"]
        for word in stop_words:
            if word in name:
                name = name.split(word)[0].strip()
        
        return name if name else "לא זוהה"
    
    return "לא זוהה"

