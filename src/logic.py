import re
import pandas as pd
import random
from datetime import datetime, timedelta

def extract_employee_name(text):
    """מחלץ את שם העובד מהטקסט"""
    lines = text.split('\n')
    for line in lines:
        if any(k in line for k in ["העובד", "שם", "לכבוד"]):
            # משאיר רק עברית ורווחים ומנקה מילות מפתח
            name = re.sub(r'[^\u0590-\u05fe\s]', '', line)
            name = name.replace("העובד", "").replace("שם", "").replace("לכבוד", "").strip()
            if len(name) > 2: return name
    return ""

def get_day_of_week(date_str):
    """מחשב יום בשבוע לפי תאריך"""
    try:
        date_obj = pd.to_datetime(date_str, dayfirst=True)
        days = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
        return days[date_obj.weekday()]
    except:
        return ""

def parse_to_df(text):
    lines = text.split('\n')
    data = []
    
    # איתור מקום דומיננטי בדף (כמו גליליון/גונן)
    main_location = ""
    if "גליליון" in text: main_location = "גליליון"
    elif "גונן" in text: main_location = "גונן"

    for line in lines:
        # איתור תאריך
        date_match = re.search(r'(\d{1,2}[/|1.]\d{1,2}[/|1.]\d{2,4})', line)
        if date_match:
            raw_date = date_match.group(0).replace('|', '/').replace('.', '/')
            times = re.findall(r'(\d{1,2}[:.]\d{2})', line)
            
            # ניקוי השורה מחילוץ המקום
            clean_loc = re.sub(r'[^א-ת\s]', '', line.replace(date_match.group(0), ""))
            for t in times:
                clean_loc = clean_loc.replace(t, "")
            
            # הסרת ימים ומילים מיותרות
            for d in ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "יום"]:
                clean_loc = clean_loc.replace(d, "")
            
            location = clean_loc.strip()
            
            # אם לא נמצא מקום בשורה, נשתמש במקום הדומיננטי או נשאיר ריק
            if len(location) < 2:
                location = main_location

            data.append({
                'date': raw_date,
                'day': get_day_of_week(raw_date),
                'location': location,
                'entry': times[0].replace('.', ':') if len(times) >= 1 else "08:00",
                'exit': times[1].replace('.', ':') if len(times) >= 2 else "16:30",
                'break': '00:30',
                'total': '8.5', 
                'h100': '8.5',
                'h125': '0.00',
                'h150': '0.00'
            })
            
    return pd.DataFrame(data)

def apply_variation(df):
    """מבצע שינויים קלים בזמנים כדי שהדו"ח לא ייראה רובוטי"""
    if df.empty: return df
    new_df = df.copy()
    for i, row in new_df.iterrows():
        try:
            # הוספת 2-12 דקות אקראיות
            offset = random.randint(2, 12)
            t1 = datetime.strptime(row['entry'], "%H:%M") + timedelta(minutes=offset)
            t2 = datetime.strptime(row['exit'], "%H:%M") + timedelta(minutes=offset)
            new_df.at[i, 'entry'] = t1.strftime("%H:%M")
            new_df.at[i, 'exit'] = t2.strftime("%H:%M")
        except: continue
    return new_df