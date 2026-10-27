# 阶段四 M5 验证笔记（定稿）

## 一、M5 定位
验证稳健性，**不调参**。基线为阶段三 `lasso_horizon_all8`（Sharpe 1.4611、年化 53.69%、期频 MDD -21.84%）。

## 二、M5.1 增量分析（口径对齐 `engine.nav_stats`）

| 组别 | 年化 | Sharpe | 期频MDD | 平均仓位 |
|---|---:|---:|---:|---:|
| baseline（v1满仓） | 53.69% | 1.4611 | -21.84% | 1.000 |
| m4a_only（v1+vol） | 49.92% | 1.3885 | -24.18% | 0.947 |
| m4b_only（激进版，仅对照） | 45.48% | 1.2725 | -24.86% | 0.877 |
| m4a_m4b（温和版） | 42.55% | 1.4801 | -18.26% | 0.805 |
| **full（定稿）** | **43.49%** | **1.5527** | **-16.22%** | **0.805** |

### 顺序增量拆解（报告核心表）

| 步骤 | Sharpe | 年化 | 期频MDD |
|---|---:|---:|---:|
| baseline | 1.4611 | 53.69% | -21.84% |
| +仓位管理 | +0.0190 | -11.14pp | +3.58pp |
| +因子平滑 | +0.0727 | +0.93pp | +2.04pp |
| full | 1.5527 | 43.49% | -16.22% |

**说明**：
- 两步骤按回测实际叠加顺序拆解，未做正交分离，交互项不可分离。
- `m4c_bt_periods.csv` 与 `m4_final_periods.csv` 逐行完全一致（max_abs_diff = 0.0），M4c 回测本身已挂载 `m4_position_series`。因此报告表述为"v2 scores 在 M4a×M4b 仓位之上叠加"，不称"M4c 独立增量"。
- `m4b_only` 为早期激进版（min_pos=0，可清仓），不参与增量相加，仅作敏感性对照。

## 三、M5.2a M4b 参数稳健性

| D \ min_pos | 0.60 | 0.70 | 0.80 |
|---|---:|---:|---:|
| 0.10 | 1.5815 | 1.6012 | 1.5657 |
| **0.15（定稿）** | 1.5027 | **1.5527** | 1.5656 |
| 0.20 | 1.4520 | 1.5073 | 1.5411 |

全网格 Sharpe 1.45–1.60，定稿 (0.15, 0.70) 位于中部，邻域最优 (0.10, 0.70)=1.6012 未达 1.680，**稳健性成立，不替换**。

## 四、M5.2c M4c 平滑 K 诊断（诚实披露）

| K | 换手 | 全期 Sharpe | 剔除2021 Sharpe |
|---:|---:|---:|---:|
| 2 | 0.552 | 1.3778 | 0.5678 |
| **3（定稿）** | **0.433** | **1.5527** | **0.7211** |
| 4 | 0.358 | 1.7381 | 0.9255 |
| 5 | 0.310 | 1.7616 | 0.9810 |
| 6 | 0.287 | 1.8440 | 0.9474 |
| 7 | 0.261 | 1.8855 | 1.0073 |
| 8 | 0.251 | 1.9653 | 1.0677 |

**诊断结论**：
1. v2 代码审计通过，`next_trade_date <= sig` 训练窗口正确，无前视。
2. v1 对照扫描同样单调上升（1.368→1.863），说明"越多平滑越好"是**全局特征**，非 v2 特有。
3. 根因是**低换手红利**：K 增大 → 换手单调下降 → 成本减 → 净 Sharpe 升。K=8 换手 0.251，平均持仓约 4 个月，已偏离"月度调仓"设计。
4. **判定**：K 参数未收敛，K=3 为平衡信号时效性与换手成本的**保守选择**，不替换、不称最优。**1.680 不是不可达，而是在不改变月度调仓规格的前提下不可达**。

## 五、日频 MDD：gross vs net 近似

| 组别 | gross MDD | net 近似 MDD | 变化 |
|---|---:|---:|---:|
| baseline | -36.32% | -36.91% | -0.59pp |
| **full** | **-27.56%** | **-26.23%** | **+1.33pp** |

两口径均超 25% 约束，验收结论不变。日频净值本身是 gross 口径（`m4_rebuild_daily_nav.py` 设计选择），报告只引用 MDD 变化（±<2pp），不引用 `cost_ratio` 绝对值。

## 六、命名更正

**M4c 正名**：从"因子轮动"改为 **"因子平滑（前视修正 + 系数/分数双层平滑）"**。

原因：`composite_factors_lasso_horizon_v2.py` 实现的是"前视修正 + 系数平滑 W_SMOOTH=3"，`m4c_final.py` 再叠加"分数平滑 K=3"，**双层串联**。代码中不存在"滚动 IC 重加权"。

## 七、M5 收尾判定

- M5.3 成本敏感性、M5.5 容量测试**跳过**，合并进报告"局限与展望"一节。
- M5 产物：`m5_1c_perf.csv`、`m5_1c_attribution.csv`、`m5_2a_m4b_scan.csv`、`m5_2c_smooth_diag.csv`、`m5_2d_v1_control.csv`、`reports/figures/m5_1b_incremental.png`。
- 下一步：M7 工程化 → M6 报告定稿。

## 八、复现命令

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
cd C:\Users\16075\code\multi_factor_lab

python scripts\stage4\validate\m5_0_audit.py
python scripts\stage4\validate\m5_1c_reconcile.py
python scripts\stage4\validate\m5_1c_fix.py
python scripts\stage4\validate\m5_2_sensitivity.py
python scripts\stage4\validate\m5_2c_smooth_diag.py
python scripts\stage4\validate\m5_2d_v1_control.py