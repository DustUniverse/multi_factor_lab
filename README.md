# multi_factor_lab

> A 股多因子选股策略实习项目  
> 核心流程：**数据获取 → 因子库 → 检验中性化 → 回测 → 归因**  
> 当前阶段：**阶段一 ✅ | 阶段二 ✅ | 阶段三 🚧 进行中（M0–M8）**  
> 最后更新：2026-10-11

---

## 目录

- [项目简介](#项目简介)
- [当前状态](#当前状态)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [数据体系](#数据体系)
- [因子库](#因子库)
- [阶段二核心结论](#阶段二核心结论)
- [阶段三计划（M0–M8）](#阶段三计划m0m8)
- [阶段三硬性规范](#阶段三硬性规范)
- [关键产物文件](#关键产物文件)
- [常用命令](#常用命令)
- [阶段进度](#阶段进度)
- [子目录 README 索引](#子目录-readme-索引)
- [开发规范](#开发规范)
- [常见问题](#常见问题)
- [下一步计划](#下一步计划)
- [维护约定](#维护约定)

## 项目简介

`multi_factor_lab` 是一个 A 股多因子选股策略实习项目，目标是从数据获取、因子构建、因子检验与中性化，到回测与归因，形成一套可复现、可测试、可扩展的多因子研究流程。

- GitHub：https://github.com/DustUniverse/multi_factor_lab
- 本地路径：`C:\Users\16075\code\multi_factor_lab`
- 开发环境：Windows + VS Code + PowerShell
- 虚拟环境：`.venv`，Python 3.12
- 包管理：`pip install -e .`（可编辑安装）
- 最新 commit（阶段二）：`b9f07e0`（M7-S5 阶段二最终报告）

## 当前状态

| 模块 | 状态 | 说明 |
|---|---|---|
| 数据体系 | ✅ 已验收 | 4853 只股票，2019-09-30 ~ 2024-09-30，1213 个交易日 |
| 基础因子库 | ✅ 18 / 18 | 价量 7 + 技术 4 + 财务 4 + 估值 2 + 换手 1 |
| 阶段一验收 | ✅ 通过 | `docs/stage1_checklist.md` |
| 阶段二 M0–M7 | ✅ 全部完成 | IC 检验 → 分层 → 中性化 → VIF 剔除 → 稳健性 → 最终因子库 → 报告 |
| 最终因子库 | ✅ 8 因子 | `data/processed/factor_panel_final.parquet`，5,045,205 × 8，方向已统一 |
| 阶段二验收 | ✅ 全部达标 | `docs/stage2_final_report.md`（353 行完整报告） |
| 单元测试 | ✅ 59 passed | `python -m pytest` |
| 阶段三 M0–M8 | 🚧 进行中 | 因子合成（线性 + 非线性）→ 自研事件驱动回测 → Backtrader 交叉验证 → 报告 |

## 快速开始

### 1. 进入项目并激活虚拟环境

```powershell
cd C:\Users\16075\code\multi_factor_lab
.\.venv\Scripts\Activate.ps1
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

期望结果：

- 工作区干净，与 `origin/main` 同步；
- `59 passed`；
- 最新 commit 是 `b9f07e0`（阶段二）。

### 4. 确认关键数据文件存在

```powershell
Test-Path data\processed\factor_panel_final.parquet
Test-Path data\processed\final_factor_list.csv
Test-Path data\processed\market_regime.csv
Test-Path docs\stage2_final_report.md
```

期望：全部 `True`。

## 目录结构

```text
multi_factor_lab/
├─ README.md                     # 项目总览与索引
├─ pyproject.toml
├─ requirements.txt
├─ .env                          # Tushare Token（不提交）
├─ .gitignore
├─ data/                         # 数据目录（不提交）
│  ├─ raw/
│  └─ processed/
│     ├─ daily_panel_tencent_clean.parquet
│     ├─ financial_panel_pit.parquet
│     ├─ factor_panel.parquet              # 18 基础因子
│     ├─ factor_panel_selected.parquet     # 阶段二初筛后
│     ├─ factor_panel_final.parquet        # 阶段二最终 8 因子
│     ├─ final_factor_list.csv
│     ├─ market_regime.csv
│     ├─ regime_ic_summary.csv
│     ├─ sector_ic_summary.csv
│     ├─ size_ic_summary.csv
│     ├─ hs300_benchmark.parquet           # 阶段三 M1：沪深 300 日线
│     ├─ rebalance_calendar.csv            # 阶段三 M1：月度调仓日
│     ├─ composite_equal.parquet           # 阶段三 M2：等权合成
│     ├─ composite_ic.parquet              # 阶段三 M2：IC 加权
│     ├─ composite_icir.parquet            # 阶段三 M2：ICIR 加权
│     ├─ composite_lasso.parquet           # 阶段三 M3：Lasso
│     └─ composite_xgb.parquet             # 阶段三 M3：XGBoost
├─ docs/
│  ├─ README.md
│  ├─ stage1_checklist.md
│  ├─ stage2_final_report.md
│  ├─ stage3_final_report.md               # 阶段三 M8：最终报告
│  └─ reports/
│     └─ data_quality_report_tencent.md
├─ scripts/
│  ├─ README.md
│  ├─ data/
│  ├─ quality/
│  ├─ factors/
│  ├─ validation/                # 阶段二：检验、中性化、稳健性
│  ├─ composite/                 # 阶段三 M1–M3：基准、日历、因子合成
│  ├─ backtest/                  # 阶段三 M4–M7：交易规则、回测、对账
│  └─ probe/
├─ src/
│  └─ mfalpha/
│     ├─ README.md
│     ├─ data/
│     │  └─ pit_align.py
│     ├─ factors/
│     ├─ composite/              # 阶段三：合成方法
│     └─ backtest/               # 阶段三：引擎、交易规则、指标
│        ├─ engine.py
│        ├─ tradable_filter.py
│        ├─ metrics.py
│        └─ backtrader_runner.py
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
| 清洗后面板 | `data/processed/daily_panel_tencent_clean.parquet`，**5,088,372 行 × 12 列**（含 `board` 列） |
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

方向已统一为"值越大 → 预期收益越高"：

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
| M7 补检 | \|β\|<0.02、R²<0.05；1D/5D/20D × 三状态全部显著；发现"小盘 alpha"；`ep_ttm` 跨市值均匀 |

## 阶段三计划（M0–M8）

阶段三主线：**因子合成（线性 + 非线性）→ 交易规则 → 自研事件驱动回测引擎 → 绩效指标 → Backtrader 交叉验证 → 最终报告**。

| 里程碑 | 内容 | 关键产出 | 验收要点 |
|---|---|---|---|
| M0 | 环境与数据确认 | 探查报告 | 工作区干净、关键文件齐全 |
| M1 | 基准与交易日历准备 | `hs300_benchmark.parquet`、调仓日历 | 沪深 300 日线、月度调仓日列表 |
| M2 | 因子合成（线性方案） | `composite_equal.parquet`、`composite_ic.parquet`、`composite_icir.parquet` | ≥ 2 种线性合成 |
| M3 | 因子合成（非线性方案） | `composite_lasso.parquet`、`composite_xgb.parquet` | Lasso + XGBoost |
| M4 | 交易规则模块 | `tradable_filter.py` | 涨跌停 / 停牌过滤、月度调仓、持仓 50 只 |
| M5 | 自研事件驱动回测引擎 | `engine.py`、`run_backtest.py` | 无未来函数、成本 0.3% + 滑点 0.1% |
| M6 | 绩效指标模块 | `metrics.py` | 年化 / Sharpe / 回撤 / Calmar / 胜率 / 盈亏比 |
| M7 | Backtrader 交叉验证 | `backtrader_runner.py`、对比表 | 误差 < 2% |
| M8 | 最终报告与交付物 | `docs/stage3_final_report.md`、净值曲线图 | 超额 ≥ 8%、Sharpe ≥ 1.2 |

### 阶段三本周重点（三大块）

1. **因子合成**
   - 三种线性合成：**等权 / IC 加权 / IR 加权**；
   - 非线性：**Lasso / XGBoost**，按时间切训练 / 验证；
   - 合成权重只能用**截至当月**的历史数据计算。

2. **自研事件驱动回测引擎**
   - 四大类起步：`DataFeed` / `Signal` / `Broker` / `Portfolio`；
   - 先用"已知答案的对照策略"验证引擎无 bug，再上真策略；
   - 绩效指标全部自实现，并配单测。

3. **Backtrader 交叉验证**
   - 同一策略用 Backtrader 重跑，误差 **< 2%**；
   - 超 2% 时逐级对账：持仓 → 单笔 → 净值。

## 阶段三硬性规范

以下四条是阶段三的"红线"，代码里必须写死为注释并严格执行：

1. **合成权重时点**：IC / IR 加权只能用**截至当月**的历史数据算权重；使用全样本统计量属于**未来函数**，禁止。
2. **训练 / 验证切分**：Lasso / XGBoost **必须按时间切分**（如滚动或扩展窗口），**严禁随机打散**。
3. **事件驱动两条铁律**（写在 `engine.py` 顶部注释里）：
   - **信号用当日数据**，不得引用 T+1 及以后的信息；
   - **成交发生在信号日之后**（如 T+1 开盘 / 收盘），不得当日成交。
4. **绩效指标自实现**：年化收益 / Sharpe / 最大回撤 / Calmar / 胜率 / 盈亏比全部自写并配单测，不直接调第三方。

## 关键产物文件

### 阶段一 / 二

| 文件 | 说明 |
|---|---|
| `data/processed/factor_panel.parquet` | 18 基础因子面板，5,088,372 × 20 |
| `data/processed/factor_panel_final.parquet` | 阶段二最终 8 因子面板，5,045,205 × 8，MultiIndex，方向已统一 |
| `data/processed/final_factor_list.csv` | 阶段二最终因子清单（类别 / 方向 / IC） |
| `data/processed/market_regime.csv` | 市场状态序列（bull / flat / bear） |
| `data/processed/regime_ic_summary.csv` | 分市场状态 IC 汇总 |
| `data/processed/sector_ic_summary.csv` | 分上市板块 IC 汇总 |
| `data/processed/size_ic_summary.csv` | 分市值 IC 汇总 |
| `docs/stage2_final_report.md` | 阶段二完整报告，353 行 |

### 阶段三（规划 / 进行中）

| 文件 | 里程碑 | 说明 |
|---|---|---|
| `data/processed/hs300_benchmark.parquet` | M1 | 沪深 300 日线基准 |
| `data/processed/rebalance_calendar.csv` | M1 | 月度调仓日列表 |
| `data/processed/composite_equal.parquet` | M2 | 等权合成因子 |
| `data/processed/composite_ic.parquet` | M2 | IC 加权合成因子 |
| `data/processed/composite_icir.parquet` | M2 | ICIR 加权合成因子 |
| `data/processed/composite_lasso.parquet` | M3 | Lasso 合成因子 |
| `data/processed/composite_xgb.parquet` | M3 | XGBoost 合成因子 |
| `src/mfalpha/backtest/engine.py` | M5 | 自研事件驱动引擎 |
| `src/mfalpha/backtest/tradable_filter.py` | M4 | 涨跌停 / 停牌过滤 |
| `src/mfalpha/backtest/metrics.py` | M6 | 自实现绩效指标 |
| `src/mfalpha/backtest/backtrader_runner.py` | M7 | Backtrader 交叉验证 |
| `docs/stage3_final_report.md` | M8 | 阶段三最终报告 |

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
| 单元测试 | ✅ 59 passed |
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

### 阶段三：合成与回测（进行中 🚧）

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M0 | 环境与数据确认 | ⏳ 待开始 |
| M1 | 基准与交易日历准备 | ⏳ 待开始 |
| M2 | 因子合成（线性） | ⏳ 待开始 |
| M3 | 因子合成（非线性） | ⏳ 待开始 |
| M4 | 交易规则模块 | ⏳ 待开始 |
| M5 | 自研事件驱动回测引擎 | ⏳ 待开始 |
| M6 | 绩效指标模块 | ⏳ 待开始 |
| M7 | Backtrader 交叉验证 | ⏳ 待开始 |
| M8 | 最终报告与交付物 | ⏳ 待开始 |

**最终验收指标**：年化超额 **≥ 8%**，Sharpe **≥ 1.2**。

## 子目录 README 索引

| 目录 | README | 内容 |
|---|---|---|
| `docs/` | [docs/README.md](docs/README.md) | 阶段验收表、质量报告、阶段三报告索引 |
| `scripts/` | [scripts/README.md](scripts/README.md) | 数据、质量、因子、检验、合成、回测脚本说明 |
| `src/mfalpha/` | [src/mfalpha/README.md](src/mfalpha/README.md) | 核心包结构、PIT 对齐、合成与回测模块约定 |
| `tests/` | [tests/README.md](tests/README.md) | 单元测试运行方式与覆盖范围 |

> `data/` 目录被 `.gitignore` 忽略，不建议在仓库中维护 `data/README.md`。

## 开发规范

- Commit 消息使用中文，遵循 Conventional Commits：`feat` / `fix` / `chore` / `docs` / `refactor` / `test`。
- 因子模块风格：单股票 `pd.Series` 输入，`window` 参数，返回等长 `Series`。
- 财务数据必须按 `ann_date` 做 PIT 对齐。
- Tushare 批量拉取必须在干净 IP 下进行，校园网可能触发 IP 限制。
- 不提交 `.env`、`.venv/`、根目录 `/data/`、`*.parquet`、`*.egg-info/`。
- **阶段三新增**：
  - 合成权重必须"滚动到时点"，禁止使用全样本统计量。
  - Lasso / XGBoost **按时间切**训练 / 验证，禁止随机打散。
  - 事件驱动引擎必须遵守"信号用当日、成交在信号之后"。
  - 绩效指标自实现 + 单测，不用第三方黑盒。
  - Backtrader 仅作为**交叉验证**，主引擎是自研的那一套。

## 常见问题

| 问题 | 解决 |
|---|---|
| `ModuleNotFoundError: mfalpha` | 在项目根目录执行 `pip install -e .` |
| PowerShell 看 UTF-8 文件乱码 | 使用 `Get-Content xxx -Encoding UTF8` |
| Tushare 报"IP 数量超限" | 切换手机热点或家庭宽带，避免校园网共享出口 IP |
| `pe_ttm` 缺失率较高 | 亏损公司 PE 无意义，改用 `ep_ttm`，负值归 NaN |
| `alphalens` 安装 / 维护问题 | 使用 `alphalens-reloaded` |
| `peewee` 在 Python 3.12 编译失败 | 先安装 `peewee>=3.17.5`，再安装 `alphalens-reloaded` |
| `pd.Timedelta(days=365)` 触发 `DeprecationWarning` | 改用 `pd.DateOffset(days=365)` |
| `np.percentile([])` 报 `IndexError` | 调用前判断 `len(valid) == 0` |
| VS Code 弹"content is newer" | 点 **Overwrite**，再手动跑 black + flake8 后重新 commit |
| flake8 报 F541 | f-string 无占位符，手动去掉 `f` 前缀 |
| Backtrader 与自研引擎误差 > 2% | 逐级对账：先比持仓，再比单笔，最后比净值 |
| XGBoost 结果抖动大 | 检查是否误用了随机打散；固定随机种子；时间序列切分 |

## 下一步计划

**阶段三 M0 第一步**：

1. 在 PowerShell 里跑环境自检，确认工作区干净、59 passed、关键文件齐全。
2. 开始 M1：拉取沪深 300 日线 → `hs300_benchmark.parquet`；生成月度调仓日 → `rebalance_calendar.csv`。
3. M2：先做三种线性合成，全部用截至当月的滚动历史权重。

## 维护约定

README 是项目的活文档，必须始终更新。

- 根 `README.md`：维护项目总览、当前状态、快速开始、因子清单、阶段进度、子目录索引。
- 子目录 `README.md`：维护该目录的详细说明，避免根 README 过长。
- 每完成一个里程碑（M0–M8）：更新"当前状态""阶段进度""关键产物文件"和"最后更新"。
- 每次新增脚本或报告：在对应子 README 中登记，并在根 README 索引中确认链接有效。