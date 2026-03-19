-- ============================================================
-- 01_window_functions.sql
-- 窗口函数分析：月度 Top 商品 & 销售额环比增长
-- 数据来源：dwd_ecommerce（DWD 明细层）
-- ============================================================

-- ----------------------------------------------------------------
-- Part 1: 每月销售额 Top 3 商品
-- 业务意义：识别各月明星商品，为选品和备货提供依据
-- 用到的窗口函数：SUM() OVER (PARTITION BY) + ROW_NUMBER()
-- ----------------------------------------------------------------
WITH monthly_product_sales AS (
    SELECT
        strftime('%Y-%m', InvoiceDate)          AS sale_month,
        Description                             AS product_name,
        SUM(Quantity * UnitPrice)               AS monthly_revenue
    FROM dwd_ecommerce
    WHERE CustomerID IS NOT NULL
      AND Quantity > 0
      AND UnitPrice > 0
    GROUP BY sale_month, Description
),
ranked AS (
    SELECT
        sale_month,
        product_name,
        monthly_revenue,
        -- 在每个月份内按销售额降序排名
        ROW_NUMBER() OVER (
            PARTITION BY sale_month
            ORDER BY monthly_revenue DESC
        ) AS rank_in_month
    FROM monthly_product_sales
)
SELECT
    sale_month,
    rank_in_month,
    product_name,
    ROUND(monthly_revenue, 2) AS monthly_revenue
FROM ranked
WHERE rank_in_month <= 3
ORDER BY sale_month, rank_in_month;


-- ----------------------------------------------------------------
-- Part 2: 月度 GMV 环比增长率
-- 业务意义：发现销售季节性规律，Q4 是否出现增长高峰
-- 用到的窗口函数：LAG() OVER (ORDER BY)
-- ----------------------------------------------------------------
WITH monthly_gmv AS (
    SELECT
        strftime('%Y-%m', InvoiceDate)          AS sale_month,
        ROUND(SUM(Quantity * UnitPrice), 2)     AS gmv
    FROM dwd_ecommerce
    WHERE CustomerID IS NOT NULL
      AND Quantity > 0
      AND UnitPrice > 0
    GROUP BY sale_month
),
gmv_with_lag AS (
    SELECT
        sale_month,
        gmv,
        -- LAG 取上一个月的 GMV
        LAG(gmv, 1) OVER (ORDER BY sale_month)  AS prev_month_gmv
    FROM monthly_gmv
)
SELECT
    sale_month,
    gmv                                                         AS current_gmv,
    prev_month_gmv,
    CASE
        WHEN prev_month_gmv IS NULL THEN NULL
        ELSE ROUND((gmv - prev_month_gmv) * 100.0 / prev_month_gmv, 2)
    END                                                         AS mom_growth_pct  -- Month-over-Month 环比增长率 (%)
FROM gmv_with_lag
ORDER BY sale_month;


-- ----------------------------------------------------------------
-- Part 3: 每个客户的累计消费额（Running Total）
-- 业务意义：观察高价值客户的消费积累曲线
-- 用到的窗口函数：SUM() OVER (PARTITION BY ... ORDER BY ...)
-- ----------------------------------------------------------------
WITH customer_orders AS (
    SELECT
        CustomerID,
        strftime('%Y-%m', InvoiceDate)          AS order_month,
        ROUND(SUM(Quantity * UnitPrice), 2)     AS monthly_spend
    FROM dwd_ecommerce
    WHERE CustomerID IS NOT NULL
      AND Quantity > 0
      AND UnitPrice > 0
    GROUP BY CustomerID, order_month
)
SELECT
    CustomerID,
    order_month,
    monthly_spend,
    -- 每个客户内，按时间顺序累加消费额
    ROUND(
        SUM(monthly_spend) OVER (
            PARTITION BY CustomerID
            ORDER BY order_month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 2
    )                                                           AS cumulative_spend
FROM customer_orders
ORDER BY CustomerID, order_month;