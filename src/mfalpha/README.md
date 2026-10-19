# mfalpha 核心包

`src/mfalpha` 是项目核心 Python 包，提供数据对齐、因子计算等基础模块。  
阶段三的合成与回测运行入口主要位于 `scripts/backtest/`，核心包保持数据与因子基础能力。

## 目录说明

```text
src/mfalpha/
├─ data/
│  └─ pit_align.py              # 财务数据 PIT 对齐：按 ann_date 公告日生效
├─ factors/                     # 阶段一：18 个基础因子
│  ├─ 价量类 7 个
│  ├─ 技术类 4 个
│  ├─ 财务类 4 个
│  ├─ 估值类 2 个
│  └─ 换手类 1 个
└─ （阶段三合成与回测模块以仓库实际为准；运行脚本见 scripts/backtest/）
```

## 因子模块约定

- 输入：单股票 `pd.Series`；
- 参数：统一 `window`；
- 输出：与输入等长的 `pd.Series`；
- 暖机期不足返回 `NaN`；
- 滚动窗口 `min_periods` 与 `window` 一致；
- 阶段二最终 8 因子方向已统一为“值越大 → 预期收益越高”，翻转只需乘 −1。

## PIT 对齐

财务数据必须按公告日 `ann_date` 生效，而非报告期 `end_date`。  
实现：`src/mfalpha/data/pit_align.py`。

- `roe`、`netprofit_yoy`、`or_yoy` 是年内累计值，不是单季值；
- 同一 `ann_date + end_date` 可能有多条，需要去重；
- 未来公告日（追溯公告 / IPO 披露）在 PIT 下天然不生效。

## 阶段三与核心包的关系

阶段三的合成、回测、交叉验证以脚本形式落地在 `scripts/backtest/`：

| 脚本 | 作用 |
|---|---|
| `composite_factors.py` | 线性合成：IC / IR / 等权 × all8 / no_vol |
| `composite_factors_lasso.py` | Lasso 非线性合成 |
| `engine.py` | 自研事件驱动回测引擎 |
| `run_composite_backtest.py` | 8 组组合回测 |
| `run_backtrader_ic_no_vol.py` | Backtrader 交叉验证 |

核心包 `src/mfalpha` 继续为这些脚本提供数据对齐与因子计算基础。

## 阶段三硬性规范

1. 合成权重只能用截至当月的历史数据，禁止全样本统计量。
2. Lasso 按时间切训练 / 验证，禁止随机打散。
3. 事件驱动两条铁律：
   - 信号只允许使用当日及之前的数据；
   - 成交只能发生在信号日之后（T+1 及以后）。
4. 绩效指标自实现 + 单测，不直接调第三方。
5. Backtrader 仅作交叉验证，主引擎是自研的。

## 导入方式

项目采用 `src` 布局，需先可编辑安装：

```powershell
pip install -e .
```

之后即可：

```python
from mfalpha.data.pit_align import ...
from mfalpha.factors import ...
```

## 测试

```powershell
python -m pytest tests
```

阶段一/二基线为 **59 passed**；阶段三新增测试以 `python -m pytest` 实际输出为准。  
新增测试应覆盖：合成权重滚动时点、Lasso 时间切分、交易规则、事件驱动对照策略、绩效指标手算对照。

## 与阶段二 / 三的衔接

- 阶段二最终因子库：`data/processed/factor_panel_final.parquet`（5,045,205 × 8，MultiIndex，方向已统一）。
- 阶段三在此之上做合成与回测，中间产物写入 `data/processed/composite_*.parquet`、`composite_bt_*.csv`、`bt_vs_self_ic_no_vol.csv`。
- 阶段三最优策略 `lasso_all8`：年化 **+65.43%**、Sharpe **1.681**、超额 **+68.75%**。