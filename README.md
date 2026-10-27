# multi_factor_lab

> A 股多因子选股策略实习项目  
> 核心流程：**数据获取 → 因子库 → 检验中性化 → 合成 → 回测 → 交叉验证 → 归因 → 稳健性验证**  
> 当前阶段：**阶段一 ✅ | 阶段二 ✅ | 阶段三 ✅ | 阶段四 M0–M5 验证分析 + M7 工程化 ✅，最终总报告撰写中 ⏳**  
> 主线策略：**`lasso_horizon_all8`**（持有 50 只等权，月度调仓，无前视）  
> 阶段四 M4 最终绩效：期频年化 **43.49%**，Sharpe **1.5527**，期频 MDD **-16.22%**，日频 MDD **-27.56%**  
> 验收结论：**期频 MDD PASS、剔除 2021 不劣化 PASS；Sharpe ≥ 1.680 FAIL、日频 MDD ≤ 25% FAIL**  
> 最后更新：2026-10-27

---

## 目录

- [项目简介](#项目简介)
- [当前状态](#当前状态)
- [阶段四核心结论](#阶段四核心结论)
- [阶段四验收对照](#阶段四验收对照)
- [核心绩效对照](#核心绩效对照)
- [M4 增量拆解](#m4-增量拆解)
- [负面结论与过拟合否决](#负面结论与过拟合否决)
- [口径与命名规范](#口径与命名规范)
- [已知限制](#已知限制)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [数据体系](#数据体系)
- [因子库](#因子库)
- [阶段三历史绩效](#阶段三历史绩效)
- [Backtrader 交叉验证](#backtrader-交叉验证)
- [关键产物文件](#关键产物文件)
- [阶段进度](#阶段进度)
- [开发与维护约定](#开发与维护约定)
- [常见问题](#常见问题)
- [下一步计划](#下一步计划)

## 项目简介

`multi_factor_lab` 是一个 A 股多因子选股策略实习项目，目标是从数据获取、因子构建、因子检验与中性化，到因子合成、事件驱动回测、独立引擎交叉验证、风险归因与稳健性验证，形成一套可复现、可测试、可扩展的多因子研究流程。

- GitHub：https://github.com/DustUniverse/multi_factor_lab
- 本地路径：`C:\Users\16075\code\multi_factor_lab`
- 当前分支：`stage4`
- 开发环境：Windows + VS Code + PowerShell
- 虚拟环境：`.venv`，Python 3.12
- 包管理：`pip install -e .`（可编辑安装）
- 关键依赖：`pandas`、`numpy`、`scikit-learn 1.9.1`、`backtrader 1.9.78.123`

> 说明：阶段四最终总报告骨架已建立在 `docs/stage4/stage4_final_report.md`，正文待定稿。README 中的绩效数字统一使用阶段四定稿基线，报告正文必须引用同一口径。

## 当前状态

| 模块 | 状态 | 说明 |
|---|---|---|
| 数据体系 | ✅ 已验收 | 4853 只股票，2019-09-30 ~ 2024-09-30，1213 个交易日 |
| 基础因子库 | ✅ 18 / 18 | 价量 7 + 技术 4 + 财务 4 + 估值 2 + 换手 1 |
| 阶段一验收 | ✅ 通过 | `docs/stage1_checklist.md` |
| 阶段二 M0–M7 | ✅ 全部完成 | IC 检验 → 分层 → 中性化 → VIF 剔除 → 稳健性 → 最终因子库 → 报告 |
| 最终因子库 | ✅ 8 因子 | `data/processed/factor_panel_final.parquet`，5,045,205 × 8，方向已统一 |
| 阶段二验收 | ✅ 全部达标 | `docs/stage2_final_report.md` |
| 阶段三 M0–M8 | ✅ 全部完成 | 基准与日历 → 线性合成 → Lasso（含持有期标签） → 10 组回测 → Backtrader v2 交叉验证 → 最终报告 |
| 阶段三验收 | ✅ 全部达标 | 超额 +57.02%、Sharpe 1.461、BT 相关系数 1.0000、年化差 ≤ 0.13% |
| 阶段四 M0–M5 | ✅ 验证分析完成 | 基线复核、风险归因、M4 仓位/因子平滑优化、M5 稳健性验证 |
| 阶段四 M7 工程化 | ✅ 完成 | `run_all_stage4.ps1` 一键复现已跑通：32 项成功，0 失败 |
| 阶段四验收 | ⚠️ 2 PASS / 2 FAIL | 期频 MDD PASS、剔除 2021 不劣化 PASS；Sharpe 目标 FAIL、日频 MDD FAIL |
| 阶段四最终总报告 | ⏳ 撰写中 | `docs/stage4/stage4_final_report.md`，骨架已建，正文待定稿 |
| 单元测试 | ✅ 阶段一/二基线 59 passed | 阶段三/四新增测试以 `python -m pytest` 实际输出为准 |

## 阶段四核心结论

1. **1.680 的 Sharpe 目标不可达，且不应通过调参凑目标。**  
   策略 alpha 高度集中于低流动性小盘股：v2 top50 中 **43.2%** 落在 `amihud` 非流动性 top5% 尾部。流动性过滤会将 Sharpe 从 **1.553 削减至 0.746**。在无前视、合规持仓前提下，**1.55 是现实上限**。

2. **日频 MDD 超限的根因是月度调仓引擎无法在期内响应急跌。**  
   2024-02-05 的谷底落在两次调仓之间，整段 1 月跌幅无法规避。要改进日频 MDD，需要日内止损/风险控制机制，**超出当前月度调仓引擎设计**。

3. **M4c 是 M4 唯一有效增强模块，但必须正名。**  
   M4c 应称为 **“因子平滑（前视修正 + 系数/分数双层平滑）”**，不能称为“因子轮动”。代码中不存在滚动 IC 重加权。其回测已挂载 M4a×M4b 仓位，报告表述为 **“v2 分数在仓位之上叠加”**，不称独立增量。

4. **M3 风险归因：收益主要来自个股特质。**  
   8 因子仅解释 **3.02%** 的月频波动，**96.98%** 为个股特质。行业风险集中在成长制造：机械设备 **12.4%**、基础化工 **8.3%** 等。

5. **阶段四不是“全部达标”。**  
   README 与最终报告都必须如实披露：Sharpe 目标差 **0.127**，日频 MDD 超限 **2.56pp**。不得为了凑目标而调参。

## 阶段四验收对照

| 验收项 | 验收线 | 实际值 | 结论 | 说明 |
|---|---:|---:|---|---|
| 期频 MDD | ≤ 25% | **-16.22%** | ✅ PASS | 期频回撤控制达标 |
| 剔除 2021 不劣化 | 阶段三 0.673 基础上不劣化 | **0.722** | ✅ PASS | 0.722 > 0.673 |
| Sharpe | ≥ 1.680 | **1.5527** | ❌ FAIL | 差 **0.127** |
| 日频 MDD | ≤ 25% | **-27.56%** | ❌ FAIL | 超限 **2.56pp** |

> 结论：阶段四完成了验证分析与工程化交付，但验收并非全 PASS。最终总报告必须同时写明两项 FAIL 及根因，禁止用调参结果替代定稿基线。

## 核心绩效对照

| 指标 | 阶段三基线 | 阶段四 M4 最终 | 变化/说明 |
|---|---:|---:|---|
| 期频年化 | 53.69% | **43.49%** | -10.20pp |
| Sharpe | 1.4611 | **1.5527** | +0.0916 |
| 期频 MDD | -21.84% | **-16.22%** | 回撤改善 5.62pp |
| 日频 MDD | — | **-27.56%** | 超验收线 2.56pp |
| 剔除 2021 Sharpe | 0.673 | **0.722** | 不劣化，PASS |

主线策略仍为 `lasso_horizon_all8`：持仓 50 只等权，月度调仓，无前视。阶段四 M4 的定位是“削减部分收益换尾部保护 + 因子平滑增强”，不是追求收益最大化。

## M4 增量拆解

> 口径：顺序法，非正交。M4c 回测已挂载 M4a×M4b 仓位，`m4c_bt_periods` 与 `m4_final_periods` 逐行完全一致（max diff = 0），因此不称 M4c 为独立增量。

| 模块 | Sharpe 变化 | 年化变化 | MDD 变化 | 定位 |
|---|---:|---:|---:|---|
| + 仓位管理（M4a×M4b） | +0.0190 | -11.14pp | 改善 3.58pp | 削减收益换尾部保护 |
| + 因子平滑（M4c） | +0.0727 | +0.93pp | 改善 2.04pp | **三项全正，M4 唯一有效增强模块** |

## 负面结论与过拟合否决

| 方案 | 表面结果 | 否决原因 |
|---|---|---|
| `top_n=25` | 全期 Sharpe 1.717 | 剔除 2021 后仅 **0.683**，判定为行情馈赠，拒绝 |
| M4c 平滑 `K=5` | 全期 Sharpe 1.76 | K 未收敛且换手极低，偏离月度调仓规格，判定为低换手红利，拒绝 |
| 流动性过滤版 | 看似更合规 | Sharpe 从 1.553 降至 **0.746**，说明 alpha 与低流动性小盘高度绑定；应作为独立约束研究，不混入主线验收 |
| 为凑 1.680 调参 | — | **严禁**。阶段四定稿基线为 1.5527，FAIL 必须如实披露 |

## 口径与命名规范

| 事项 | 规范 |
|---|---|
| M4c 正名 | 必须叫 **“因子平滑（前视修正 + 系数/分数双层平滑）”**，绝不能叫“因子轮动”；代码中不存在滚动 IC 重加权 |
| 绩效计算 | 统一对齐 `engine.nav_stats`；年化使用 **n-1 期收益率** |
| 重叠修正 | `m4c_bt_periods` 与 `m4_final_periods` 逐行完全一致（max diff = 0）；表述为“v2 分数在仓位之上叠加”，不称独立增量 |
| 警告处理 | `m3_rebuild_daily_nav.py` 中的 Pandas `FutureWarning` 不影响数值，写入“已知限制”即可，不修 |
| 验收披露 | PASS/FAIL 必须同时列出；不得只写 PASS 项，不得用调参结果替代定稿基线 |

## 已知限制

- Sharpe 未达 1.680，差 **0.127**；在无前视、合规持仓前提下，1.55 是现实上限。
- 日频 MDD 为 **-27.56%**，超验收线 **2.56pp**；月度调仓引擎无法在期内响应急跌，改进需日内止损机制。
- 策略 alpha 高度集中于低流动性小盘股；流动性过滤会显著削减 Sharpe 至 0.746。
- M4c 平滑 `K=5` 未收敛且换手极低，已被否决，不作为交付方案。
- `m3_rebuild_daily_nav.py` 存在 Pandas `FutureWarning`，不影响数值结果。
- 阶段四最终总报告正文尚未定稿；README 中的数字为定稿基线，报告必须同口径引用。

## 快速开始

### 1. 进入项目并激活虚拟环境

```powershell
cd C:\Users\16075\code\multi_factor_lab
.\.venv\Scripts\Activate.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

确认命令行提示符前出现 `(.venv)`。

### 2. 安装项目（可编辑模式）

```powershell
python -m pip install --upgrade pip
pip install -e .
```

### 3. 环境自检

```powershell
git status
python -m pytest
git log --oneline -8
```

### 4. 阶段四一键复现

```powershell
# 在项目根目录执行工程化一键脚本
.\run_all_stage4.ps1
```

已跑通结果：**32 项成功，0 失败**。  
阶段四图表在 `reports/figures/stage4/`，数据表包括 `m5_1c_perf.csv`、`m5_1c_attribution.csv` 等。

### 5. 阶段三历史复现入口

阶段三完整命令见 `docs/stage3_final_report.md` 与 `scripts/backtest/`。主推组关键脚本包括：

```powershell
python scripts\backtest\run_composite_backtest.py
python scripts\backtest\extract_holdings.py --group lasso_horizon_all8
python scripts\backtest\run_backtrader_lasso_horizon_all8_v2.py
```

## 目录结构

```text
multi_factor_lab/
├─ README.md
├─ pyproject.toml
├─ requirements.txt
├─ run_all_stage4.ps1              # 阶段四一键复现脚本
├─ .env                            # Tushare Token（不提交）
├─ data/
│  ├─ raw/
│  └─ processed/
│     ├─ daily_panel_tencent_clean.parquet
│     ├─ financial_panel_pit.parquet
│     ├─ factor_panel_final.parquet
│     ├─ final_factor_list.csv
│     ├─ hs300_benchmark.parquet
│     ├─ rebalance_calendar.csv
│     ├─ composite_bt_summary.csv
│     ├─ composite_holdings_lasso_horizon_all8.csv
│     ├─ bt_vs_self_*_v2.csv
│     ├─ m5_1c_perf.csv            # 阶段四六组绩效对齐表
│     └─ m5_1c_attribution.csv     # 阶段四增量拆解表
├─ docs/
│  ├─ stage1_checklist.md
│  ├─ stage2_final_report.md
│  ├─ stage3_final_report.md
│  ├─ stage4/
│  │  └─ stage4_final_report.md    # 阶段四最终总报告（骨架已建，正文待定稿）
│  └─ figures/stage3/composite_navs.png
├─ reports/
│  └─ figures/
│     └─ stage4/
│        ├─ m1_*.png
│        ├─ m2_*.png
│        ├─ m3_*.png
│        ├─ m4_*.png
│        └─ m5_*.png
├─ scripts/
│  ├─ backtest/
│  ├─ validation/
│  ├─ factors/
│  └─ quality/
├─ src/
│  └─ mfalpha/
└─ tests/
```

> `data/` 目录被 `.gitignore` 忽略；阶段四具体数据文件路径以仓库实际结构为准。

## 数据体系

| 项目 | 结果 |
|---|---|
| 股票池 | 5026 只，成功抓取 **4853 只（96.5%）** |
| 覆盖板块 | 主板 / 创业板 / 科创板 |
| 时间跨度 | 2019-09-30 ~ 2024-09-30，1213 个交易日 |
| 复权 | 腾讯前复权 |
| 退市 / 停牌 | 含退市股，无幸存者偏差；前复权数据不含停牌日 |
| 清洗后面板 | `data/processed/daily_panel_tencent_clean.parquet`，5,088,372 行 × 12 列 |
| 财务数据 | Tushare Pro；PIT 对齐后 `financial_panel_pit.parquet`，5,088,372 行 × 6 列 |
| 质量报告 | `docs/reports/data_quality_report_tencent.md`，单字段缺失率 < 2% |

## 因子库

### 基础因子（阶段一，18 个）

价量 7 + 技术 4 + 财务 4 + 估值 2 + 换手 1。完整清单见 `docs/stage1_checklist.md` 与 `data/processed/factor_panel.parquet`。

### 最终因子库（阶段二，8 个纯 alpha 因子）

方向已统一为“值越大 → 预期收益越高”：

| 因子 | 类别 | 方向翻转 | 20D IC（统一后） |
|---|---|---:|---:|
| `turnover` | 核心稳健 | ✅ | +0.105 |
| `volatility_20` | 待观察 | ✅ | +0.095 |
| `bp` | 进攻型 | 保持 | +0.081 |
| `amihud_20` | 核心稳健 | 保持 | +0.076 |
| `ep_ttm` | 进攻型 | 保持 | +0.058 |
| `reversal_20` | 防御型 | 保持 | +0.054 |
| `corr_pv_20` | 防御型 | ✅ | +0.048 |
| `bias_20` | 防御型 | ✅ | +0.047 |

## 阶段三历史绩效

阶段三主推策略为 `lasso_horizon_all8`。完整 10 组绩效见 `docs/stage3_final_report.md` 与 `data/processed/composite_bt_summary.csv`。关键对照如下：

| 组 | 年化 | Sharpe | MDD | 说明 |
|---|---:|---:|---:|---|
| `lasso_all8` | +68.36% | 1.750 | -21.91% | 旧 t+1 标签，含前视，仅作对照 |
| **`lasso_horizon_all8`** | **+53.69%** | **1.461** | **-21.84%** | 阶段三主推，无前视 |
| `ic_no_vol` | +47.02% | 1.345 | -21.80% | 线性基准 |

同期沪深 300 年化：**-2.88%**。  
剔除 2021 后，`lasso_horizon_all8` 阶段三 Sharpe 由 1.461 降至 **0.673**，年化仍有 **+18.81%**；阶段四 M4 最终剔除 2021 Sharpe 为 **0.722**，满足“不劣化”验收。

## Backtrader 交叉验证

| 指标 | 结果 | 验收要求 |
|---|---:|---|
| 净值相关系数（三组） | **1.0000** | > 0.95 |
| 年化收益差（三组） | **≤ 0.13%** | < 2% |

三组明细：

| 组 | net 年化差 | 相关系数 |
|---|---:|---:|
| `lasso_all8` | +0.13% | 1.0000 |
| `lasso_horizon_all8` | +0.11% | 1.0000 |
| `ic_no_vol` | +0.05% | 1.0000 |

> Backtrader 仅作为交叉验证，主引擎是自研事件驱动引擎。

## 关键产物文件

### 阶段四

| 文件 | 说明 |
|---|---|
| `docs/stage4/stage4_final_report.md` | 阶段四最终总报告；骨架已建，正文待定稿 |
| `run_all_stage4.ps1` | 阶段四一键复现脚本；已跑通 32 项成功、0 失败 |
| `m5_1c_perf.csv` | 阶段四六组绩效对齐表 |
| `m5_1c_attribution.csv` | 阶段四 M4 增量拆解表 |
| `reports/figures/stage4/m1_*.png` ~ `m5_*.png` | 阶段四 M1–M5 图表，共十几张 |
| `m4c_bt_periods` / `m4_final_periods` | 逐行完全一致（max diff = 0），用于证明 M4c 已挂载仓位 |
| `m3_rebuild_daily_nav.py` | 日频净值重建脚本；存在 Pandas `FutureWarning`，不影响数值 |

### 阶段一 / 二 / 三

| 文件 | 说明 |
|---|---|
| `data/processed/factor_panel_final.parquet` | 阶段二最终 8 因子面板，5,045,205 × 8，方向已统一 |
| `data/processed/composite_bt_summary.csv` | 阶段三 10 组绩效汇总 |
| `data/processed/composite_holdings_lasso_horizon_all8.csv` | 主推组持仓 |
| `data/processed/bt_vs_self_*_v2.csv` | Backtrader v2 对账结果 |
| `docs/stage3_final_report.md` | 阶段三最终报告 v1.1 |

## 阶段进度

| 阶段 | 状态 | 验收结论 |
|---|---|---|
| 阶段一：数据与因子库 | ✅ 已验收 | 4853 只，18 因子，缺失率 < 2% |
| 阶段二：检验、中性化、稳健性 | ✅ 已验收 | 8 因子，VIF 达标，三种市场状态显著 |
| 阶段三：合成与回测 | ✅ 已完成 | 超额 +57.02%，Sharpe 1.461，BT 误差 ≤ 0.13% |
| 阶段四 M0–M5：验证分析 | ✅ 已完成 | 2 PASS / 2 FAIL，FAIL 项已定位根因 |
| 阶段四 M7：工程化 | ✅ 已完成 | 一键脚本 32 成功、0 失败 |
| 阶段四最终总报告 | ⏳ 撰写中 | 需整合 M1–M5 结论，如实披露 FAIL |

## 开发与维护约定

- Commit 消息使用中文，遵循 Conventional Commits：`feat` / `fix` / `chore` / `docs` / `refactor` / `test`。
- 财务数据必须按 `ann_date` 做 PIT 对齐。
- 合成权重必须“滚动到时点”，禁止使用全样本统计量。
- Lasso 按时间切训练 / 验证，禁止随机打散。
- 事件驱动引擎必须遵守“信号用当日、成交在信号之后”。
- 绩效指标自实现 + 单测，不用第三方黑盒；Backtrader 仅作交叉验证。
- **阶段四新增约定**：
  - 绩效统一对齐 `engine.nav_stats`，年化用 n-1 期收益率。
  - M4c 必须正名为“因子平滑（前视修正 + 系数/分数双层平滑）”，禁止写成“因子轮动”。
  - M4c 表述为“v2 分数在仓位之上叠加”，不称独立增量。
  - `m3_rebuild_daily_nav.py` 的 Pandas `FutureWarning` 写入已知限制，不修。
  - **严禁为了凑 1.680 或日频 MDD 目标而调参**；FAIL 项必须如实披露。
- README 是活文档：每完成一个里程碑，更新“当前状态”“阶段进度”“关键产物文件”和“最后更新”。

## 常见问题

| 问题 | 解决 |
|---|---|
| `ModuleNotFoundError: mfalpha` | 在项目根目录执行 `pip install -e .` |
| PowerShell 看 UTF-8 文件乱码 | 先执行 `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` |
| Tushare 报“IP 数量超限” | 切换手机热点或家庭宽带，避免校园网共享出口 IP |
| `pe_ttm` 缺失率较高 | 亏损公司 PE 无意义，改用 `ep_ttm`，负值归 NaN |
| Backtrader 与自研引擎误差 > 2% | 逐级对账：先比持仓，再比单笔，最后比净值；优先检查 `TimeReturn` 口径与 `order_target_percent` 估值时点 |
| Lasso 期数与线性组不对齐 | 直接读线性组 index，确保 52 期严格对齐 |
| flake8 报 E501 行过长 | 手动折行，或先跑 `pre-commit run --files <file>` 让 black 自动折行后再提交 |
| 阶段四脚本是否全部成功 | 以 `run_all_stage4.ps1` 输出为准；当前记录为 32 成功、0 失败 |

## 下一步计划

1. 完成 `docs/stage4/stage4_final_report.md` 正文定稿，整合 M1–M5 全部结论。
2. 在最终报告中固定披露：Sharpe 1.5527 未达 1.680，日频 MDD -27.56% 超限 2.56pp。
3. 如未来要改进日频 MDD，需引入日内止损/风险控制机制，属于新引擎设计，不在当前月度调仓引擎内“调参解决”。
4. 流动性约束版应作为独立研究，不混入主线验收；其 Sharpe 降至 0.746 的事实必须保留。
5. 可选历史优化方向：交易成本敏感性、双月调仓、Lasso 系数滚动稳定性、分行业/市值归因、horizon 敏感性网格。