-- ============================================================
-- 02_rfm_segmentation.sql
-- RFM 用户分层模型
-- R = Recency   最近一次购买距今天数（越小越好）
-- F = Frequency 购买频次（越大越好）
-- M = Monetary  累计消费金额（越大越好）
-- ============================================================

-- ----------------------------------------------------------------
-- Step 1: 计算每个用户的 R / F / M 原始值
-- ----------------------------------------------------------------
WITH snapshot_date AS (
    -- 用数据集中最大日期 +1 作为"今天"，模拟分析快照时间点
    SELECT DATE(MAX(InvoiceDate), '+1 day') AS today
    FROM dwd_ecommerce
),
rfm_raw AS (
    SELECT
        o.CustomerID,
        -- Recency：距今天数，越小说明越近
        CAST(
            julianday((SELECT today FROM snapshot_date)) -
            julianday(MAX(o.InvoiceDate))
        AS INTEGER)                             AS recency_days,
        -- Frequency：不同 InvoiceNo 的数量（每张发票算一次购买）
        COUNT(DISTINCT o.InvoiceNo)             AS frequency,
        -- Monetary：累计消费金额
        ROUND(SUM(o.Quantity * o.UnitPrice), 2) AS monetary
    FROM dwd_ecommerce o
    WHERE o.CustomerID IS NOT NULL
      AND o.Quantity > 0
      AND o.UnitPrice > 0
    GROUP BY o.CustomerID
),

-- ----------------------------------------------------------------
-- Step 2: 用 NTILE(5) 对 R/F/M 各打 1-5 分
-- 注意 Recency 越小越好，所以分数反向
-- ----------------------------------------------------------------
rfm_scores AS (
    SELECT
        CustomerID,
        recency_days,
        frequency,
        monetary,
        -- R 分：天数越少，分越高 → 反向排序
        NTILE(5) OVER (ORDER BY recency_days DESC)  AS r_score,
        -- F 分：频次越高，分越高
        NTILE(5) OVER (ORDER BY frequency ASC)      AS f_score,
        -- M 分：金额越高，分越高
        NTILE(5) OVER (ORDER BY monetary ASC)       AS m_score
    FROM rfm_raw
),

-- ----------------------------------------------------------------
-- Step 3: 根据 RFM 组合打业务标签
-- ----------------------------------------------------------------
rfm_labeled AS (
    SELECT
        CustomerID,
        recency_days,
        frequency,
        monetary,
        r_score,
        f_score,
        m_score,
        -- 综合分（简单加权，可按业务调整权重）
        ROUND((r_score * 0.3 + f_score * 0.35 + m_score * 0.35), 2) AS rfm_score,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4
                THEN '高价值用户'        -- Champions
            WHEN r_score >= 3 AND f_score >= 3
                THEN '忠诚用户'          -- Loyal Customers
            WHEN r_score >= 4 AND f_score <= 2
                THEN '新客户'            -- New Customers (recent but low frequency)
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3
                THEN '流失高价值用户'    -- At Risk (used to be good, now gone quiet)
            WHEN r_score <= 2 AND f_score <= 2
                THEN '沉睡用户'          -- Hibernating
            ELSE '潜力用户'              -- Promising / Needs Attention
        END                             AS user_segment
    FROM rfm_scores
)

-- ----------------------------------------------------------------
-- Step 4: 输出结果 + 统计各分层人数与 GMV 占比
-- ----------------------------------------------------------------
SELECT
    user_segment,
    COUNT(CustomerID)                           AS user_count,
    ROUND(COUNT(CustomerID) * 100.0 /
        SUM(COUNT(CustomerID)) OVER (), 1)      AS user_pct,        -- 人数占比 %
    ROUND(SUM(monetary), 2)                     AS segment_gmv,
    ROUND(SUM(monetary) * 100.0 /
        SUM(SUM(monetary)) OVER (), 1)          AS gmv_pct,         -- GMV 占比 %
    ROUND(AVG(monetary), 2)                     AS avg_monetary,
    ROUND(AVG(frequency), 1)                    AS avg_frequency,
    ROUND(AVG(recency_days), 0)                 AS avg_recency_days
FROM rfm_labeled
GROUP BY user_segment
ORDER BY segment_gmv DESC;


-- ----------------------------------------------------------------
-- （附）如需查看单个用户明细，可单独执行此查询
-- ----------------------------------------------------------------
/*
SELECT *
FROM rfm_labeled
ORDER BY rfm_score DESC
LIMIT 50;
*/