"""
run_sql_analysis.py
将 4 个 SQL 分析脚本的结果写入 SQLite ADS 层，并打印摘要
用法：python scripts/run_sql_analysis.py
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("data/ecommerce.db")
SQL_DIR = Path("scripts/sql")

conn = sqlite3.connect(DB_PATH)

# ── 1. 窗口函数：月度 Top3 商品 ──────────────────────────────────
sql_top3 = """
WITH monthly_product_sales AS (
    SELECT strftime('%Y-%m', InvoiceDate) AS sale_month,
           Description AS product_name,
           SUM(Quantity * UnitPrice) AS monthly_revenue
    FROM dwd_ecommerce
    WHERE CustomerID IS NOT NULL AND Quantity > 0 AND UnitPrice > 0
    GROUP BY sale_month, Description
),
ranked AS (
    SELECT sale_month, product_name, monthly_revenue,
           ROW_NUMBER() OVER (PARTITION BY sale_month ORDER BY monthly_revenue DESC) AS rank_in_month
    FROM monthly_product_sales
)
SELECT sale_month, rank_in_month, product_name, ROUND(monthly_revenue, 2) AS monthly_revenue
FROM ranked WHERE rank_in_month <= 3
ORDER BY sale_month, rank_in_month
"""

# ── 2. 月度 GMV 环比 ─────────────────────────────────────────────
sql_mom = """
WITH monthly_gmv AS (
    SELECT strftime('%Y-%m', InvoiceDate) AS sale_month,
           ROUND(SUM(Quantity * UnitPrice), 2) AS gmv
    FROM dwd_ecommerce
    WHERE CustomerID IS NOT NULL AND Quantity > 0 AND UnitPrice > 0
    GROUP BY sale_month
),
gmv_with_lag AS (
    SELECT sale_month, gmv,
           LAG(gmv, 1) OVER (ORDER BY sale_month) AS prev_month_gmv
    FROM monthly_gmv
)
SELECT sale_month, gmv AS current_gmv, prev_month_gmv,
       CASE WHEN prev_month_gmv IS NULL THEN NULL
            ELSE ROUND((gmv - prev_month_gmv) * 100.0 / prev_month_gmv, 2)
       END AS mom_growth_pct
FROM gmv_with_lag ORDER BY sale_month
"""

# ── 3. RFM 分层 ──────────────────────────────────────────────────
sql_rfm = """
WITH snapshot_date AS (
    SELECT DATE(MAX(InvoiceDate), '+1 day') AS today FROM dwd_ecommerce
),
rfm_raw AS (
    SELECT o.CustomerID,
           CAST(julianday((SELECT today FROM snapshot_date)) - julianday(MAX(o.InvoiceDate)) AS INTEGER) AS recency_days,
           COUNT(DISTINCT o.InvoiceNo) AS frequency,
           ROUND(SUM(o.Quantity * o.UnitPrice), 2) AS monetary
    FROM dwd_ecommerce o
    WHERE o.CustomerID IS NOT NULL AND o.Quantity > 0 AND o.UnitPrice > 0
    GROUP BY o.CustomerID
),
rfm_scores AS (
    SELECT CustomerID, recency_days, frequency, monetary,
           NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
           NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
           NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
    FROM rfm_raw
),
rfm_labeled AS (
    SELECT CustomerID, recency_days, frequency, monetary, r_score, f_score, m_score,
           ROUND((r_score*0.3 + f_score*0.35 + m_score*0.35), 2) AS rfm_score,
           CASE WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN '高价值用户'
                WHEN r_score >= 3 AND f_score >= 3                  THEN '忠诚用户'
                WHEN r_score >= 4 AND f_score <= 2                  THEN '新客户'
                WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN '流失高价值用户'
                WHEN r_score <= 2 AND f_score <= 2                  THEN '沉睡用户'
                ELSE '潜力用户'
           END AS user_segment
    FROM rfm_scores
)
SELECT user_segment,
       COUNT(CustomerID) AS user_count,
       ROUND(COUNT(CustomerID)*100.0/SUM(COUNT(CustomerID)) OVER (), 1) AS user_pct,
       ROUND(SUM(monetary), 2) AS segment_gmv,
       ROUND(SUM(monetary)*100.0/SUM(SUM(monetary)) OVER (), 1) AS gmv_pct,
       ROUND(AVG(monetary), 2) AS avg_monetary,
       ROUND(AVG(frequency), 1) AS avg_frequency,
       ROUND(AVG(recency_days), 0) AS avg_recency_days
FROM rfm_labeled GROUP BY user_segment ORDER BY segment_gmv DESC
"""

# ── 4. Cohort 留存 ────────────────────────────────────────────────
sql_cohort = """
WITH first_purchase AS (
    SELECT CustomerID, strftime('%Y-%m', MIN(InvoiceDate)) AS cohort_month
    FROM dwd_ecommerce WHERE CustomerID IS NOT NULL AND Quantity > 0 AND UnitPrice > 0
    GROUP BY CustomerID
),
user_activity AS (
    SELECT DISTINCT o.CustomerID, strftime('%Y-%m', o.InvoiceDate) AS activity_month
    FROM dwd_ecommerce o WHERE o.CustomerID IS NOT NULL AND o.Quantity > 0 AND o.UnitPrice > 0
),
cohort_activity AS (
    SELECT f.cohort_month, a.activity_month,
           CAST((julianday(a.activity_month||'-01') - julianday(f.cohort_month||'-01')) / 30.44 AS INTEGER) AS month_offset
    FROM first_purchase f JOIN user_activity a ON f.CustomerID = a.CustomerID
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_users FROM cohort_activity WHERE month_offset = 0 GROUP BY cohort_month
),
retention_counts AS (
    SELECT cohort_month, month_offset, COUNT(*) AS active_users
    FROM cohort_activity WHERE month_offset >= 0 GROUP BY cohort_month, month_offset
)
SELECT r.cohort_month, r.month_offset, r.active_users, s.cohort_users AS cohort_size,
       ROUND(r.active_users*100.0/s.cohort_users, 1) AS retention_rate
FROM retention_counts r JOIN cohort_size s ON r.cohort_month = s.cohort_month
ORDER BY r.cohort_month, r.month_offset
"""

queries = {
    "ads_monthly_top3_products": sql_top3,
    "ads_monthly_gmv_mom":       sql_mom,
    "ads_rfm_segments":          sql_rfm,
    "ads_cohort_retention":      sql_cohort,
}

print("=" * 55)
print("  Build ADS tables from SQL")
print("=" * 55)

for table_name, sql in queries.items():
    df = pd.read_sql_query(sql, conn)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    # 用纯 ASCII 输出，兼容 Windows 控制台默认编码（避免 UnicodeEncodeError）
    print(f"OK  {table_name:<35} {len(df):>5} rows")

conn.close()
print("=" * 55)
print("All results written to data/ecommerce.db. Visualize in analysis/analysis.ipynb")