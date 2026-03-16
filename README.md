📄 README 模板 (GitHub 专用)
🛒 E-Commerce Data Warehouse Project
这是一个基于 Medallion Architecture (奖牌架构) 思想构建的轻量级电商数仓项目。项目实现了从原始 CSV 数据到多层结构化数据库的完整 ETL 流程。

🏗 项目架构
本项目遵循标准的数仓分层设计，确保了数据的可追溯性和逻辑解耦：

ODS (Original Data Store): 贴源层，存储原始 Kaggle 电商数据。

DWD (Data Warehouse Detail): 明细层，进行数据清洗（处理空值、去重、格式化字符串）。

ADS (Application Data Service): 应用层，存储最终的业务分析指标（如 Top 10 客户、每小时销售分布）。

📂 目录结构
Plaintext
ecommerce_data_warehouse/
├── data/
│   ├── data.csv          # 原始数据集 (Source)
│   └── ecommerce.db      # 自动生成的 SQLite 数据库 (Warehouse)
├── scripts/
│   └── load_data.py      # ETL 脚本：负责 ODS -> DWD 的转化
├── analysis/
│   └── analysis.ipynb    # 分析手册：负责 ADS 层生成及可视化
└── README.md
🚀 技术栈
语言: Python 3.x

数据库: SQLite (SQL)

库: Pandas (数据处理), Matplotlib/Seaborn (可视化)

📈 核心发现
用户价值: 通过 SQL 聚合识别出贡献度最高的 Top 10 客户，并保存至 ads_top_customers 表。

销售趋势: 发现下午 12:00 - 15:00 是下单高峰期，为库存管理和广告投放提供决策支持。