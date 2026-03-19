"""
export_portfolio_figures.py
从 SQLite 的 ADS 表导出作品集图表（PNG），用于 GitHub README 展示。

用法：
  py scripts/export_portfolio_figures.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import font_manager


DB_PATH = Path("data/ecommerce.db")
FIG_DIR = Path("analysis/figures")


def _setup_fonts() -> None:
    """
    Best-effort Chinese font setup for Windows/macOS/Linux.
    If no CJK-capable font is found, fall back to default.
    """
    candidates = [
        # Windows
        "Microsoft YaHei",
        "SimHei",
        # macOS
        "PingFang SC",
        "Heiti SC",
        # Linux common
        "Noto Sans CJK SC",
        "WenQuanYi Zen Hei",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    # Ensure minus sign renders correctly
    plt.rcParams["axes.unicode_minus"] = False


def _rfm_segment_en(label: str) -> str:
    mapping = {
        "高价值用户": "Champions",
        "忠诚用户": "Loyal",
        "新客户": "New",
        "流失高价值用户": "At Risk",
        "沉睡用户": "Hibernating",
        "潜力用户": "Promising",
    }
    return mapping.get(label, label)


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"找不到数据库文件：{DB_PATH.as_posix()}（请先运行 load_data.py）")

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    _setup_fonts()

    conn = sqlite3.connect(DB_PATH)

    # 1) GMV + MoM
    ads_gmv = pd.read_sql("SELECT * FROM ads_monthly_gmv_mom ORDER BY sale_month", conn)
    fig, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(ads_gmv["sale_month"], ads_gmv["current_gmv"], marker="o")
    ax1.set_title("GMV Trend (Monthly) + MoM Growth")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("GMV")
    ax1.tick_params(axis="x", rotation=45)

    ax2 = ax1.twinx()
    ax2.plot(
        ads_gmv["sale_month"],
        ads_gmv["mom_growth_pct"],
        marker="o",
        linestyle="--",
        color="tab:orange",
    )
    ax2.set_ylabel("MoM Growth (%)")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "gmv_mom.png", dpi=160)
    plt.close(fig)

    # 2) RFM segments
    ads_rfm = pd.read_sql("SELECT * FROM ads_rfm_segments", conn)
    # If the current font cannot render Chinese, use an English label column
    ads_rfm["user_segment_label"] = ads_rfm["user_segment"].map(_rfm_segment_en)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    sns.barplot(data=ads_rfm, x="user_segment_label", y="user_pct", ax=axes[0])
    axes[0].set_title("RFM Segments - User %")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("User %")
    axes[0].tick_params(axis="x", rotation=45)

    sns.barplot(data=ads_rfm, x="user_segment_label", y="segment_gmv", ax=axes[1])
    axes[1].set_title("RFM Segments - GMV")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("GMV")
    axes[1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "rfm_segments.png", dpi=160)
    plt.close(fig)

    # 3) Cohort retention heatmap
    ads_ret = pd.read_sql("SELECT * FROM ads_cohort_retention", conn)
    pivot = ads_ret.pivot(index="cohort_month", columns="month_offset", values="retention_rate").sort_index()
    fig = plt.figure(figsize=(10, 6))
    sns.heatmap(pivot, annot=False, cmap="Blues", linewidths=0.5)
    plt.title("Cohort Retention Heatmap (%)")
    plt.xlabel("Month Offset")
    plt.ylabel("Cohort Month")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "cohort_retention.png", dpi=160)
    plt.close(fig)

    # 4) Latest month top3 products
    ads_top3 = pd.read_sql("SELECT * FROM ads_monthly_top3_products", conn)
    latest_month = ads_top3["sale_month"].max()
    df_latest = ads_top3[ads_top3["sale_month"] == latest_month].sort_values("rank_in_month")

    fig = plt.figure(figsize=(10, 4))
    sns.barplot(data=df_latest, x="monthly_revenue", y="product_name")
    plt.title(f"Top 3 Products by Revenue - {latest_month}")
    plt.xlabel("Monthly Revenue")
    plt.ylabel("Product")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "top3_products_latest.png", dpi=160)
    plt.close(fig)

    conn.close()

    print("Exported figures to:", FIG_DIR.as_posix())


if __name__ == "__main__":
    sns.set_theme(style="whitegrid")
    main()

