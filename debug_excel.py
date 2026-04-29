import pandas as pd
for f in ['a_r_25_NEW.xlsx','a_r_9_NEW.xlsx','n_r_10_n_NEW.xlsx','n_r_5_n_NEW.xlsx']:
    print(f'\n=== {f} ===')
    try:
        df = pd.read_excel(f'data/outputs/{f}')
        print(f'rows: {len(df)}')
        print(df[['date','day','location','entry','exit','total']].to_string())
    except Exception as e:
        print(f'Error: {e}')
