
```markdown
# multi_factor_lab

> A 股多因子选股策略实习项目  
> 核心流程：**数据获取 → 因子库 → 检验中性化 → 合成 → 回测 → 交叉验证 → 归因**  
> 当前阶段：**阶段一 ✅ | 阶段二 ✅ | 阶段三 ✅ 收尾（M0–M8 全部完成）**  
> 最优策略：**`lasso_horizon_all8`**（持有期标签，无前视），年化 **+53.69%**，Sharpe **1.461**，超额 **+57.02%**  
> 最后更新：2026-10-22

---

## 目录

- [项目简介](#项目简介)
- [当前状态](#当前状态)
- [阶段三核心成果](#阶段三核心成果)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [数据体系](#数据体系)
- [因子库](#因子库)
- [阶段二核心结论](#阶段二核心结论)
- [阶段三完成情况（M0–M8）](#阶段三完成情况m0m8)
- [10 组策略绩效](#10-组策略绩效)
- [Backtrader 交叉验证](#backtrader-交叉验证)
- [关键产物文件](#关键产物文件)
- [常用命令](#常用命令)
- [阶段进度](#阶段进度)
- [子目录 README 索引](#子目录-readme-索引)
- [开发规范](#开发规范)
- [常见问题](#常见问题)
- [下一步计划](#下一步计划)
- [维护约定](#维护约定)

## 项目简介

`multi_factor_lab` 是一个 A 股多因子选股策略实习项目，目标是从数据获取、因子构建、因子检验与中性化，到因子合成、事件驱动回测、独立引擎交叉验证与归因，形成一套可复现、可测试、可扩展的多因子研究流程。

- GitHub：https://github.com/DustUniverse/multi_factor_lab
- 本地路径：`C:\Users\16075\code\multi_factor_lab`
- 开发环境：Windows + VS Code + PowerShell
- 虚拟环境：`.venv`，Python 3.12
- 包管理：`pip install -e .`（可编辑安装）
- 关键依赖：`pandas`、`numpy`、`scikit-learn 1.9.1`、`backtrader 1.9.78.123`

## 当前状态

| 模块 | 状态 | 说明 |
|---|---|---|
| 数据体系 | ✅ 已验收 | 4853 只股票，2019-09-30 ~ 2024-09-30，1213 个交易日 |
| 基础因子库 | ✅ 18 / 18 | 价量 7 + 技术 4 + 财务 4 + 估值 2 + 换手 1 |
| 阶段一验收 | ✅ 通过 | `docs/stage1_checklist.md` |
| 阶段二 M0–M7 | ✅ 全部完成 | IC 检验 → 分层 → 中性化 → VIF 剔除 → 稳健性 → 最终因子库 → 报告 |
| 最终因子库 | ✅ 8 因子 | `data/processed/factor_panel_final.parquet`，5,045,205 × 8，方向已统一 |
| 阶段二验收 | ✅ 全部达标 | `docs/stage2_final_report.md`（353 行完整报告） |
| 阶段三 M0–M8 | ✅ 全部完成 | 基准与日历 → 线性合成 → Lasso（含持有期标签） → 10 组回测 → Backtrader v2 交叉验证 → 最终报告 |
| 阶段三验收 | ✅ 全部达标 | 超额 +57.02%、Sharpe 1.461、BT 相关系数 1.0000、年化差 ≤ 0.13% |
| 阶段三最终报告 | ✅ 已完成 | `docs/stage3_final_report.md`（v1.1） |
| 单元测试 | ✅ 阶段一/二基线 59 passed | 阶段三新增测试以 `python -m pytest` 实际输出为准 |

## 阶段三核心成果

1. **主推策略切换为无前视的 `lasso_horizon_all8`**  
   原 `lasso_all8` 使用 t+1 标签，存在前视偏差（年化虚高约 14.7pp），仅作对照。新策略改用持有期标签，训练集严格早于预测期，全周期年化 **+53.69%**、Sharpe **1.461**、最大回撤 **-21.84%**、Calmar **2.459**、超额年化 **+57.02%**。

2. **Backtrader 交叉验证 v2 口径通过**  
   修正 `TimeReturn` close-to-close 与自研 open-to-open 的口径错位、`order_target_percent` 用昨日 close 估值导致的系统性少买、`rets.dropna()` 丢弃停牌股收益三层问题后，三组（`lasso_all8` / `lasso_horizon_all8` / `ic_no_vol`）净值相关系数均为 **1.0000**，net 年化差分别 **+0.13% / +0.11% / +0.05%**，远优于"相关系数 > 0.95、年化差 < 2%"的验收线。

3. **10 组策略绩效完整出炉**  
   在 8 组线性 + 旧 Lasso 基础上，新增持有期标签版本 2 组（`lasso_horizon_all8`、`lasso_horizon_no_vol`）。主推组 `lasso_horizon_all8`：年化 **+53.69%**、Sharpe **1.461**、最大回撤 **-21.84%**、Calmar **2.459**、超额 **+57.02%**。同期沪深 300 年化 **-2.88%**。

4. **稳健性验证**  
   剔除 2021 大牛市后，主推策略 Sharpe 由 1.461 降至 **0.673**、年化由 +53.69% 降至 **+18.81%**，显著高于沪深 300 的 -2.88%，基础 alpha 仍成立。2024 年回撤 -20.79%，是主推策略需重点披露的风险点。

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

### 4. 阶段三完整复现流程

```powershell
# M1：下载沪深300基准 + 构建调仓日历
python scripts\backtest\fetch_hs300.py
python scripts\backtest\build_rebalance_calendar.py

# M2-prep：计算日频 IC
python scripts\backtest\compute_daily_ic.py

# M2a：线性因子合成（6 组）
python scripts\backtest\composite_factors.py

# M2a-Lasso：Lasso 非线性合成（2 组，旧 t+1 标签）
python scripts\backtest\composite_factors_lasso.py

# M2a-Horizon：持有期标签 Lasso 合成（2 组，无前视）
python scripts\backtest\composite_factors_lasso_horizon.py

# M5b：10 组组合回测
python scripts\backtest\run_composite_backtest.py

# M7-a：提取持仓
python scripts\backtest\extract_holdings.py --group lasso_horizon_all8

# M7-b：Backtrader v2 交叉验证（三组）
python scripts\backtest\run_backtrader_lasso_all8_v2.py
python scripts\backtest\run_backtrader_lasso_horizon_all8_v2.py
python scripts\backtest\run_backtrader_ic_no_vol_v2.py

# 分年度收益与剔除 2021 Sharpe
python scripts\backtest\diag_year_sharpe.py
```

## 目录结构

```text
multi_factor_lab/
├─ README.md
├─ pyproject.toml
├─ requirements.txt
├─ .env                          # Tushare Token（不提交）
├─ .gitignore
├─ data/
│  ├─ raw/
│  └─ processed/
│     ├─ daily_panel_tencent_clean.parquet
│     ├─ financial_panel_pit.parquet
│     ├─ factor_panel.parquet
│     ├─ factor_panel_selected.parquet
│     ├─ factor_panel_final.parquet
│     ├─ final_factor_list.csv
│     ├─ market_regime.csv
│     ├─ regime_ic_summary.csv
│     ├─ sector_ic_summary.csv
│     ├─ size_ic_summary.csv
│     ├─ hs300_benchmark.parquet
│     ├─ rebalance_calendar.csv
│     ├─ factor_ic_daily_1d.parquet
│     ├─ composite_scores_{ic|ir|equal|lasso}_{all8|no_vol}.parquet
│     ├─ composite_scores_lasso_horizon_{all8|no_vol}.parquet
│     ├─ composite_weights_{ic|ir|equal|lasso}_{all8|no_vol}.csv
│     ├─ composite_weights_lasso_horizon_{all8|no_vol}.csv
│     ├─ composite_bt_{group}.csv                 # 10 组逐期收益
│     ├─ composite_bt_summary.csv
│     ├─ composite_holdings_lasso_horizon_all8.csv
│     ├─ bt_vs_self_{lasso_all8|lasso_horizon_all8|ic_no_vol}_v2.csv
│     └─ stage2_monthly_recompute.csv
├─ docs/
│  ├─ README.md
│  ├─ stage1_checklist.md
│  ├─ stage2_final_report.md
│  ├─ stage3_final_report.md                # v1.1
│  ├─ figures/stage3/composite_navs.png
│  └─ reports/data_quality_report_tencent.md
├─ scripts/
│  ├─ README.md
│  ├─ data/
│  ├─ quality/
│  ├─ factors/
│  ├─ validation/
│  ├─ backtest/                  # 阶段三主脚本目录
│  │  └─ diag/                   # 诊断脚本归档
│  ├─ attribution/               # 数据源探测脚本
│  └─ probe/
├─ src/
│  └─ mfalpha/
│     ├─ README.md
│     ├─ data/pit_align.py
│     ├─ factors/
│     └─ ...
└─ tests/
   └─ README.md
```

## 数据体系

| 项目 | 结果 |
|---|---|
| 股票池 | 5026 只，成功抓取 **4853 只（96.5%）** |
| 覆盖板块 | 主板 / 创业板 / 科创板 |
| 时间跨度 | 2019-09-30 ~ 2024-09-30，1213 个交易日 |
| 复权 | 腾讯前复权 |
| 退市 / 停牌 | 含退市股，无幸存者偏差；前复权数据不含停牌日 |
| 清洗后面板 | `data/processed/daily_panel_tencent_clean.parquet`，5,088,372 行 × 12 列 |
| 财务数据 | Tushare Pro；PIT 对齐后 `data/processed/financial_panel_pit.parquet`，5,088,372 行 × 6 列 |
| 质量报告 | `docs/reports/data_quality_report_tencent.md`，单字段缺失率 < 2% |

## 因子库

### 基础因子（阶段一，18 个）

| 类别 | 数量 | 因子 |
|---|---:|---|
| 价量类 | 7 | `momentum_20`、`reversal_20`、`volatility_20`、`corr_pv_20`、`volume_ratio`、`amplitude_20`、`amihud_20` |
| 技术类 | 4 | `rsi_14`（Wilder 平滑）、`bias_20`、`boll_dev_20`、`macd_dev`（已归一化） |
| 财务类 | 4 | `roe`、`netprofit_yoy`、`or_yoy`、`debt_to_assets`（PIT 对齐） |
| 估值类 | 2 | `ep_ttm`（1/PE_TTM）、`bp`（1/PB） |
| 换手类 | 1 | `turnover`（来自 Tushare `daily_basic`） |
| **合计** | **18** | — |

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

## 阶段二核心结论

| 环节 | 关键结论 |
|---|---|
| M2 IC 检验 | 20D 口径下 12 个因子通过初筛 |
| M3 分层回测 | `turnover` 多空夏普 8.12、`amihud_20` 7.86 |
| M4 中性化 | ICIR 全部改善，`turnover` Sharpe → 14.04 |
| M5 VIF 剔除 | 迭代 4 轮，最终保留 8 因子，`vif_mean < 5`、`vif_median < 4` |
| M6 稳健性 | bull 32.1% / flat 51.6% / bear 16.2%；8 因子三状态下全部显著；7/8 因子跨板块符号一致 |
| M7 补检 | \|β\|<0.02、R²<0.05；1D/5D/20D × 三状态全部显著；发现“小盘 alpha”；`ep_ttm` 跨市值均匀 |

## 阶段三完成情况（M0–M8）

| 里程碑 | 内容 | 状态 | 关键产物 |
|---|---|---|---|
| M0 | 环境与数据确认 | ✅ | 工作区干净、关键文件齐全 |
| M1 | 基准与交易日历准备 | ✅ | `hs300_benchmark.parquet`、`rebalance_calendar.csv` |
| M2 | 线性因子合成（6 组） | ✅ | `composite_scores_{ic|ir|equal}_{all8|no_vol}.parquet` |
| M2a-Lasso | Lasso 非线性合成（2 组，旧 t+1 标签） | ✅ | `composite_scores_lasso_{all8|no_vol}.parquet` |
| M2a-Horizon | 持有期标签 Lasso 合成（2 组，无前视） | ✅ | `composite_scores_lasso_horizon_{all8|no_vol}.parquet` |
| M5a | 单因子对账 / 月频修正 | ✅ | `stage2_monthly_recompute.csv` |
| M5b | 10 组组合回测 | ✅ | `composite_bt_summary.csv` |
| M7-a | 提取持仓 | ✅ | `composite_holdings_lasso_horizon_all8.csv` |
| M7-b | Backtrader v2 交叉验证（三组） | ✅ | `bt_vs_self_*_v2.csv`，相关系数均 1.0000 |
| M8 | 阶段三最终报告 | ✅ | `docs/stage3_final_report.md`（v1.1） |

**最终验收指标**：年化超额 **≥ 8%**（实际 +57.02%），Sharpe **≥ 1.2**（实际 1.461），Backtrader 误差 **< 2%**（实际 ≤ 0.13%），全部达成。

## 10 组策略绩效

数据源：`data/processed/composite_bt_summary.csv`

| 组 | 年化 | Sharpe | MDD | Calmar | 胜率 | 盈亏比 | 超额 |
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

同期沪深 300 年化：**-2.88%**。

### 分年度收益

| 年份 | `lasso_all8` | `lasso_horizon_all8` | `ic_no_vol` |
|---|---:|---:|---:|
| 2020（部分） | +57.25% | +42.40% | +41.31% |
| 2021 | +275.49% | +247.28% | +204.94% |
| 2022 | +15.49% | +18.90% | +5.64% |
| 2023 | +34.61% | +28.70% | +18.54% |
| 2024（部分） | -4.54% | -20.79% | -7.67% |

### 剔除 2021 大牛市后的稳健性

| 组 | 全周期 Sharpe | 剔除 2021 后 Sharpe | 全周期年化 | 剔除 2021 年化 |
|---|---:|---:|---:|---:|
| `lasso_all8` | 1.750 | 0.983 | +68.36% | +30.68% |
| **`lasso_horizon_all8`** | **1.461** | **0.673** | **+53.69%** | **+18.81%** |
| `ic_no_vol` | 1.345 | 0.650 | +47.02% | +16.77% |

结论：主推策略剔除 2021 后年化仍有 **+18.81%**，显著高于沪深 300 的 -2.88%，基础 alpha 成立；但 Sharpe 降幅 53.9%，对 2021 年依赖较重，是主要风险点。

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

关键脚本：`run_backtrader_{lasso_all8|lasso_horizon_all8|ic_no_vol}_v2.py`  
输出：`data/processed/bt_vs_self_*_v2.csv`

v1 遗留问题与 v2 修复：

| 层 | v1 根因 | v2 修复 |
|---|---|---|
| 1 | `TimeReturn` 是 close-to-close，自研是 open-to-open | 记录调仓日 open 时（调仓前）组合价值，算 open-to-open 收益 |
| 2 | `order_target_percent` 用昨日 close 估目标金额，跳空导致系统性少买（仓位仅 95.5%） | 改用今日 open 估值总价值手动算股数，`order_target_size` 下单 |
| 3 | `rets.dropna()` 丢弃停牌股收益 | 缺价股用“next_trade 前最后一个可用 open”填充，与 BT 的 ffill 口径一致 |

## 关键产物文件

### 阶段一 / 二

| 文件 | 说明 |
|---|---|
| `data/processed/factor_panel.parquet` | 18 基础因子面板，5,088,372 × 20 |
| `data/processed/factor_panel_final.parquet` | 阶段二最终 8 因子面板，5,045,205 × 8，MultiIndex，方向已统一 |
| `data/processed/final_factor_list.csv` | 阶段二最终因子清单 |
| `data/processed/market_regime.csv` | 市场状态序列（bull / flat / bear） |
| `data/processed/regime_ic_summary.csv` | 分市场状态 IC 汇总 |
| `data/processed/sector_ic_summary.csv` | 分上市板块 IC 汇总 |
| `data/processed/size_ic_summary.csv` | 分市值 IC 汇总 |
| `docs/stage2_final_report.md` | 阶段二完整报告，353 行 |

### 阶段三

| 文件 | 里程碑 | 说明 |
|---|---|---|
| `data/processed/hs300_benchmark.parquet` | M1 | 沪深 300 日线基准 |
| `data/processed/rebalance_calendar.csv` | M1 | 月度调仓日列表，52 期 |
| `data/processed/factor_ic_daily_1d.parquet` | M2-prep | 日频因子 IC |
| `data/processed/composite_scores_{ic|ir|equal|lasso}_{all8|no_vol}.parquet` | M2 / M2a-Lasso | 8 组合成得分 |
| `data/processed/composite_scores_lasso_horizon_{all8|no_vol}.parquet` | M2a-Horizon | 2 组持有期标签合成得分 |
| `data/processed/composite_weights_{ic|ir|equal|lasso}_{all8|no_vol}.csv` | M2 / M2a-Lasso | 8 组合成权重 |
| `data/processed/composite_weights_lasso_horizon_{all8|no_vol}.csv` | M2a-Horizon | 2 组持有期权重 |
| `data/processed/composite_bt_{group}.csv` | M5b | 10 组逐期回测明细 |
| `data/processed/composite_bt_summary.csv` | M5b | 10 组绩效汇总 |
| `data/processed/composite_holdings_lasso_horizon_all8.csv` | M7-a | 主推组持仓 |
| `data/processed/bt_vs_self_{lasso_all8|lasso_horizon_all8|ic_no_vol}_v2.csv` | M7-b | 三组 v2 对账结果 |
| `data/processed/stage2_monthly_recompute.csv` | M5a | 单因子月频修正 |
| `docs/stage3_final_report.md` | M8 | 阶段三最终报告 v1.1 |
| `docs/figures/stage3/composite_navs.png` | M8 | 10 组 + 沪深 300 净值曲线 |

## 常用命令

```powershell
# 运行测试
python -m pytest

# 代码格式化
python -m black .
python -m isort .

# 静态检查
python -m flake8 .

# 导出依赖
python -m pip freeze | Out-File -Encoding ascii requirements.txt

# 查看 Git 状态
git status
git log --oneline -8
```

## 阶段进度

### 阶段一：数据与因子库（已验收 ✅）

| 验收标准 | 状态 |
|---|---|
| 数据覆盖沪深全市场 A 股 | ✅ 4853 只（96.5%） |
| 5 年时间跨度完整 | ✅ 2019-09-30 ~ 2024-09-30 |
| 单字段缺失率 < 2% | ✅ |
| 一键生成全量因子面板 | ✅ |
| ≥ 18 个基础因子 | ✅ 18 个 |
| 单元测试 | ✅ 59 passed（阶段一/二基线） |
| 阶段一验收表 | ✅ `docs/stage1_checklist.md` |

### 阶段二：检验、中性化、稳健性（已验收 ✅）

| 验收标准 | 结果 | 状态 |
|---|---|---|
| IC\|≥0.03、IR≥0.3 的有效因子 ≥ 8 | 8 个 | ✅ |
| 因子 VIF < 5 | 全部达标 | ✅ |
| 中性化后市值 / 行业暴露 ≈ 0 | \|β\|<0.02、R²<0.05 | ✅ |
| 有效因子 ≥2 种环境显著 | 3 种环境全部显著 | ✅ 超额 |
| 稳健性覆盖 ≥3 种环境 | bull / flat / bear | ✅ |
| 报告含完整统计 + 图表 | 353 行 Markdown | ✅ |

### 阶段三：合成与回测（已完成 ✅）

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M0 | 环境与数据确认 | ✅ |
| M1 | 基准与交易日历准备 | ✅ |
| M2 | 线性因子合成（6 组） | ✅ |
| M2a-Lasso | Lasso 非线性合成（2 组，旧 t+1 标签） | ✅ |
| M2a-Horizon | 持有期标签 Lasso 合成（2 组，无前视） | ✅ |
| M5a | 单因子对账 / 月频修正 | ✅ |
| M5b | 10 组组合回测 | ✅ |
| M7-a | 提取持仓 | ✅ |
| M7-b | Backtrader v2 交叉验证（三组） | ✅ 相关系数均 1.0000，年化差 ≤ 0.13% |
| M8 | 最终报告与交付物 | ✅ `docs/stage3_final_report.md`（v1.1） |

**最终验收指标**：年化超额 **≥ 8%**（实际 +57.02%），Sharpe **≥ 1.2**（实际 1.461），BT 误差 **< 2%**（实际 ≤ 0.13%），全部达成。

## 子目录 README 索引

| 目录 | README | 内容 |
|---|---|---|
| `docs/` | [docs/README.md](docs/README.md) | 阶段验收表、质量报告、阶段三最终报告索引 |
| `scripts/` | [scripts/README.md](scripts/README.md) | 数据、质量、因子、检验、合成、回测脚本说明 |
| `src/mfalpha/` | [src/mfalpha/README.md](src/mfalpha/README.md) | 核心包结构、PIT 对齐、因子模块约定 |
| `tests/` | [tests/README.md](tests/README.md) | 单元测试运行方式与覆盖范围 |

> `data/` 目录被 `.gitignore` 忽略，不建议在仓库中维护 `data/README.md`。

## 开发规范

- Commit 消息使用中文，遵循 Conventional Commits：`feat` / `fix` / `chore` / `docs` / `refactor` / `test`。
- 因子模块风格：单股票 `pd.Series` 输入，`window` 参数，返回等长 `Series`。
- 财务数据必须按 `ann_date` 做 PIT 对齐。
- Tushare 批量拉取必须在干净 IP 下进行，校园网可能触发 IP 限制。
- 不提交 `.env`、`.venv/`、根目录 `/data/`、`*.parquet`、`*.egg-info/`。
- **阶段三新增**：
  - 合成权重必须“滚动到时点”，禁止使用全样本统计量。
  - Lasso 按时间切训练 / 验证，禁止随机打散。
  - 事件驱动引擎必须遵守“信号用当日、成交在信号之后”。
  - 绩效指标自实现 + 单测，不用第三方黑盒。
  - Backtrader 仅作为**交叉验证**，主引擎是自研的那一套。

## 常见问题

| 问题 | 解决 |
|---|---|
| `ModuleNotFoundError: mfalpha` | 在项目根目录执行 `pip install -e .` |
| PowerShell 看 UTF-8 文件乱码 | 先执行 `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` |
| Tushare 报“IP 数量超限” | 切换手机热点或家庭宽带，避免校园网共享出口 IP |
| `pe_ttm` 缺失率较高 | 亏损公司 PE 无意义，改用 `ep_ttm`，负值归 NaN |
| `alphalens` 安装 / 维护问题 | 使用 `alphalens-reloaded` |
| `peewee` 在 Python 3.12 编译失败 | 先安装 `peewee>=3.17.5`，再安装 `alphalens-reloaded` |
| `pd.Timedelta(days=365)` 触发 `DeprecationWarning` | 改用 `pd.DateOffset(days=365)` |
| `np.percentile([])` 报 `IndexError` | 调用前判断 `len(valid) == 0` |
| VS Code 弹“content is newer” | 点 **Overwrite**，再手动跑 black + flake8 后重新 commit |
| flake8 报 F541 | f-string 无占位符，手动去掉 `f` 前缀 |
| Backtrader 与自研引擎误差 > 2% | 逐级对账：先比持仓，再比单笔，最后比净值；优先检查 `TimeReturn` 口径与 `order_target_percent` 估值时点 |
| Backtrader `next_open` 触发天数少 | 加日历 feed 作为 `datas[0]`；每只票 reindex + ffill/bfill |
| symbol int vs str 静默不匹配 | 统一 `astype(str).str.zfill(6)` |
| Lasso 期数与线性组不对齐 | 直接读线性组 index，确保 52 期严格对齐 |
| flake8 报 E501 行过长 | 手动折行，或先跑 `pre-commit run --files <file>` 让 black 自动折行后再提交 |

## 下一步计划

阶段三已收尾。可选优化方向：

1. 行业 / 市值中性约束版。
2. XGBoost 非线性合成（任务书写“Lasso 或 XGBoost”，Lasso 已完成）。
3. 交易成本敏感性：0.4% → 0.8%。
4. 双月调仓。
5. Lasso 系数滚动稳定性图。
6. 分行业、分市值收益归因。
7. horizon 敏感性网格（h=5/10/20）。

待带教确认：

- Backtrader 对账精度（相关系数 > 0.95、年化差 < 2%）是否足够。
- 是否需要补 XGBoost 版。
- 报告格式（Markdown / Word / 公司模板）。

## 维护约定

README 是项目的活文档，必须始终更新。

- 根 `README.md`：维护项目总览、当前状态、快速开始、因子清单、阶段进度、子目录索引。
- 子目录 `README.md`：维护该目录的详细说明，避免根 README 过长。
- 每完成一个里程碑（M0–M8）：更新“当前状态”“阶段进度”“关键产物文件”和“最后更新”。
- 每次新增脚本或报告：在对应子 README 中登记，并在根 README 索引中确认链接有效。
```

---
