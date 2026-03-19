-- ============================================================
-- 03_cohort_retention.sql
-- 同期群留存分析（Cohort Retention Analysis）
-- 定义：将用户按首次购买月份分为同一 Cohort，
--       追踪后续每月还有多少用户回来复购
-- ============================================================

-- ----------------------------------------------------------------
-- Step 1: 找到每个用户的首次购买月份（Cohort 归属）
-- ----------------------------------------------------------------
WITH first_purchase AS (
    SELECT
        CustomerID,
        strftime('%Y-%m', MIN(InvoiceDate))     AS cohort_month
    FROM dwd_ecommerce
    WHERE CustomerID IS NOT NULL
      AND Quantity > 0
      AND UnitPrice > 0
    GROUP BY CustomerID
),

-- ----------------------------------------------------------------
-- Step 2: 列出每个用户每次活跃的月份
-- ----------------------------------------------------------------
user_activity AS (
    SELECT DISTINCT
        o.CustomerID,
        strftime('%Y-%m', o.InvoiceDate)        AS activity_month
    FROM dwd_ecommerce o
    WHERE o.CustomerID IS NOT NULL
      AND o.Quantity > 0
      AND o.UnitPrice > 0
),

-- ----------------------------------------------------------------
-- Step 3: 计算每次活跃相对于 Cohort 月份的偏移量（月数）
-- ----------------------------------------------------------------
cohort_activity AS (
    SELECT
        f.cohort_month,
        a.activity_month,
        -- 用 julianday 差值除以 30.44 近似月数，再取整
        CAST(
            (julianday(a.activity_month || '-01') -
             julianday(f.cohort_month   || '-01'))
            / 30.44
        AS INTEGER)                             AS month_offset
    FROM first_purchase f
    JOIN user_activity a ON f.CustomerID = a.CustomerID
),

-- ----------------------------------------------------------------
-- Step 4: 统计每个 Cohort 在各偏移月的活跃用户数
-- ----------------------------------------------------------------
cohort_size AS (
    -- 先算每个 Cohort 的初始用户量（offset = 0）
    SELECT
        cohort_month,
        COUNT(*)                                AS cohort_users
    FROM cohort_activity
    WHERE month_offset = 0
    GROUP BY cohort_month
),
retention_counts AS (
    SELECT
        cohort_month,
        month_offset,
        COUNT(*)                                AS active_users
    FROM cohort_activity
    WHERE month_offset >= 0
    GROUP BY cohort_month, month_offset
)

-- ----------------------------------------------------------------
-- Step 5: 输出留存率表（核心结果）
-- 留存率 = 当月活跃用户 / Cohort 初始用户数
-- ----------------------------------------------------------------
SELECT
    r.cohort_month,
    r.month_offset,
    r.active_users,
    s.cohort_users                              AS cohort_size,
    ROUND(r.active_users * 100.0 / s.cohort_users, 1)  AS retention_rate   -- 留存率 %
FROM retention_counts r
JOIN cohort_size s ON r.cohort_month = s.cohort_month
ORDER BY r.cohort_month, r.month_offset;


-- ----------------------------------------------------------------
-- （附）透视格式：以 month_offset 为列，便于导出到 Excel 看热力图
-- 因 SQLite 不支持动态 PIVOT，下方固定展示 offset 0~5 月
-- ----------------------------------------------------------------
/*
SELECT
    r.cohort_month,
    s.cohort_users                              AS cohort_size,
    MAX(CASE WHEN r.month_offset = 0 THEN ROUND(r.active_users * 100.0 / s.cohort_users, 1) END) AS "M0_%",
    MAX(CASE WHEN r.month_offset = 1 THEN ROUND(r.active_users * 100.0 / s.cohort_users, 1) END) AS "M1_%",
    MAX(CASE WHEN r.month_offset = 2 THEN ROUND(r.active_users * 100.0 / s.cohort_users, 1) END) AS "M2_%",
    MAX(CASE WHEN r.month_offset = 3 THEN ROUND(r.active_users * 100.0 / s.cohort_users, 1) END) AS "M3_%",
    MAX(CASE WHEN r.month_offset = 4 THEN ROUND(r.active_users * 100.0 / s.cohort_users, 1) END) AS "M4_%",
    MAX(CASE WHEN r.month_offset = 5 THEN ROUND(r.active_users * 100.0 / s.cohort_users, 1) END) AS "M5_%"
FROM retention_counts r
JOIN cohort_size s ON r.cohort_month = s.cohort_month
GROUP BY r.cohort_month
ORDER BY r.cohort_month;
*/