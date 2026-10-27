# scripts 脚本目录

本目录存放项目可执行脚本，按用途分为 `data / quality / factors / validation / backtest / attribution / probe` 七类。  
阶段三脚本实际集中在 `scripts/backtest/` 下，原规划中的 `scripts/composite/` 未单独使用。  
阶段四验证分析（M0–M5）与工程化（M7）已完成；**一键复现入口在项目根 `run_all_stage4.ps1`**，不在本目录下。阶段四各脚本以仓库实际归档为准，新增后必须在本 README 登记。

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

> 阶段四脚本若未单独建子目录，按实际归档位置登记；**禁止只存在于本地而不写进本 README**。

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

### 阶段四脚本与入口

阶段四的一键复现入口在项目根，不在 `scripts/` 下：

| 脚本 / 入口 | 位置 | 里程碑 | 说明 |
|---|---|---|---|
| `run_all_stage4.ps1` | 项目根 | M7 工程化 | 阶段四一键复现；已跑通 **32 项成功、0 失败** |
| `m3_rebuild_daily_nav.py` | 按仓库实际归档 | M3 | 日频净值重建；存在 Pandas `FutureWarning`，**不影响数值，不修**，写入“已知限制” |

阶段四其余脚本（M1 基线复核、M2 风险归因、M4 仓位/因子平滑、M5 稳健性与 M5.1c 绩效对齐）以仓库实际文件为准。新增后必须在本表登记，并写清：

- 所属里程碑（M1–M5 / M7）
- 输入与输出文件
- 是否挂载 M4a×M4b 仓位
- 是否涉及 M4c 因子平滑

阶段四关键产物：

| 产物 | 说明 |
|---|---|
| `m5_1c_perf.csv` | 阶段四六组绩效对齐表 |
| `m5_1c_attribution.csv` | 阶段四 M4 增量拆解表 |
| `m4c_bt_periods` / `m4_final_periods` | 逐行完全一致（max diff = 0），用于证明 M4c 已挂载仓位 |
| `reports/figures/stage4/m1_*.png` ~ `m5_*.png` | 阶段四图表，共十几张；在项目根 `reports/` 下，**不在 `docs/` 下** |

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

## 阶段四硬性规范（写代码前必读）

1. **绩效统一对齐 `engine.nav_stats`**；年化使用 **n-1 期收益率**，不得混用其他口径。
2. **M4c 必须正名为“因子平滑（前视修正 + 系数/分数双层平滑）”**，绝不能叫“因子轮动”；代码中不存在滚动 IC 重加权。
3. **M4c 不称独立增量**：`m4c_bt_periods` 与 `m4_final_periods` 逐行完全一致（max diff = 0），说明 M4c 回测已挂载 M4a×M4b 仓位；表述为“v2 分数在仓位之上叠加”。
4. **`m3_rebuild_daily_nav.py` 的 Pandas `FutureWarning` 不修**，写入“已知限制”即可；不得因为它去改数值口径。
5. **严禁为了凑 1.680 Sharpe 或日频 MDD ≤ 25% 而调参**。定稿基线为 Sharpe **1.5527**、日频 MDD **-27.56%**，FAIL 必须如实披露。
6. **阶段四图表输出到项目根 `reports/figures/stage4/`**，不要写进 `docs/figures/stage4/`。
7. 新增阶段四脚本必须同步更新：本 README、根 README 的“关键产物文件”、`docs/README.md` 的阶段四文档节。

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

## 阶段四防坑记录

1. **M4c 叫“因子轮动”** → 错。正名为“因子平滑（前视修正 + 系数/分数双层平滑）”，代码无滚动 IC 重加权。
2. **把 M4c 当独立增量汇报** → 错。M4c 回测已挂载仓位，只能表述为“v2 分数在仓位之上叠加”。
3. **用 `top_n=25` 的全期 1.717 替代主线** → 错。剔除 2021 后仅 0.683，判定为行情馈赠，已否决。
4. **用 M4c 平滑 `K=5` 的全期 1.76 替代主线** → 错。K 未收敛且换手极低，判定为低换手红利，已否决。
5. **为凑 1.680 反复调参** → 严禁。1.55 是无前视、合规持仓下的现实上限；流动性过滤会把 Sharpe 打到 0.746。
6. **把日频 MDD 超限归因于“参数没调好”** → 错。根因是月度调仓引擎无法在期内响应急跌，2024-02-05 谷底落在两次调仓之间；改进需日内止损机制，超出当前引擎设计。
7. **把 `m3_rebuild_daily_nav.py` 的 `FutureWarning` 当 bug 修** → 不必。不影响数值，写入已知限制。
8. **图表写到 `docs/figures/stage4/`** → 错。应在项目根 `reports/figures/stage4/`。

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
- **阶段四新增**：`run_all_stage4.ps1` 必须保持 32 项成功、0 失败；任何新增阶段四脚本都要纳入该一键脚本，并在本 README 登记。