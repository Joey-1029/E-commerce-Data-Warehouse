"""
data_quality_check.py
运行数据质量检查并输出摘要（面向作品集展示）

用法：
  python scripts/data_quality_check.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


DB_PATH = Path("data/ecommerce.db")


def _pct(part: int, total: int) -> float:
    return round((part * 100.0 / total), 2) if total else 0.0


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"找不到数据库文件：{DB_PATH.as_posix()}。请先运行 python scripts/load_data.py"
        )

    conn = sqlite3.connect(DB_PATH)

    ods_rows = pd.read_sql("SELECT COUNT(*) AS n FROM ods_ecommerce", conn)["n"][0]
    dwd_rows = pd.read_sql("SELECT COUNT(*) AS n FROM dwd_ecommerce", conn)["n"][0]

    # 按“会被过滤的原因”做互斥分类（用于解释 DWD 行数减少）
    ods_reason_sql = """
    SELECT
      CASE
        WHEN CustomerID IS NULL THEN 'drop:CustomerID_is_null'
        WHEN Quantity <= 0 THEN 'drop:Quantity_non_positive'
        WHEN UnitPrice <= 0 THEN 'drop:UnitPrice_non_positive'
        ELSE 'keep:DWD'
      END AS reason,
      COUNT(*) AS cnt
    FROM ods_ecommerce
    GROUP BY reason
    ORDER BY cnt DESC
    """
    ods_reason = pd.read_sql(ods_reason_sql, conn)

    # DWD 关键字段缺失率（用于说明数据可用性）
    dwd_missing_sql = """
    SELECT
      SUM(CASE WHEN InvoiceNo   IS NULL THEN 1 ELSE 0 END) AS miss_invoice_no,
      SUM(CASE WHEN StockCode   IS NULL THEN 1 ELSE 0 END) AS miss_stock_code,
      SUM(CASE WHEN Description IS NULL THEN 1 ELSE 0 END) AS miss_description,
      SUM(CASE WHEN InvoiceDate IS NULL THEN 1 ELSE 0 END) AS miss_invoice_date,
      SUM(CASE WHEN CustomerID  IS NULL THEN 1 ELSE 0 END) AS miss_customer_id,
      SUM(CASE WHEN Country     IS NULL THEN 1 ELSE 0 END) AS miss_country
    FROM dwd_ecommerce
    """
    dwd_missing = pd.read_sql(dwd_missing_sql, conn).iloc[0].to_dict()

    # DWD 数值范围（用于快速 sanity check）
    dwd_range_sql = """
    SELECT
      MIN(InvoiceDate) AS min_invoice_date,
      MAX(InvoiceDate) AS max_invoice_date,
      MIN(Quantity)    AS min_quantity,
      MAX(Quantity)    AS max_quantity,
      MIN(UnitPrice)   AS min_unit_price,
      MAX(UnitPrice)   AS max_unit_price,
      ROUND(SUM(TotalLineItemAmount), 2) AS gmv
    FROM dwd_ecommerce
    """
    dwd_range = pd.read_sql(dwd_range_sql, conn).iloc[0].to_dict()

    conn.close()

    print("=" * 70)
    print("Data Quality Report (ODS -> DWD)")
    print("=" * 70)
    print(f"ODS rows: {ods_rows:,}")
    print(f"DWD rows: {dwd_rows:,}")
    print(f"Kept ratio: {_pct(dwd_rows, ods_rows)}%")
    print("-" * 70)
    print("ODS filter reasons (mutually exclusive):")
    for _, row in ods_reason.iterrows():
        reason = row["reason"]
        cnt = int(row["cnt"])
        print(f"- {reason:<28} {cnt:>10,}  ({_pct(cnt, ods_rows):>6}%)")
    print("-" * 70)
    print("DWD missing checks:")
    for k, v in dwd_missing.items():
        v_int = int(v)
        print(f"- {k:<18} {v_int:>10,}  ({_pct(v_int, dwd_rows):>6}%)")
    print("-" * 70)
    print("DWD sanity ranges:")
    print(f"- invoice_date: {dwd_range['min_invoice_date']} ~ {dwd_range['max_invoice_date']}")
    print(f"- quantity:     {dwd_range['min_quantity']} ~ {dwd_range['max_quantity']}")
    print(f"- unit_price:   {dwd_range['min_unit_price']} ~ {dwd_range['max_unit_price']}")
    print(f"- GMV:          {dwd_range['gmv']}")
    print("=" * 70)


if __name__ == "__main__":
    main()

