```markdown
# scripts 脚本目录

本目录存放项目可执行脚本，按用途分为 `data / quality / factors / validation / backtest / attribution / probe` 七类。  
阶段三脚本实际集中在 `scripts/backtest/` 下，原规划中的 `scripts/composite/` 未单独使用。

## 运行前准备

```powershell
cd C:\Users\16075\code\multi_factor_lab
.\.venv\Scripts\Activate.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
pip install -e .
```

## 子目录说明

| 子目录 | 用途 | 典型内容 |
|---|---|---|
| `data/` | 数据拉取与构建 | 腾讯日线、Tushare `daily_basic`、`fina_indicator`、PIT 财务面板 |
| `quality/` | 数据质量检查 | 缺失率、重复值、极端涨跌幅、面板完整性 |
| `factors/` | 因子面板构建 | `build_factor_panel.py`（18 因子主入口） |
| `validation/` | 因子检验、中性化、稳健性 | IC 分析、分层、VIF、牛熊 / 板块 / 市值稳健性、最终因子库 |
| `backtest/` | **阶段三**：基准、日历、合成、回测、交叉验证 | 沪深 300 基准、调仓日历、线性/Lasso（含持有期）合成、10 组回测、Backtrader v2 对账 |
| `backtest/diag/` | 阶段三诊断脚本归档 | 停牌股、dropna、单期差、分年度 Sharpe 等 11 个诊断脚本 |
| `attribution/` | 数据源探测 | 腾讯行情、HS300、申万成分股接口探测 |
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

### 阶段三脚本（scripts/backtest/）

| 脚本 | 里程碑 | 说明 | 输出 |
|---|---|---|---|
| `fetch_hs300.py` | M1 | 拉取沪深 300 日线 | `hs300_benchmark.parquet` |
| `build_rebalance_calendar.py` | M1 | 生成月度调仓日，共 52 期 | `rebalance_calendar.csv` |
| `compute_daily_ic.py` | M2-prep | 计算日频因子 IC（1D 口径） | `factor_ic_daily_1d.parquet` |
| `composite_factors.py` | M2 | 线性合成：IC / IR / 等权 × all8 / no_vol，共 6 组 | `composite_scores_{ic\|ir\|equal}_{all8\|no_vol}.parquet`、`composite_weights_*.csv` |
| `composite_factors_lasso.py` | M2a-Lasso | Lasso 非线性合成（旧 t+1 标签），滚动 12 个月，最少 120 交易日，`alpha=1e-4` | `composite_scores_lasso_{all8\|no_vol}.parquet`、`composite_weights_lasso_*.csv` |
| `composite_factors_lasso_horizon.py` | M2a-Horizon | 持有期标签 Lasso 合成（无前视），训练集右端点严格早于预测期 | `composite_scores_lasso_horizon_{all8\|no_vol}.parquet`、`composite_weights_lasso_horizon_*.csv` |
| `engine.py` | M5 | 自研事件驱动回测引擎（停牌股收益口径已修复） | 被 `run_*` 脚本导入 |
| `run_single_backtest.py` | M5a | 单因子回测 / 对账 | 单因子回测结果 |
| `stage2_recompute_monthly.py` | M5a | 月频修正 | `stage2_monthly_recompute.csv` |
| `run_composite_backtest.py` | M5b | 10 组组合回测，`GROUPS` 列表含 4 组 Lasso（含持有期） | `composite_bt_*.csv`、`composite_bt_summary.csv` |
| `extract_holdings.py` | M7-a | 提取指定组持仓（`--group`） | `composite_holdings_{group}.csv` |
| `run_backtrader_lasso_all8.py` | M7-b-v1 | v1 对账（close-to-close 口径，仅作对照） | `bt_vs_self_lasso_all8.csv` |
| `run_backtrader_lasso_horizon_all8.py` | M7-b-v1 | v1 对账（close-to-close 口径，仅作对照） | `bt_vs_self_lasso_horizon_all8.csv` |
| `run_backtrader_lasso_all8_v2.py` | M7-b-v2 | v2 对账（open-to-open + 手动成本），net 年化差 +0.13% | `bt_vs_self_lasso_all8_v2.csv` |
| `run_backtrader_lasso_horizon_all8_v2.py` | M7-b-v2 | v2 对账，net 年化差 +0.11% | `bt_vs_self_lasso_horizon_all8_v2.csv` |
| `run_backtrader_ic_no_vol_v2.py` | M7-b-v2 | v2 对账，net 年化差 +0.05% | `bt_vs_self_ic_no_vol_v2.csv` |
| `diag_year_sharpe.py` | M8 | 分年度收益与剔除 2021 Sharpe（与 summary 同口径） | 终端输出 |

### 诊断脚本（scripts/backtest/diag/）

归档 11 个阶段三诊断脚本，用于定位 `engine.py` 与 Backtrader 差异、停牌股处理、dropna 影响等：

| 脚本 | 用途 |
|---|---|
| `diag_300641.py` | 定位 300641 停牌期间收益差 |
| `diag_dropna.py` / `diag_dropna_all8.py` | `rets.dropna()` 对收益的影响 |
| `diag_gross.py` | gross 收益逐期对比 |
| `diag_period_diff.py` | 单期差定位 |
| `diag_all8_v2.py` | `lasso_all8` v2 对账辅助 |
| `diag_20240506.py` / `diag_horizon_diff.py` | 特定日期 / horizon 差异 |
| `compare_holdings_lasso_all8.py` / `compare_holdings_temp.py` | 持仓对比 |
| `diag_year_sharpe.py` | 分年度与剔除 2021 |

## 阶段三硬性规范（写代码前必读）

1. **合成权重只能用截至当月的历史数据**。全样本 IC / IR 是未来函数，禁止。
2. **Lasso 按时间切分**训练 / 验证；严禁随机打散。
3. **持有期标签训练集右端点必须严格早于预测期**，标签为未来 h 期累计收益。
4. **事件驱动两条铁律**（写进 `engine.py` 顶部注释）：
   - 信号用当日数据；
   - 成交在信号日之后。
5. **绩效指标全部自实现** + 单测，不直接调第三方。
6. Backtrader 只做交叉验证，主引擎是自研的。
7. **停牌股收益用最后可用 open 填充**，不得 `dropna` 丢弃。

## 阶段三踩坑记录

1. Backtrader 主时钟是“所有 data 交易日交集” → 用日历 feed 破。
2. Backtrader 遇到 NaN 不推进主时钟 → reindex + ffill/bfill。
3. pandas 大表逐只过滤会卡死 → 先 `groupby` 再 O(1) 取。
4. symbol int vs str 静默不匹配 → 统一 `astype(str).str.zfill(6)`。
5. PowerShell 中文乱码 → `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`。
6. `except IndexError: continue` 必须显式写，否则 UnboundLocalError。
7. Lasso 期数与线性组不对齐 → 直接读线性组 index。
8. `BUFFER_RATIO = 0.95` 会带来约 2% 年化差 → 改 1.0 与自研对齐。
9. **`TimeReturn` analyzer 是 close-to-close**，与自研 open-to-open 错位，单期可差 ±5% → v2 改为记录调仓日 open 时组合价值。
10. **`order_target_percent` 在 `cheat_on_open` 下用昨日 close 估目标金额**，今日 open 成交，跳空导致系统性少买约 4.5% 仓位 → 改 `order_target_size` + 今日 open 估值。
11. **`rets.dropna()` 丢弃停牌股收益**，300641 停牌期间涨 4.86 倍，单期差 9.77% → 用最后可用 open ffill 填充。
12. **pre-commit flake8 报 E501 行过长** → 先 `pre-commit run --files <file>` 让 black 自动折行，再 `git add` 重新提交。

## 注意事项

- Tushare 批量拉取必须在干净 IP 下进行，校园网可能触发“IP 数量超限”。
- 抓取脚本应支持断点续传，跳过已存在文件。
- 运行脚本报 `ModuleNotFoundError: mfalpha` 时，先执行 `pip install -e .`。
- 输出文件默认写入 `data/processed/`，该目录不提交 Git。
- smoke 测试要选数据成熟期（如 2021-06 起），避开 20 日滚动因子的暖机期。
- `pd.Timedelta(days=365)` 建议改用 `pd.DateOffset(days=365)`。
- `np.percentile([])` 对空数组会抛 `IndexError`，调用前先判断 `len(valid) == 0`。
- 事件驱动回测：**先跑对照策略**（如固定持有 1 只、已知净值可手算），确认引擎无 bug，再上真策略。
- 新增脚本后，**同步更新本 README 和根 README 的“关键产物文件”表**。
```