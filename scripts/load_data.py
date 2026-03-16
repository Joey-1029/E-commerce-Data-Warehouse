import pandas as pd
import sqlite3
import os

def run_etl():
    db_path = 'data/ecommerce.db'
    csv_path = 'data/data.csv'
    conn = sqlite3.connect(db_path)
    
    # --- 1. ODS 层：原始数据导入 ---
    print("Step 1: Loading Raw Data to ODS...")
    df = pd.read_csv(csv_path, encoding='ISO-8859-1')
    df.to_sql('ods_ecommerce', conn, if_exists='replace', index=False)

    # --- 2. DWD 层：数据清洗 (关键步骤) ---
    print("Step 2: Transforming Data to DWD...")
    # 这里我们直接用 SQL 在数据库内部处理，效率更高
    dwd_sql = """
    CREATE TABLE IF NOT EXISTS dwd_ecommerce AS
    SELECT 
        InvoiceNo,
        StockCode,
        UPPER(TRIM(Description)) AS Description,
        Quantity,
        InvoiceDate, 
        UnitPrice,
        CustomerID,
        Country,
        (Quantity * UnitPrice) AS TotalLineItemAmount -- 增加一个计算列
    FROM ods_ecommerce
    WHERE CustomerID IS NOT NULL 
      AND Quantity > 0 
      AND UnitPrice > 0;
    """
    conn.execute("DROP TABLE IF EXISTS dwd_ecommerce")
    conn.execute(dwd_sql)
    
    conn.close()
    print("ETL Job Finished!")

if __name__ == "__main__":
    run_etl()