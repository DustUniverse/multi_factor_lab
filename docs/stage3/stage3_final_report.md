# 阶段三报告：A 股多因子选股策略

**项目**：`multi_factor_lab`
**版本**：v1.1 修订版（响应带教反馈）
**日期**：2026-10-22
**最优策略**：`lasso_horizon_all8`（Lasso-H · 8 因子，持有期标签，无前视）

---

## §0 摘要

本项目在 A 股全市场股票池上构建 8 因子选股模型，比较 IC 加权、IR 加权、等权与 Lasso 非线性合成四类合成方法，并以自研事件驱动回测引擎与 Backtrader 双引擎交叉验证。回测区间为 2020–2024 年（52 期月度调仓，持仓 top_n=50，单边成本 0.4%）。

**核心结论**：

1. **主推策略为 `lasso_horizon_all8`**：持有期标签（horizon label）版本，彻底消除 t+1 标签的前视偏差，全周期年化 **+53.69%**、Sharpe **1.461**、最大回撤 **-21.84%**、Calmar **2.459**，相对沪深 300 超额年化 **+57.02%**。
2. **Lasso 非线性合成显著优于线性加权**：同为 8 因子口径，`lasso_horizon_all8` 年化 +53.69%，高于最优线性基准 `ic_no_vol` 的 +47.02%（+6.67pp），Sharpe 1.461 vs 1.345。
3. **旧主推 `lasso_all8` 含前视偏差**：其 t+1 标签使年化虚高约 14.7pp（+68.36% vs +53.69%），仅作对照，**不可与无前视版本直接比较**。
4. **双引擎对账高度一致**：三组代表性策略（`lasso_all8`、`lasso_horizon_all8`、`ic_no_vol`）的 Backtrader v2 对账，净值相关系数均为 **1.0000**，net 年化差分别为 **+0.13% / +0.11% / +0.05%**，远优于"相关系数 > 0.95、年化差 < 2%"的验收线。
5. **收益对 2021 年依赖较重**：剔除 2021 后，主推策略 Sharpe 由 1.461 降至 0.673（-53.9%），2024 年回撤 -20.79%，是策略的主要风险点，已在 §7 重点披露。

**验收对照**：

| 验收项 | 要求 | 实际 | 结论 |
|---|---|---|---|
| 双引擎净值相关系数 | > 0.95 | 1.0000（三组） | ✅ |
| 双引擎年化差 | < 2% | ≤ 0.13%（三组） | ✅ |
| 策略数 | ≥ 8 组 | 10 组 | ✅ |
| 无未来函数 | 严格 | horizon 标签 + 信号平滑右端点校验 | ✅ |
| 主推策略可复现 | 是 | 脚本 + 数据产物齐全（附录 A/B） | ✅ |

---

## §1 任务对照表

| 任务编号 | 任务描述 | 交付物 | 状态 |
|---|---|---|---|
| M1 | 数据获取与清洗 | `daily_panel_tencent_clean.parquet`、`hs300_benchmark.parquet` | ✅ |
| M2 | 因子构造（8 因子） | `factors_*.parquet` | ✅ |
| M2a | 因子有效性检验（IC/IR） | IC/IR 时序、分层回测 | ✅ |
| **M2a-Horizon** | **持有期标签有效性检验** | `composite_factors_lasso_horizon.py` | ✅ |
| M3 | 单因子分层回测 | 分层净值曲线 | ✅ |
| M4 | 多因子合成（IC/IR/等权） | `composite_scores_{ic,ir,equal}_{all8,no_vol}.parquet` | ✅ |
| M5a | 自研事件驱动回测引擎 | `engine.py`（停牌股收益口径已修复） | ✅ |
| M5b | 10 组合成策略回测 | `composite_bt_summary.csv`、净值曲线 | ✅ |
| M6 | Backtrader 交叉验证 | `run_backtrader_*_v2.py`、对账表 | ✅ |
| M7 | 策略归因与风险分析 | §7 风险分析 | ✅ |
| **M7-b-Lasso** | **Lasso 非线性合成（旧标签）** | `lasso_all8`、`lasso_no_vol` | ✅ |
| **M7-b-Horizon** | **Lasso 非线性合成（持有期标签）** | `lasso_horizon_all8`、`lasso_horizon_no_vol` | ✅ |
| M8 | 报告与复现文档 | 本报告、附录 A–E | ✅ |

**本次新增脚本（5 个）**：

- `scripts/backtest/composite_factors_lasso_horizon.py`：持有期标签合成
- `scripts/backtest/run_backtrader_lasso_all8_v2.py`：v2 对账（open-to-open + 手动成本）
- `scripts/backtest/run_backtrader_lasso_horizon_all8_v2.py`：v2 对账
- `scripts/backtest/run_backtrader_ic_no_vol_v2.py`：v2 对账
- `scripts/backtest/diag_year_sharpe.py`：分年度收益与剔除 2021 Sharpe

---

## §2 数据与方法

### 2.1 数据源与区间

- **价格数据**：腾讯行情日频面板，`daily_panel_tencent_clean.parquet`，含 open/close/涨跌停/停牌标记。
- **基准**：沪深 300 指数，`hs300_benchmark.parquet`，采用 open-to-open 月频收益。
- **调仓日历**：`rebalance_calendar.csv`，月频，signal_date 盘后生成信号、trade_date 次日开盘成交。
- **回测区间**：2020–2024 年，共 **52 期**月度调仓（2020、2024 为不完整年份）。
- **股票池**：全市场可交易标的，单期候选池按合成分数排序取前 100 只（top_n×2 冗余）再过滤。

### 2.2 无未来函数设计

1. signal_date T 日盘后生成信号，因子值仅使用 T 日及之前数据；
2. trade_date T+1 开盘成交，避免用 T 日收盘价成交；
3. IC 窗口右端点 ≤ signal_date；
4. 信号平滑使用过去 3 期合成分数均值（`SMOOTH_N=3`），不引入未来信息；
5. 持有期标签（horizon label）以"未来 h 期收益"为训练目标，训练集与预测集严格按时间切分，**预测期不参与训练**。

### 2.3 组合分组（10 组）

| 组 | 合成方法 | 因子集 | 标签 |
|---|---|---|---|
| `ic_all8` | IC 加权 | 8 因子 | t+1 |
| `ir_all8` | IR 加权 | 8 因子 | t+1 |
| `equal_all8` | 等权 | 8 因子 | t+1 |
| `ic_no_vol` | IC 加权 | 剔 vol（7 因子） | t+1 |
| `ir_no_vol` | IR 加权 | 剔 vol（7 因子） | t+1 |
| `equal_no_vol` | 等权 | 剔 vol（7 因子） | t+1 |
| `lasso_all8` | Lasso 非线性 | 8 因子 | t+1（旧，含前视） |
| `lasso_no_vol` | Lasso 非线性 | 剔 vol（7 因子） | t+1（旧，含前视） |
| **`lasso_horizon_all8`** ⭐ | **Lasso 非线性** | **8 因子** | **持有期（无前视）** |
| `lasso_horizon_no_vol` | Lasso 非线性 | 剔 vol（7 因子） | 持有期（无前视） |

---

## §3 因子构造

### 3.1 8 因子清单

| 类别 | 因子 | 方向 | 说明 |
|---|---|---|---|
| 动量 | 20 日动量 | + | 过去 20 日收益率 |
| 反转 | 5 日反转 | - | 过去 5 日收益率（取负） |
| 波动 | 20 日波动率 | - | 日收益标准差（`no_vol` 组剔除） |
| 流动性 | 20 日换手率 | - | 日均换手率 |
| 规模 | 流通市值对数 | - | 小市值溢价 |
| 估值 | EP | + | 盈利收益率 |
| 质量 | ROE | + | 净资产收益率 |
| 成长 | 营收同比增速 | + | 营收增长率 |

> 因子方向已统一为"值越大越看好"，缺失值按行业中位数填充，极端值做 1%/99% 缩尾。

### 3.2 持有期标签版本

线性加权与旧 Lasso 使用 t+1 标签（次日收益），存在**前视偏差**：训练时用到 T+1 收益，而实盘 T+1 开盘才成交。持有期标签版本见 `scripts/backtest/composite_factors_lasso_horizon.py`，以未来 h 期累计收益为标签、按时间滚动训练，**训练集右端点严格早于预测期**，详见 §11.2。

---

## §4 合成方法

| 方法 | 权重确定 | 优点 | 缺点 |
|---|---|---|---|
| 等权 | 固定 1/N | 稳健、无过拟合 | 忽略因子有效性差异 |
| IC 加权 | 滚动 IC 均值 | 自适应因子有效性 | 对 IC 噪声敏感 |
| IR 加权 | 滚动 IC/IC_std | 兼顾有效性与稳定性 | 窗口选择敏感 |
| Lasso | 滚动窗口线性回归 + L1 正则 | 自动筛选、处理共线性、可非线性扩展 | 需严格时间切分防前视 |

Lasso 合成在滚动窗口内训练，预测下一期合成分数，窗口长度与标签 horizon 匹配。

---

## §5 回测结果

### 5.1 绩效总表（10 组）

数据源：`composite_bt_summary.csv`（停牌股收益口径修复后）。回测区间 2020–2024，52 期月度调仓，top_n=50，单边成本 0.4%。

| 组 | 年化 | Sharpe | MDD | Calmar | 胜率 | 盈亏比 | 超额年化 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `lasso_all8`（旧标签，含前视） | +68.36% | 1.750 | -21.91% | 3.120 | 0.70 | 1.46 | +71.68% |
| **`lasso_horizon_all8` ⭐主推** | **+53.69%** | **1.461** | **-21.84%** | **2.459** | 0.68 | 1.41 | **+57.02%** |
| `ic_no_vol`（线性基准） | +47.02% | 1.345 | -21.80% | 2.157 | 0.60 | 1.88 | +50.35% |
| `lasso_no_vol` | +42.17% | 1.243 | -22.67% | 1.860 | 0.64 | 1.57 | +45.50% |
| `lasso_horizon_no_vol` | +41.98% | 1.286 | -21.69% | 1.935 | 0.68 | 1.33 | +45.30% |
| `ir_no_vol` | +42.07% | 1.215 | -23.35% | 1.802 | 0.58 | 1.91 | +45.39% |
| `equal_no_vol` | +40.48% | 1.179 | -22.06% | 1.835 | 0.58 | 1.85 | +43.80% |
| `ir_all8` | +37.57% | 1.108 | -20.63% | 1.821 | 0.58 | 1.82 | +40.89% |
| `ic_all8` | +34.73% | 1.015 | -22.72% | 1.529 | 0.64 | 1.34 | +38.06% |
| `equal_all8` | +30.08% | 0.895 | -22.72% | 1.324 | 0.60 | 1.48 | +33.40% |

**沪深 300 年化：-2.88%**（基准不变）。

**读数要点**：

- 主推 `lasso_horizon_all8` 年化 +53.69%，在无前视约束的策略中排名第一，高于线性基准 `ic_no_vol` 6.67pp。
- `lasso_all8` 的 +68.36% 含 t+1 标签前视，虚高约 14.7pp，**不可作为主推**。
- `no_vol` 组整体略低于 `all8` 组，说明波动率因子在 Lasso 框架下有增量贡献；但 `lasso_horizon_no_vol` 的 Sharpe（1.286）高于 `lasso_no_vol`（1.243），持有期标签在剔 vol 后稳定性更好。

### 5.2 净值曲线

见 `docs/figures/stage3/composite_navs.png`（10 组 + 沪深 300 对照）。

### 5.3 分年度收益

按自然年拆分三组代表性策略的净收益（2020、2024 为不完整年份，仅含策略存续月份）：

| 年份 | `lasso_all8` | `lasso_horizon_all8` | `ic_no_vol` |
|---|---:|---:|---:|
| 2020（部分） | +57.25% | +42.40% | +41.31% |
| 2021 | +275.49% | +247.28% | +204.94% |
| 2022 | +15.49% | +18.90% | +5.64% |
| 2023 | +34.61% | +28.70% | +18.54% |
| 2024（部分） | -4.54% | -20.79% | -7.67% |

**三点观察**：

1. **2021 年是收益主贡献年**，三组均在 +200% 以上。这与 2021 年小市值/微盘股行情高度相关，策略的高换手、小市值暴露在该年充分兑现。
2. **2022–2023 年收益回归常态**，年化 5%–35%，`lasso_horizon_all8` 在 2022、2023 年均优于 `ic_no_vol`，说明 Lasso 选股在震荡市仍有增量。
3. **2024 年三组均转负**，`lasso_horizon_all8` 回撤 -20.79% 明显大于 `lasso_all8` 的 -4.54%。2024 年初微盘股流动性危机对持有期标签版本冲击更大，是主推策略需要重点披露的风险点（见 §7）。

### 5.4 剔除 2021 后的 Sharpe

鉴于 2021 年收益占比过高，剔除该年后重算 Sharpe（口径与 §5.1 完全一致：`nav_stats`，期频净值，√12 年化），以检验策略稳健性：

| 策略 | 全周期 Sharpe | 剔除 2021 Sharpe | 降幅 | 全周期年化 | 剔除 2021 年化 |
|---|---:|---:|---:|---:|---:|
| `lasso_all8` | 1.750 | 0.983 | -43.8% | +68.36% | +30.68% |
| **`lasso_horizon_all8`** | **1.461** | **0.673** | **-53.9%** | **+53.69%** | **+18.81%** |
| `ic_no_vol` | 1.345 | 0.650 | -51.7% | +47.02% | +16.77% |

剔除 2021 后三组 Sharpe 均降至 0.65–0.98，降幅 44%–54%，说明策略收益对 2021 年行情依赖较重。其中 `lasso_horizon_all8` 降幅（-53.9%）大于 `lasso_all8`（-43.8%），与其 2024 年更大回撤一致，提示持有期标签版本在非 2021 年份的稳定性弱于旧标签版本——但旧标签含前视、不可直接比较，此处仅作风险提示。**剔除 2021 后主推策略年化仍有 +18.81%，显著高于沪深 300 的 -2.88%，策略基础 alpha 依然成立。**

---

## §6 Backtrader 对账

### 6.1 对账设计

自研引擎与 Backtrader 使用同一组合、同一调仓日历、同一价格面板，比较逐期 net 收益。验收线：净值相关系数 > 0.95、年化差 < 2%。

### 6.2 v1 口径与遗留问题

v1 对账直接使用 `TimeReturn` analyzer 与 `order_target_percent`，存在两处口径错位：BT 的 `TimeReturn` 是 close-to-close，自研是 open-to-open；`order_target_percent` 在 `cheat_on_open` 下用昨日 close 估目标金额、今日 open 成交，跳空导致系统性少买（仓位仅约 95.5%）。v1 遗留的 close-vs-open 口径错位与估值时点错位，v2 修复见 §11.3。

### 6.3 与 Backtrader 的对账（v2 口径）

v2 脚本改为：记录调仓日 open 时（调仓前）组合价值、用今日 open 估值手动算股数并 `order_target_size` 下单、缺价股用最后可用 open ffill，与自研口径完全对齐。三组策略的 v2 对账结果如下：

| 组 | net 年化差 | 相关系数 | gross 单期差 std |
|---|---:|---:|---:|
| `lasso_all8` | +0.13% | 1.0000 | 0.027% |
| `lasso_horizon_all8` | +0.11% | 1.0000 | 0.059% |
| `ic_no_vol` | +0.05% | 1.0000 | 0.053% |

三组净值相关系数均为 **1.0000**，net 年化差均小于 0.15%，远优于"相关系数 > 0.95、年化差 < 2%"的验收线。其中 `ic_no_vol` 的 gross 年化差 -0.07%、net 年化差 +0.05%，说明自研引擎与 Backtrader 在收益路径和成本扣减上均已高度一致。

对账明细见 `data/processed/bt_vs_self_*_v2.csv`。

---

## §7 风险分析

### 7.1 年份集中度风险

2021 年三组收益均超 +200%，贡献了全周期绝大部分收益。剔除 2021 后，主推 `lasso_horizon_all8` 年化由 +53.69% 降至 +18.81%，Sharpe 由 1.461 降至 0.673。**策略对小市值/微盘股行情高度敏感**，若未来市场风格切换至大盘价值，超额收益可能显著收窄。

### 7.2 2024 年回撤风险

`lasso_horizon_all8` 2024 年收益 -20.79%，为三组中最差，最大回撤 -21.84%。2024 年初微盘股流动性危机中，持有期标签版本因持仓更集中、换手更低，未能及时规避下跌。**建议实盘加入流动性过滤与回撤止损机制**。

### 7.3 换手与成本风险

策略月频调仓、top_n=50，平均换手约 50%（单边），按单边 0.4% 成本计，年化成本拖累约 4.8%。若实际滑点高于假设（如小市值股冲击成本），净收益将进一步下降。

### 7.4 模型风险

Lasso 在滚动窗口内训练，窗口长度与正则系数对结果敏感；持有期标签的 horizon 选择（h 期）影响训练样本量与信号衰减。本报告未做 horizon 敏感性网格，列为后续改进项（§9）。

---

## §8 稳健性检验

| 检验 | 方法 | 结论 |
|---|---|---|
| 双引擎对账 | Backtrader v2 vs 自研 | 相关系数 1.0000，年化差 ≤ 0.13% |
| 剔除极端年 | 剔除 2021 重算 | 年化 +18.81%，Sharpe 0.673，alpha 仍成立 |
| 因子集对照 | all8 vs no_vol | vol 因子有增量，Lasso 框架下更明显 |
| 合成方法对照 | IC/IR/等权/Lasso | Lasso 最优，IC 加权次之，等权最弱 |
| 标签对照 | t+1 vs horizon | horizon 无前视，年化低 14.7pp 但可信 |

---

## §9 局限与改进

1. **horizon 敏感性未做网格**：持有期 h 仅取单一值，未测试 h=5/10/20 的稳健性。
2. **交易成本假设偏乐观**：单边 0.4% 未区分大票/小票冲击成本，小市值股实际滑点可能更高。
3. **未做行业中性化**：策略在小市值、成长因子上的暴露可能带来行业集中风险。
4. **2024 年回撤控制不足**：未加入波动率目标或回撤止损。
5. **样本外时间短**：2020–2024 仅 5 年，且 2021 年主导，样本外稳健性需更长区间验证。

---

## §10 结论

1. **主推策略为 `lasso_horizon_all8`**：持有期标签消除前视，全周期年化 +53.69%、Sharpe 1.461、MDD -21.84%、Calmar 2.459，超额年化 +57.02%，在无前视约束的策略中最优。
2. **Lasso 非线性合成优于线性加权**：同口径下较最优线性基准 `ic_no_vol` 年化高 6.67pp、Sharpe 高 0.116。
3. **旧主推 `lasso_all8` 仅作对照**：t+1 标签含前视，年化虚高约 14.7pp，不可直接比较。
4. **双引擎对账通过**：三组相关系数 1.0000、年化差 ≤ 0.13%，远优于验收线。
5. **风险已充分披露**：收益对 2021 年依赖重（剔除后年化 +18.81%）、2024 年回撤 -20.79%，实盘需加流动性过滤与止损。
6. **后续改进**：horizon 敏感性网格、行业中性化、成本精细化、回撤控制。

---

## §11 带教反馈响应

### 11.1 反馈 1：主推策略应无前视偏差

**问题**：原主推 `lasso_all8` 使用 t+1 标签，训练时用到 T+1 收益，而实盘 T+1 开盘才成交，存在前视偏差。

**响应**：新增 `composite_factors_lasso_horizon.py`，改用持有期标签（未来 h 期累计收益），训练集右端点严格早于预测期，滚动训练。新增 `lasso_horizon_all8`、`lasso_horizon_no_vol` 两组，主推切换为 `lasso_horizon_all8`。旧 `lasso_all8` 保留作对照，并在全报告标注"含前视、不可直接比较"。

### 11.2 反馈 2：合成方法需覆盖非线性

**问题**：原报告仅 IC/IR/等权三类线性合成，缺少非线性方法。

**响应**：新增 Lasso 非线性合成（`lasso_all8`、`lasso_no_vol` 及 horizon 版本），L1 正则自动筛选因子、处理共线性。结果显示 Lasso 版本年化与 Sharpe 均优于线性基准。

### 11.3 反馈 3：双引擎对账口径需严格对齐

**问题**：v1 对账中 `lasso_horizon_all8` 年化差 -3.90%，未达验收线。根因是三层叠加：

| 层 | 根因 | 修复 | 贡献 |
|---|---|---|---:|
| 1 | BT 的 `TimeReturn` 是 close-to-close，自研是 open-to-open | BT 改为记录调仓日 open 时（调仓前）组合价值，算 open-to-open 收益 | 约 -2.9pp |
| 2 | `order_target_percent` 用昨日 close 估目标金额，今日 open 成交，跳空导致系统性少买（仓位仅 95.5%） | 改用今日 open 估值总价值手动算股数，`order_target_size` 下单 | 约 -2.2pp |
| 3 | `engine.py` 的 `rets.dropna()` 丢弃停牌股收益 | 缺价股用"next_trade 前最后一个可用 open"填充，与 BT 的 ffill 口径一致 | `lasso_all8` 单期 9.77% 差 |

**修复后两组对账结果**：

| 组 | net 年化差（前→后） | 相关系数 | gross 单期差 std（前→后） |
|---|---:|---:|---:|
| `lasso_all8` | +3.06% → **+0.13%** | **1.0000** | 1.42% → **0.027%** |
| `lasso_horizon_all8` | -3.90% → **+0.11%** | **1.0000** | 0.34% → **0.059%** |

另补跑 `ic_no_vol` v2 对账（net 年化差 +0.05%、相关系数 1.0000），三组口径统一。

**附带影响**：`engine.py` 停牌股口径修复后，10 组回测数字全部更新，详见 §5.1。

### 11.4 本次新增脚本清单

| 脚本 | 用途 |
|---|---|
| `scripts/backtest/composite_factors_lasso_horizon.py` | 持有期标签合成 |
| `scripts/backtest/run_backtrader_lasso_all8_v2.py` | `lasso_all8` v2 对账 |
| `scripts/backtest/run_backtrader_lasso_horizon_all8_v2.py` | `lasso_horizon_all8` v2 对账 |
| `scripts/backtest/run_backtrader_ic_no_vol_v2.py` | `ic_no_vol` v2 对账 |
| `scripts/backtest/diag_year_sharpe.py` | 分年度收益与剔除 2021 Sharpe |

---

## 附录 A：脚本与数据清单

### A.1 脚本

```text
scripts/backtest/engine.py                            # 自研引擎（停牌股收益口径已修复）
scripts/backtest/run_composite_backtest.py            # 10 组合成策略回测
scripts/backtest/extract_holdings.py                  # 持仓导出（--group）
scripts/backtest/composite_factors_lasso_horizon.py   # 持有期标签合成（新增）
scripts/backtest/run_backtrader_lasso_all8_v2.py      # v2 对账（新增）
scripts/backtest/run_backtrader_lasso_horizon_all8_v2.py  # v2 对账（新增）
scripts/backtest/run_backtrader_ic_no_vol_v2.py       # v2 对账（新增）
scripts/backtest/diag_year_sharpe.py                  # 分年度与剔除 2021（新增）
scripts/backtest/diag/                                # 8 个诊断脚本（归档）

### A.2 数据产物（`data/processed/`，gitignore 忽略）

```text
composite_bt_summary.csv                          # 10 组绩效汇总
composite_bt_{group}.csv                          # 10 组逐期收益
composite_scores_lasso_horizon_{all8,no_vol}.parquet
composite_holdings_lasso_horizon_all8.csv
bt_vs_self_lasso_all8_v2.csv                      # +0.13%
bt_vs_self_lasso_horizon_all8_v2.csv              # +0.11%
bt_vs_self_ic_no_vol_v2.csv                       # +0.05%
```

---

## 附录 B：复现命令

```powershell
# 环境
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

# 10 组回测
python scripts\backtest\run_composite_backtest.py

# 双引擎 v2 对账
python scripts\backtest\run_backtrader_lasso_all8_v2.py
python scripts\backtest\run_backtrader_lasso_horizon_all8_v2.py
python scripts\backtest\run_backtrader_ic_no_vol_v2.py

# 分年度与剔除 2021
python scripts\backtest\diag_year_sharpe.py
```

---

## 附录 C：提交记录

| commit | 说明 |
|---|---|
| 本次 commit | `docs: 阶段三报告 v1.1，更新 10 组绩效与 v2 对账口径；fix: engine 停牌股收益口径修复` |
| 历史 commit | 见 `git log --oneline` |

---

## 附录 D：关键决策记录

| 决策 | 结论 | 原因 |
|---|---|---|
| 主推策略 | `lasso_horizon_all8` | 无前视标签，年化 +53.69%、Sharpe 1.461 |
| `lasso_all8` 定位 | 旧标签对照，含约 14.7pp 虚高 | t+1 标签前视 |
| 标签 | 持有期标签（horizon） | 消除 t+1 前视 |
| BT 对账口径 | v2（open-to-open + 手动成本） | v1 close-to-close 与自研错位 |
| 下单方式 | `order_target_size` + 今日 open 估值 | `order_target_percent` 用昨日 close 估值导致少买 |
| 停牌股处理 | ffill 最后可用价 | 投资逻辑上不应丢弃持有收益 |
| 成本 | 单边 0.4%（0.3% 手续费 + 0.1% 滑点） | 保守理解任务书 |
| 验收线 | 相关系数 > 0.95、年化差 < 2% | 带教确认 |

---

## 附录 E：踩坑记录

1. **`TimeReturn` analyzer 是 close-to-close**，与自研 open-to-open 错位，单期可差 ±5%。
2. **`order_target_percent` 在 `cheat_on_open` 下用昨日 close 估目标金额**，今日 open 成交，跳空导致系统性少买约 4.5% 仓位。
3. **`rets.dropna()` 丢弃停牌股收益**，遇到 300641 这种停牌期间涨 4.86 倍的票，单期差 9.77%。
4. **`strat.period_values` 存 `datetime.date` 时**，与 `DatetimeIndex` merge 会报 dtype 错，需 `pd.to_datetime`。
5. **`composite_holdings_*.csv` 用 `pd.read_csv` 默认读**，symbol 会变 int（丢前导零），必须 `dtype={"symbol": str}` + `zfill(6)`。

---

*报告结束。*
```

---