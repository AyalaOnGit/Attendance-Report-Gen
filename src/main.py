import os
from ocr_engine import get_pdf_text, identify_report_type
# הוספנו כאן ייבוא של extract_employee_name
from logic import parse_to_df, apply_variation, extract_employee_name 
from exporters import export_results

def main():
    input_folder = 'data/inputs'
    
    if not os.path.exists(input_folder):
        print(f"Error: Folder {input_folder} not found!")
        return

    for file in os.listdir(input_folder):
        if file.endswith('.pdf'):
            file_path = os.path.join(input_folder, file)
            raw_text = get_pdf_text(file_path)
            
            print(f"--- Processing: {file} ---")
            
            rtype = identify_report_type(raw_text)
            
            # חילוץ שם העובד (מופיע בדרך כלל בראש הדף)
            emp_name = extract_employee_name(raw_text)
            
            # שלב 2: ניתוח הנתונים (עכשיו הוא יחלץ גם יום ומקום)
            df = parse_to_df(raw_text)
            
            if df.empty:
                print(f"No data found in {file}")
                continue
            
            modified_df = apply_variation(df)
            
            # שלב 3: ייצוא - מעבירים גם את שם העובד
            base_name = os.path.splitext(file)[0] + "_NEW"
            export_results(modified_df, base_name, rtype, emp_name)
            
            print(f"Successfully created outputs for {file} (Employee: {emp_name})")

if __name__ == "__main__":
    main()