# multi_factor_lab

> A 股多因子选股策略实习项目  
> 核心流程：**数据获取 → 因子库 → 检验中性化 → 回测 → 归因**  
> 当前阶段：**阶段一 ✅ 已验收 | 阶段二 ✅ 已验收 | 阶段三 🚧 待确认方向**  
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
- [关键产物文件](#关键产物文件)
- [一键生成因子面板](#一键生成因子面板)
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
- 最新 commit：`b9f07e0`（M7-S5 阶段二最终报告）

## 当前状态

| 模块 | 状态 | 说明 |
|---|---|---|
| 数据体系 | ✅ 已验收 | 4853 只股票，2019-09-30 ~ 2024-09-30，1213 个交易日 |
| 基础因子库 | ✅ 18 / 18 | 价量 7 + 技术 4 + 财务 4 + 估值 2 + 换手 1 |
| 因子面板 | ✅ 已生成 | `data/processed/factor_panel.parquet`，5,088,372 行 × 20 列 |
| 阶段一验收 | ✅ 通过 | `docs/stage1_checklist.md` |
| 阶段二 M0–M7 | ✅ 全部完成 | IC 检验 → 分层 → 中性化 → VIF 剔除 → 稳健性 → 最终因子库 → 报告 |
| 最终因子库 | ✅ 8 因子 | `data/processed/factor_panel_final.parquet`，5,045,205 × 8，方向已统一 |
| 阶段二验收 | ✅ 全部达标 | `docs/stage2_final_report.md`（353 行完整报告） |
| 单元测试 | ✅ 59 passed | `python -m pytest` |
| 阶段三 | 🚧 待确认方向 | 多因子合成 / 组合优化 / 策略回测 |

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
- 最新 commit 是 `b9f07e0`。

### 4. 确认关键数据文件存在

```powershell
Test-Path data\processed\factor_panel_final.parquet
Test-Path data\processed\final_factor_list.csv
Test-Path data\processed\factor_panel_selected.parquet
Test-Path data\processed\market_regime.csv
Test-Path data\processed\regime_ic_summary.csv
Test-Path data\processed\sector_ic_summary.csv
Test-Path data\processed\size_ic_summary.csv
Test-Path docs\stage2_final_report.md
```

期望：全部 `True`。

## 目录结构

```text
multi_factor_lab/
├─ README.md                     # 项目总览与索引
├─ pyproject.toml                # 项目配置
├─ requirements.txt              # 依赖清单
├─ .env                          # Tushare Token（不提交）
├─ .gitignore
├─ data/                         # 数据目录（不提交）
│  ├─ raw/
│  └─ processed/
│     ├─ daily_panel_tencent_clean.parquet
│     ├─ financial_panel_pit.parquet
│     ├─ factor_panel.parquet              # 18 基础因子
│     ├─ factor_panel_selected.parquet     # 阶段二初筛后
│     ├─ factor_panel_final.parquet        # 最终 8 因子
│     ├─ final_factor_list.csv
│     ├─ market_regime.csv
│     ├─ regime_ic_summary.csv
│     ├─ sector_ic_summary.csv
│     └─ size_ic_summary.csv
├─ docs/                         # 文档与报告
│  ├─ README.md
│  ├─ stage1_checklist.md
│  ├─ stage2_final_report.md               # 阶段二完整报告（353 行）
│  └─ reports/
│     ├─ data_quality_report_tencent.md
│     └─ ...
├─ scripts/                      # 可执行脚本
│  ├─ README.md
│  ├─ data/
│  ├─ quality/
│  ├─ factors/
│  ├─ validation/                # 阶段二新增：检验、中性化、稳健性
│  └─ probe/
├─ src/
│  └─ mfalpha/                   # 核心 Python 包
│     ├─ README.md
│     ├─ data/
│     │  └─ pit_align.py
│     └─ factors/
└─ tests/                        # 单元测试
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

> 翻转只需乘 −1，不需重新标准化。

## 阶段二核心结论

阶段二路线：**IC 检验（M2）→ 分层回测（M3）→ 中性化（M4）→ VIF 剔除（M5）→ 牛熊/板块稳健性（M6）→ 补检 + 最终因子库 + 报告（M7）**。

| 环节 | 关键结论 |
|---|---|
| M2 IC 检验 | `run_ic_analysis.py` → 18 因子 IC/IR/胜率/t；20D 口径下 12 个因子通过初筛 |
| M3 分层回测 | 十分位分层；`turnover` 多空夏普 8.12、`amihud_20` 7.86 |
| M4 中性化 | 市值/行业中性化后 ICIR 全部改善，`turnover` Sharpe → 14.04 |
| M5 VIF 剔除 | 迭代 4 轮，最终保留 8 因子，全部 `vif_mean < 5`、`vif_median < 4` |
| M6 稳健性 | 市场状态（等权指数 120 日滚动，±10%）→ bull 32.1% / flat 51.6% / bear 16.2%；8 因子在三状态下**全部统计显著**；7/8 因子跨板块符号一致；`amihud_20` 科创板反号但不显著 |
| M7 补检 | 中性化暴露复核 \|β\|<0.02、R²<0.05；1D/5D/20D × 三状态**全部显著**；分市值发现"小盘 alpha"；`ep_ttm` 是唯一跨市值均匀的因子 |

**因子分类（M6 结论）**：

- 核心稳健：`turnover`、`amihud_20`
- 防御型：`reversal_20`、`bias_20`、`corr_pv_20`
- 进攻型：`bp`、`ep_ttm`
- 待观察：`volatility_20`

## 关键产物文件

| 文件 | 说明 |
|---|---|
| `data/processed/factor_panel.parquet` | 18 基础因子面板，5,088,372 × 20 |
| `data/processed/factor_panel_selected.parquet` | 阶段二初筛后因子面板 |
| `data/processed/factor_panel_final.parquet` | **最终 8 因子面板**，5,045,205 × 8，MultiIndex，方向已统一 |
| `data/processed/final_factor_list.csv` | 最终因子清单（类别 / 方向 / IC） |
| `data/processed/market_regime.csv` | 市场状态序列（bull / flat / bear） |
| `data/processed/regime_ic_summary.csv` | 分市场状态 IC 汇总 |
| `data/processed/sector_ic_summary.csv` | 分上市板块 IC 汇总 |
| `data/processed/size_ic_summary.csv` | 分市值 IC 汇总 |
| `docs/stage2_final_report.md` | **阶段二完整报告**，353 行 Markdown |

## 一键生成因子面板

基础 18 因子主入口：

```powershell
python scripts/factors/build_factor_panel.py
```

输出：

```text
data/processed/factor_panel.parquet
```

面板规格：

- 行数：**5,088,372**
- 列数：**20**
- 列结构：`symbol + date + 18 个因子`

旧 11 因子脚本保留：

```powershell
python scripts/factors/build_factor_panel_11f.py
```

输出：

```text
data/processed/factor_panel_11f.parquet
```

阶段二最终 8 因子面板：

```powershell
python scripts/validation/build_final_factor_panel.py
```

输出：

```text
data/processed/factor_panel_final.parquet
data/processed/final_factor_list.csv
```

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
| 复权、停牌、退市处理 | ✅ |
| 无幸存者偏差 | ✅ |
| 一键生成全量因子面板 | ✅ |
| 数据质量校验报告 | ✅ |
| ≥ 18 个基础因子 | ✅ 18 个 |
| 单元测试 | ✅ 59 passed |
| 阶段一验收表 | ✅ `docs/stage1_checklist.md` |

### 阶段二：检验、中性化、稳健性（已验收 ✅）

| 验收标准 | 结果 | 状态 |
|---|---|---|
| IC\|≥0.03、IR≥0.3 的有效因子 ≥ 8 | 8 个 | ✅ |
| 因子 VIF < 5 | 全部 `vif_mean<5`、`median<4` | ✅ |
| 中性化后市值 / 行业暴露 ≈ 0 | \|β\|<0.02、R²<0.05 | ✅ |
| 有效因子 ≥2 种环境显著 | 全部因子 3 种环境全部显著 | ✅ 超额 |
| 稳健性覆盖 ≥3 种环境 | bull / flat / bear | ✅ |
| 报告含完整统计 + 图表 | 353 行 Markdown | ✅ |

### 阶段三：待确认方向（🚧）

| 方向 | 内容 | 优先级 |
|---|---|---|
| A. 多因子合成 | IC 加权 / ICIR 加权 / 最大化 ICIR 组合 8 因子，对比组合后 IC 与 Sharpe | ⭐ 建议先做 |
| B. 组合优化 | 因子暴露约束下均值-方差优化，控制行业 / 市值中性 | 次之 |
| C. 策略回测 | 月频调仓，持有 top-N，扣费后净值 vs 基准 | 最后 |

待与带教确认：

1. 报告格式：Markdown 够不够，是否需要转 Word / PDF / 公司模板？
2. 最终因子库是否需要再做标准化 / 去极值处理？
3. 阶段三具体做 A / B / C 哪个，或全部做？
4. 多因子合成的合成频率（日频 / 月频）？调仓频率（当前默认 20 日）？
5. 是否要指定基准（沪深 300 / 中证 500 / 全市场等权）？

## 子目录 README 索引

| 目录 | README | 内容 |
|---|---|---|
| `docs/` | [docs/README.md](docs/README.md) | 验收表、质量报告、阶段二报告索引 |
| `scripts/` | [scripts/README.md](scripts/README.md) | 数据、质量、因子、检验脚本说明 |
| `src/mfalpha/` | [src/mfalpha/README.md](src/mfalpha/README.md) | 核心包结构、PIT 对齐、因子模块约定 |
| `tests/` | [tests/README.md](tests/README.md) | 单元测试运行方式与覆盖范围 |

> `data/` 目录被 `.gitignore` 忽略，不建议在仓库中维护 `data/README.md`。数据说明统一写在根 README 和 `docs/README.md`。

## 开发规范

- Commit 消息使用中文，遵循 Conventional Commits：`feat` / `fix` / `chore` / `docs` / `refactor` / `test`。
- 因子模块风格：单股票 `pd.Series` 输入，`window` 参数，返回等长 `Series`。
- 财务数据必须按 `ann_date` 做 PIT 对齐。
- Tushare 批量拉取必须在干净 IP 下进行，校园网可能触发 IP 限制。
- 不提交 `.env`、`.venv/`、根目录 `/data/`、`*.parquet`、`*.egg-info/`。
- 每次新增因子、脚本、数据产物、验收项，都要同步更新本 README 对应章节。

## 常见问题

| 问题 | 解决 |
|---|---|
| `ModuleNotFoundError: mfalpha` | 在项目根目录执行 `pip install -e .` |
| PowerShell 看 UTF-8 文件乱码 | 使用 `Get-Content xxx -Encoding UTF8` |
| Tushare 报“IP 数量超限” | 切换手机热点或家庭宽带，避免校园网共享出口 IP |
| `pe_ttm` 缺失率较高 | 亏损公司 PE 无意义，改用 `ep_ttm`，负值归 NaN |
| `alphalens` 安装 / 维护问题 | 使用 `alphalens-reloaded` |
| `peewee` 在 Python 3.12 编译失败 | 先安装 `peewee>=3.17.5`，再安装 `alphalens-reloaded` |
| 脚本输出中文乱码 | 多为 PowerShell 编码显示问题，文件本身通常正常 |
| `pd.Timedelta(days=365)` 触发 `DeprecationWarning` | 改用 `pd.DateOffset(days=365)` |
| `np.percentile([])` 报 `IndexError` | 调用前判断 `len(valid) == 0` |
| smoke 测试报"无有效交易日" | 选数据成熟期（如 2021-06 起），避开 20 日暖机期 |
| VS Code 弹"content is newer" | 点 **Overwrite**，再手动跑 black + flake8 后重新 commit |
| flake8 报 F541 | f-string 无占位符，手动去掉 `f` 前缀 |

## 下一步计划

### 阶段三（待带教确认后启动）

1. **多因子合成**（建议优先）：IC 加权 / ICIR 加权 / 最大化 ICIR 组合，对比组合前后 IC 与 Sharpe。
2. **组合优化**（次之）：因子暴露约束下的均值-方差优化，控制行业 / 市值中性。
3. **策略回测**（最后）：月频调仓，持有 top-N，扣费后净值 vs 基准。

### 阶段三 S1 第一步

先探查 `data/processed/factor_panel_final.parquet` 结构：8 因子的分布、覆盖率、缺失模式，再决定多因子合成方案。

## 维护约定

README 是项目的活文档，必须始终更新。

- 根 `README.md`：维护项目总览、当前状态、快速开始、因子清单、阶段进度、子目录索引。
- 子目录 `README.md`：维护该目录的详细说明，避免根 README 过长。
- 每次完成一个小阶段：更新"当前状态""阶段进度""最后更新"。
- 每次新增脚本或报告：在对应子 README 中登记，并在根 README 索引中确认链接有效。