# scripts 脚本目录

本目录存放项目可执行脚本，按用途分为 `data / quality / factors / validation / probe` 五类。

## 运行前准备

```powershell
cd C:\Users\16075\code\multi_factor_lab
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## 子目录说明

| 子目录 | 用途 | 典型内容 |
|---|---|---|
| `data/` | 数据拉取与构建 | 腾讯日线、Tushare `daily_basic`、`fina_indicator`、PIT 财务面板 |
| `quality/` | 数据质量检查 | 缺失率、重复值、极端涨跌幅、面板完整性 |
| `factors/` | 因子面板构建 | `build_factor_panel.py`（18 因子主入口） |
| `validation/` | 因子检验、中性化、稳健性 | IC 分析、分层回测、VIF、牛熊 / 板块 / 市值稳健性、最终因子库 |
| `probe/` | 接口探测与临时诊断 | AKShare 参数探测、Tushare 字段检查 |

## 常用脚本

### 因子面板构建（factors/）

| 脚本 | 说明 | 输出 |
|---|---|---|
| `scripts/factors/build_factor_panel.py` | 一键生成 18 因子面板，主入口 | `data/processed/factor_panel.parquet`，5,088,372 行 × 20 列 |
| `scripts/factors/build_factor_panel_11f.py` | 旧 11 因子面板脚本，保留兼容 | `data/processed/factor_panel_11f.parquet` |

### 阶段二检验脚本（validation/）

| 脚本 | 阶段 | 说明 | 输出 |
|---|---|---|---|
| `run_ic_analysis.py` | M2 | 18 因子 IC / IR / 胜率 / t 值 | `factor_ic_summary.csv` |
| `run_layered_backtest.py`（按仓库实际文件名为准） | M3 | 十分位分层回测 | 分层收益 / 多空夏普 |
| `run_neutralization.py`（按仓库实际文件名为准） | M4 | 市值 / 行业中性化 | 中性化后因子 |
| `run_vif_selection.py`（按仓库实际文件名为准） | M5 | VIF 迭代剔除 | 最终 8 因子清单 |
| `build_market_regime.py` | M6 | 市场状态探查（保留作为记录） | — |
| `build_market_regime_final.py` | M6 | 市场状态落盘 | `market_regime.csv` |
| `run_regime_ic.py` | M6 | 分状态 IC + 多空 Sharpe | `regime_ic_summary.csv` |
| `run_sector_ic.py` | M6 | 分上市板块 IC | `sector_ic_summary.csv` |
| `plot_robustness.py` | M6 | 3 张稳健性热力图 | 图表 |
| `check_neutralization_exposure.py` | M7-S1 | 中性化暴露复核 | 报告 |
| `summarize_regime_significance.py` | M7-S2 | 分状态显著性汇总 | 报告 |
| `run_size_ic.py` | M7-S3 | 分市值 IC（30% / 40% / 30%） | `size_ic_summary.csv` |
| `build_final_factor_panel.py` | M7-S4 | 最终因子库（8 因子，方向统一） | `factor_panel_final.parquet`、`final_factor_list.csv` |

> 上表中标注"按仓库实际文件名为准"的脚本，请以仓库实际文件为准；新增脚本后请更新本表。

## 注意事项

- Tushare 批量拉取必须在干净 IP 下进行，校园网可能触发"IP 数量超限"。
- 抓取脚本应支持断点续传，跳过已存在文件。
- 运行脚本报 `ModuleNotFoundError: mfalpha` 时，先执行 `pip install -e .`。
- 输出文件默认写入 `data/processed/`，该目录不提交 Git。
- smoke 测试要选数据成熟期（如 2021-06 起），避开 20 日滚动因子的暖机期。
- `pd.Timedelta(days=365)` 建议改用 `pd.DateOffset(days=365)`，避免新版 numpy 弃用警告。
- `np.percentile([])` 对空数组会抛 `IndexError`，调用前先判断 `len(valid) == 0`。