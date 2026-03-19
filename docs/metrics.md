# 指标字典（Metrics Dictionary）

本项目基于 `dwd_ecommerce`（清洗后的明细）计算指标。为保证口径一致，默认使用以下清洗规则：
- `CustomerID IS NOT NULL`
- `Quantity > 0`
- `UnitPrice > 0`

---

## 1. GMV（Gross Merchandise Value）
- **定义**：订单行金额之和（不含退款/负数行，已在 DWD 过滤）
- **计算**：\(\sum Quantity \times UnitPrice\)
- **明细字段**：`TotalLineItemAmount`（ETL 生成）
- **常用切片**：按月（`strftime('%Y-%m', InvoiceDate)`）、国家、商品

---

## 2. MoM（GMV 月环比）
- **定义**：当月 GMV 相比上月的增长率
- **计算**：
  - `prev_month_gmv = LAG(gmv) OVER (ORDER BY sale_month)`
  - `mom_growth_pct = (gmv - prev_month_gmv) / prev_month_gmv`
- **产出表**：`ads_monthly_gmv_mom`

---

## 3. Top 商品（按月 Top3）
- **定义**：每月 GMV 最高的 Top3 商品
- **计算**：
  - `monthly_revenue = SUM(Quantity * UnitPrice)`
  - `ROW_NUMBER() OVER (PARTITION BY sale_month ORDER BY monthly_revenue DESC)`
- **产出表**：`ads_monthly_top3_products`

---

## 4. AOV（Average Order Value，客单价）
- **定义**：每单平均金额
- **计算**：
  - 先按 `InvoiceNo` 聚合得到 `invoice_total`
  - `AOV = AVG(invoice_total)`
- **相关分析脚本**：`scripts/sql/04_repurchase_and_metrics.sql`（客单价分桶）

---

## 5. 复购率（Repurchase Rate）
- **定义**：购买次数（不同 `InvoiceNo`）≥ 2 的用户数 / 全部用户数
- **计算**：
  - `order_count = COUNT(DISTINCT InvoiceNo) GROUP BY CustomerID`
  - `repurchase_rate = SUM(order_count>=2)/COUNT(*)`
- **相关分析脚本**：`scripts/sql/04_repurchase_and_metrics.sql`

---

## 6. 新客 / 老客 GMV 拆分
- **定义**：以“用户首购月份”标记新客月，其余月份为老客
- **计算**：
  - `first_month = MIN(strftime('%Y-%m', InvoiceDate)) GROUP BY CustomerID`
  - 若 `order_month == first_month` → 新客，否则老客
- **相关分析脚本**：`scripts/sql/04_repurchase_and_metrics.sql`

---

## 7. Cohort 留存（按月）
- **定义**：按“首次购买月份”分 cohort，统计后续每个偏移月仍活跃的用户占比
- **关键字段**：
  - `cohort_month = MIN(strftime('%Y-%m', InvoiceDate))`
  - `activity_month = strftime('%Y-%m', InvoiceDate)`
  - `month_offset`：activity 相对 cohort 的月偏移
- **产出表**：`ads_cohort_retention`

---

## 8. RFM 分群
- **Recency**：距“分析快照日”的天数（快照日 = 数据最大日期 + 1 天）
- **Frequency**：不同 `InvoiceNo` 数量
- **Monetary**：累计 GMV
- **分数**：`NTILE(5)` 打分（R 反向，F/M 正向），并给出业务标签
- **产出表**：`ads_rfm_segments`

