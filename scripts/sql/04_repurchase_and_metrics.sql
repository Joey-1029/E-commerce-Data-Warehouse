-- ============================================================
-- 04_repurchase_and_metrics.sql
-- 复购率 & 补充业务指标
-- ============================================================

-- ----------------------------------------------------------------
-- Part 1: 整体复购率
-- 定义：购买次数 >= 2 的用户 / 全部用户
-- 业务意义：衡量平台用户粘性，大厂面试常被问到
-- ----------------------------------------------------------------
WITH order_count_per_user AS (
    SELECT
        CustomerID,
        COUNT(DISTINCT InvoiceNo)               AS order_count
    FROM dwd_ecommerce
    WHERE CustomerID IS NOT NULL
      AND Quantity > 0
      AND UnitPrice > 0
    GROUP BY CustomerID
)
SELECT
    COUNT(*)                                    AS total_customers,
    SUM(CASE WHEN order_count >= 2 THEN 1 ELSE 0 END)
                                                AS repurchase_customers,
    ROUND(
        SUM(CASE WHEN order_count >= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        1
    )                                           AS repurchase_rate_pct
FROM order_count_per_user;


-- ----------------------------------------------------------------
-- Part 2: 各月新客 vs 老客 GMV 拆分
-- 业务意义：判断增长是来自拉新还是老客复购，指导运营策略
-- ----------------------------------------------------------------
WITH first_purchase AS (
    SELECT
        CustomerID,
        MIN(strftime('%Y-%m', InvoiceDate))     AS first_month
    FROM dwd_ecommerce
    WHERE CustomerID IS NOT NULL
      AND Quantity > 0
      AND UnitPrice > 0
    GROUP BY CustomerID
),
tagged_orders AS (
    SELECT
        o.CustomerID,
        strftime('%Y-%m', o.InvoiceDate)        AS order_month,
        o.Quantity * o.UnitPrice                AS revenue,
        CASE
            WHEN strftime('%Y-%m', o.InvoiceDate) = f.first_month
            THEN '新客'
            ELSE '老客'
        END                                     AS customer_type
    FROM dwd_ecommerce o
    JOIN first_purchase f ON o.CustomerID = f.CustomerID
    WHERE o.Quantity > 0 AND o.UnitPrice > 0
)
SELECT
    order_month,
    customer_type,
    ROUND(SUM(revenue), 2)                      AS gmv,
    COUNT(DISTINCT CustomerID)                  AS user_count
FROM tagged_orders
GROUP BY order_month, customer_type
ORDER BY order_month, customer_type;


-- ----------------------------------------------------------------
-- Part 3: 商品品类复购率排名 Top 10
-- 业务意义：找到最能带来复购的商品，支持选品和促销决策
-- ----------------------------------------------------------------
WITH user_product_orders AS (
    SELECT
        CustomerID,
        Description                             AS product,
        COUNT(DISTINCT InvoiceNo)               AS purchase_count
    FROM dwd_ecommerce
    WHERE CustomerID IS NOT NULL
      AND Quantity > 0
      AND UnitPrice > 0
    GROUP BY CustomerID, Description
),
product_repurchase AS (
    SELECT
        product,
        COUNT(DISTINCT CustomerID)              AS total_buyers,
        SUM(CASE WHEN purchase_count >= 2 THEN 1 ELSE 0 END)
                                                AS repurchase_buyers
    FROM user_product_orders
    GROUP BY product
    HAVING total_buyers >= 50                   -- 过滤购买人数太少的长尾商品
)
SELECT
    product,
    total_buyers,
    repurchase_buyers,
    ROUND(repurchase_buyers * 100.0 / total_buyers, 1)
                                                AS repurchase_rate_pct
FROM product_repurchase
ORDER BY repurchase_rate_pct DESC
LIMIT 10;


-- ----------------------------------------------------------------
-- Part 4: 客单价分布区间
-- 业务意义：了解用户消费层次，为定价和促销门槛提供依据
-- ----------------------------------------------------------------
WITH invoice_value AS (
    SELECT
        InvoiceNo,
        ROUND(SUM(Quantity * UnitPrice), 2)     AS invoice_total
    FROM dwd_ecommerce
    WHERE CustomerID IS NOT NULL
      AND Quantity > 0
      AND UnitPrice > 0
    GROUP BY InvoiceNo
)
SELECT
    CASE
        WHEN invoice_total < 10   THEN '< £10'
        WHEN invoice_total < 50   THEN '£10 - £50'
        WHEN invoice_total < 100  THEN '£50 - £100'
        WHEN invoice_total < 500  THEN '£100 - £500'
        ELSE '>= £500'
    END                                         AS price_bucket,
    COUNT(*)                                    AS order_count,
    ROUND(SUM(invoice_total), 2)                AS bucket_gmv,
    ROUND(AVG(invoice_total), 2)                AS avg_order_value
FROM invoice_value
GROUP BY price_bucket
ORDER BY MIN(invoice_total);