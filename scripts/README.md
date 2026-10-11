# scripts 脚本目录

本目录存放项目可执行脚本，按用途分为 `data / quality / factors / validation / composite / backtest / probe` 七类。

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
| `validation/` | 因子检验、中性化、稳健性 | IC 分析、分层、VIF、牛熊 / 板块 / 市值稳健性、最终因子库 |
| `composite/` | **阶段三**：基准与日历、因子合成 | 沪深 300 基准、调仓日历、等权 / IC / ICIR / Lasso / XGBoost |
| `backtest/` | **阶段三**：交易规则、回测、对账 | 涨跌停过滤、自研引擎入口、Backtrader 交叉验证 |
| `probe/` | 接口探测与临时诊断 | AKShare 参数探测、Tushare 字段检查 |

## 常用脚本

### 因子面板构建（factors/）

| 脚本 | 说明 | 输出 |
|---|---|---|
| `scripts/factors/build_factor_panel.py` | 一键生成 18 因子面板，主入口 | `data/processed/factor_panel.parquet`，5,088,372 × 20 列 |
| `scripts/factors/build_factor_panel_11f.py` | 旧 11 因子面板脚本 | `data/processed/factor_panel_11f.parquet` |

### 阶段二检验脚本（validation/）

| 脚本 | 阶段 | 说明 | 输出 |
|---|---|---|---|
| `run_ic_analysis.py` | M2 | 18 因子 IC / IR / 胜率 / t | `factor_ic_summary.csv` |
| `run_layered_backtest.py` | M3 | 十分位分层回测 | 分层收益 / 多空夏普 |
| `run_neutralization.py` | M4 | 市值 / 行业中性化 | 中性化后因子 |
| `run_vif_selection.py` | M5 | VIF 迭代剔除 | 8 因子清单 |
| `build_market_regime_final.py` | M6 | 市场状态落盘 | `market_regime.csv` |
| `run_regime_ic.py` | M6 | 分状态 IC + 多空 Sharpe | `regime_ic_summary.csv` |
| `run_sector_ic.py` | M6 | 分上市板块 IC | `sector_ic_summary.csv` |
| `plot_robustness.py` | M6 | 3 张稳健性热力图 | 图表 |
| `check_neutralization_exposure.py` | M7-S1 | 中性化暴露复核 | 报告 |
| `summarize_regime_significance.py` | M7-S2 | 分状态显著性汇总 | 报告 |
| `run_size_ic.py` | M7-S3 | 分市值 IC | `size_ic_summary.csv` |
| `build_final_factor_panel.py` | M7-S4 | 最终 8 因子库 | `factor_panel_final.parquet`、`final_factor_list.csv` |

> 上表中部分脚本名以仓库实际文件为准；新增脚本后请更新本表。

### 阶段三脚本（composite/ 与 backtest/）

| 脚本 | 里程碑 | 说明 | 输出 |
|---|---|---|---|
| `scripts/composite/fetch_hs300_benchmark.py` | M1 | 拉取沪深 300 日线 | `hs300_benchmark.parquet` |
| `scripts/composite/build_rebalance_calendar.py` | M1 | 生成月度调仓日 | `rebalance_calendar.csv` |
| `scripts/composite/build_composite_linear.py` | M2 | 等权 / IC 加权 / ICIR 加权（滚动到时点） | `composite_equal.parquet`、`composite_ic.parquet`、`composite_icir.parquet` |
| `scripts/composite/build_composite_lasso.py` | M3 | Lasso，按时间切训练 / 验证 | `composite_lasso.parquet` |
| `scripts/composite/build_composite_xgb.py` | M3 | XGBoost，按时间切训练 / 验证 | `composite_xgb.parquet` |
| `scripts/backtest/run_backtest.py` | M5 | 自研事件驱动引擎入口 | 净值曲线 / 持仓 / 单笔 |
| `scripts/backtest/run_backtrader.py` | M7 | Backtrader 交叉验证 | 对比表 |
| `scripts/backtest/reconcile.py` | M7 | 误差 >2% 时逐级对账（持仓 → 单笔 → 净值） | 对账报告 |

> 阶段三脚本名称为规划，落地后以仓库实际文件名为准，并同步更新本表。

## 阶段三硬性规范（写代码前必读）

1. **合成权重只能用截至当月的历史数据**。全样本 IC / IR 是未来函数，禁止。
2. **Lasso / XGBoost 按时间切分**训练 / 验证；严禁随机打散。
3. **事件驱动两条铁律**（写进 `engine.py` 顶部注释）：
   - 信号用当日数据；
   - 成交在信号日之后。
4. **绩效指标全部自实现** + 单测，不直接调第三方。
5. Backtrader 只做交叉验证，主引擎是自研的。

## 注意事项

- Tushare 批量拉取必须在干净 IP 下进行，校园网可能触发"IP 数量超限"。
- 抓取脚本应支持断点续传，跳过已存在文件。
- 运行脚本报 `ModuleNotFoundError: mfalpha` 时，先执行 `pip install -e .`。
- 输出文件默认写入 `data/processed/`，该目录不提交 Git。
- smoke 测试要选数据成熟期（如 2021-06 起），避开 20 日滚动因子的暖机期。
- `pd.Timedelta(days=365)` 建议改用 `pd.DateOffset(days=365)`。
- `np.percentile([])` 对空数组会抛 `IndexError`，调用前先判断 `len(valid) == 0`。
- 事件驱动回测：**先跑对照策略**（如固定持有 1 只、已知净值可手算），确认引擎无 bug，再上真策略。