import pandas as pd
import sqlite3

def run_etl():
    db_path = 'data/ecommerce.db'
    csv_path = 'data/data.csv'
    conn = sqlite3.connect(db_path)

    # --- 1. ODS 层：原始数据导入 ---
    print("Step 1: Loading Raw Data to ODS...")
    df = pd.read_csv(csv_path, encoding='ISO-8859-1')
    df.to_sql('ods_ecommerce', conn, if_exists='replace', index=False)

    # --- 2. DWD 层：数据清洗 ---
    print("Step 2: Transforming Data to DWD...")
    dwd_df = df[df['CustomerID'].notna() & (df['Quantity'] > 0) & (df['UnitPrice'] > 0)].copy()
    dwd_df['Description'] = dwd_df['Description'].str.strip().str.upper()
    dwd_df['InvoiceDate'] = pd.to_datetime(dwd_df['InvoiceDate']).dt.strftime('%Y-%m-%d')
    dwd_df['TotalLineItemAmount'] = dwd_df['Quantity'] * dwd_df['UnitPrice']
    dwd_df.to_sql('dwd_ecommerce', conn, if_exists='replace', index=False)

    conn.commit()
    conn.close()
    print("ETL Job Finished!")

if __name__ == "__main__":
    run_etl()