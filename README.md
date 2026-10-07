# multi_factor_lab

A 股多因子选股策略实习项目。

**核心流程**：数据获取 → 因子库 → 检验中性化 → 回测 → 归因

## 当前状态

**阶段一：数据体系与因子库 — 已验收通过 ✅**

| 项目 | 状态 |
|---|---|
| 股票池 | 4853 只（全市场 A 股，覆盖主板/创业板/科创板） |
| 时间跨度 | 2019-09-30 ~ 2024-09-30（1213 个交易日） |
| 清洗后面板 | 5,088,372 行 × 12 列 |
| 因子库 | **18 个**（价量 7 + 技术 4 + 财务 4 + 估值 2 + 换手 1） |
| 一键因子面板 | `scripts/factors/build_factor_panel.py` → 5,088,372 × 20 |
| 单元测试 | 59 passed |
| 验收表 | [docs/stage1_checklist.md](docs/stage1_checklist.md) |

**阶段二：因子检验 → 中性化 → 回测 → 归因（进行中）**

## 快速开始

```powershell
# 1. 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 2. 安装依赖（首次）
python -m pip install -r requirements.txt
python -m pip install -e .

# 3. 运行测试
python -m pytest

# 4. 一键生成 18 因子面板
python scripts/factors/build_factor_panel.py