## `data/` — 数据获取与构建

### 日线行情（腾讯源）

| 脚本 | 用途 |
|---|---|
| `fetch_stock_list.py` | 拉取全市场股票列表 |
| `build_universe.py` | 构建股票池 |
| `fetch_daily_tencent.py` | 拉取腾讯前复权日线 |
| `build_daily_panel_tencent.py` | 合并为日线面板 |
| `clean_panel_tencent.py` | 清洗日线面板（±20% 过滤等） |

### 财务数据（Tushare 源）

| 脚本 | 用途 | 输出 |
|---|---|---|
| `fetch_daily_basic.py` | 拉取 PE_TTM / PB / 换手率（按交易日） | `data/raw/financial/daily_basic_*.parquet` |
| `fetch_fina_indicator.py` | 拉取财务指标（逐票，分批） | `data/raw/financial/fina_indicator_part_*.parquet` |

> 使用前需在项目根目录 `.env` 配置 `TUSHARE_TOKEN`。

### 历史 / 探索脚本

`build_daily_panel.py`、`clean_panel.py`、`fetch_daily_panel.py`、`fetch_panel_10.py`、`fetch_single_stock.py` 为早期探索脚本，保留作参考。

## `factors/` — 因子构建

| 脚本 | 用途 | 输出 |
|---|---|---|
| **`build_factor_panel.py`** | **主入口**，生成 18 因子 | `data/processed/factor_panel.parquet` |
| `build_factor_panel_11f.py` | 历史保留，生成 11 因子（价量 + 技术） | `data/processed/factor_panel_11f.parquet` |
| `build_financial_panel.py` | 财务数据 PIT 对齐到日频 | `data/processed/financial_panel_pit.parquet` |
| `analyze_factor.py` | 单因子分析（含 alphalens IC 图） | `docs/figures/alphalens_ic/` |
| `plot_close.py` | 收盘价可视化 | `docs/figures/` |

历史 / 探索脚本：`compute_factors_panel.py`、`compute_momentum_panel.py`。

## `quality/` — 数据质量检查

| 脚本 | 用途 |
|---|---|
| `data_quality_report_tencent.py` | 生成数据质量报告（当前版本） |
| `check_missing.py` / `verify_missing.py` | 缺失率检查与复核 |
| `inspect_extreme_pct.py` | 极端涨跌幅检查 |
| `inspect_negative_price.py` | 负价格检查（前复权坑） |
| `inspect_tencent_files.py` | 腾讯原始文件检查 |

历史：`data_quality_report.py`。

## `probe/` — 数据源探测（临时脚本）

| 脚本 | 用途 |
|---|---|
| `test_data_sources.py` | 数据源可用性探测 |
| `test_tencent.py` / `test_tencent_segment.py` | 腾讯接口探测 |

## 运行环境

所有脚本从项目根目录运行，确保已激活 `.venv`：

```powershell
cd C:\Users\16075\code\multi_factor_lab
.\.venv\Scripts\Activate.ps1
python scripts/factors/build_factor_panel.py