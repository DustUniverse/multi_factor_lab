# multi_factor_lab

> A 股多因子选股策略实习项目  
> 核心流程：**数据获取 → 因子库 → 检验中性化 → 回测 → 归因**  
> 当前阶段：**阶段一 ✅ 已验收 | 阶段二 🚧 进行中**  
> 最后更新：2026-10-08

---

## 目录

- [项目简介](#项目简介)
- [当前状态](#当前状态)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [数据体系](#数据体系)
- [因子库（18 个）](#因子库18-个)
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

## 当前状态

| 模块 | 状态 | 说明 |
|---|---|---|
| 数据体系 | ✅ 已验收 | 4853 只股票，2019-09-30 ~ 2024-09-30，1213 个交易日 |
| 因子库 | ✅ 18 / 18 | 价量 7 + 技术 4 + 财务 4 + 估值 2 + 换手 1 |
| 因子面板 | ✅ 已生成 | `data/processed/factor_panel.parquet`，5,088,372 行 × 20 列 |
| 单元测试 | ✅ 59 passed | `python -m pytest` |
| 阶段一验收 | ✅ 通过 | `docs/stage1_checklist.md` |
| 阶段二 | 🚧 进行中 | 因子有效性检验 → 中性化 → 回测骨架 → 归因 |

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
Test-Path data\processed\factor_panel.parquet
```

期望结果：

- 工作区干净，与 `origin/main` 同步；
- `59 passed`；
- `Test-Path` 返回 `True`。

### 4. 生成因子面板

```powershell
python scripts/factors/build_factor_panel.py
```

输出：

```text
data/processed/factor_panel.parquet
```

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
│     └─ factor_panel.parquet
├─ docs/                         # 文档与报告
│  ├─ README.md
│  ├─ stage1_checklist.md
│  └─ reports/
│     └─ data_quality_report_tencent.md
├─ scripts/                      # 可执行脚本
│  ├─ README.md
│  ├─ data/
│  ├─ quality/
│  ├─ factors/
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
| 清洗后面板 | `data/processed/daily_panel_tencent_clean.parquet`，**5,088,372 行 × 12 列** |
| 财务数据 | Tushare Pro；PIT 对齐后 `data/processed/financial_panel_pit.parquet`，5,088,372 行 |
| 质量报告 | `docs/reports/data_quality_report_tencent.md`，单字段缺失率 < 2% |

## 因子库（18 个）

| 类别 | 数量 | 因子 |
|---|---:|---|
| 价量类 | 7 | `momentum_20`、`reversal_20`、`volatility_20`、`corr_pv_20`、`volume_ratio`、`amplitude_20`、`amihud_20` |
| 技术类 | 4 | `rsi_14`（Wilder 平滑）、`bias_20`、`boll_dev_20`、`macd_dev`（已归一化） |
| 财务类 | 4 | `roe`、`netprofit_yoy`、`or_yoy`、`debt_to_assets`（PIT 对齐） |
| 估值类 | 2 | `ep_ttm`（1/PE_TTM）、`bp`（1/PB） |
| 换手类 | 1 | `turnover`（来自 Tushare `daily_basic`） |
| **合计** | **18** | — |

## 一键生成因子面板

主入口：

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

### 阶段二：检验、中性化、回测、归因（进行中 🚧）

建议路线：**先 A（因子有效性检验），再 C（中性化），最后 B（回测骨架）。**

| 步骤 | 内容 | 状态 |
|---|---|---|
| A. 因子有效性检验 | 用 `alphalens-reloaded` 计算 IC、ICIR、分层收益，筛掉无效因子 | 🚧 待开始 |
| C. 因子中性化 | 对行业、市值做回归取残差，消除风格暴露 | ⏳ 未开始 |
| B. 多因子合成与回测骨架 | 因子合成、打分选股、组合构建、净值曲线 | ⏳ 未开始 |
| D. 归因分析 | 收益来源拆解 | ⏳ 未开始 |

## 子目录 README 索引

| 目录 | README | 内容 |
|---|---|---|
| `docs/` | [docs/README.md](docs/README.md) | 验收表、质量报告、阶段报告索引 |
| `scripts/` | [scripts/README.md](scripts/README.md) | 数据、质量、因子、探测脚本说明 |
| `src/mfalpha/` | [src/mfalpha/README.md](src/mfalpha/README.md) | 核心包结构、PIT 对齐、因子模块约定 |
| `tests/` | [tests/README.md](tests/README.md) | 单元测试运行方式与覆盖范围 |

> `data/` 目录被 `.gitignore` 忽略，不建议在仓库中维护 `data/README.md`。数据说明统一写在根 README 和 `docs/README.md`。

## 开发规范

- Commit 消息使用中文，遵循 Conventional Commits：`feat` / `fix` / `chore` / `docs` / `refactor` / `test`。
- 因子模块风格：单股票 `pd.Series` 输入，`window` 参数，返回等长 `Series`。
- 财务数据必须按 `ann_date` 做 PIT 对齐。
- Tushare 批量拉取必须在干净 IP 下进行，校园网可能触发 IP 限制。
- 不提交 `.env`、`.venv/`、根目录 `/data/`、`*.parquet`。
- 每次新增因子、脚本、数据产物、验收项，都要同步更新本 README 对应章节。

## 常见问题

| 问题 | 解决 |
|---|---|
| `ModuleNotFoundError: mfalpha` | 在项目根目录执行 `pip install -e .` |
| PowerShell 看 UTF-8 文件乱码 | 使用 `Get-Content xxx -Encoding UTF8` |
| Tushare 报“IP 数量超限” | 切换手机热点或家庭宽带，避免校园网共享出口 IP |
| `pe_ttm` 缺失率较高 | 亏损公司 PE 无意义，改用 `ep_ttm`，负值归 NaN |
| `alphalens` 安装/维护问题 | 使用 `alphalens-reloaded` |
| `peewee` 在 Python 3.12 编译失败 | 先安装 `peewee>=3.17.5`，再安装 `alphalens-reloaded` |
| 脚本输出中文乱码 | 多为 PowerShell 编码显示问题，文件本身通常正常 |

## 下一步计划

1. 对 18 个因子逐个计算 IC、ICIR、分层收益，产出汇总排名。
2. 对行业、市值进行中性化，保存残差因子。
3. 搭建多因子合成与回测骨架，输出净值曲线。
4. 做归因分析，拆解收益来源。


## 维护约定

README 是项目的活文档，必须始终更新。

- 根 `README.md`：维护项目总览、当前状态、快速开始、因子清单、阶段进度、子目录索引。
- 子目录 `README.md`：维护该目录的详细说明，避免根 README 过长。
- 每次完成一个小阶段：更新“当前状态”“阶段进度”“最后更新”。
- 每次新增脚本或报告：在对应子 README 中登记，并在根 README 索引中确认链接有效。