# mfalpha 核心包

`src/mfalpha` 是项目核心 Python 包，提供数据对齐、因子计算、因子合成与回测所需的基础模块。

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
├─ composite/                   # 阶段三 M2–M3：因子合成
│  └─ （等权 / IC / ICIR / Lasso / XGBoost 的合成逻辑）
└─ backtest/                    # 阶段三 M4–M7：交易规则、引擎、指标
   ├─ tradable_filter.py        # 涨跌停 / 停牌过滤、调仓日历
   ├─ engine.py                 # 自研事件驱动引擎（DataFeed / Signal / Broker / Portfolio）
   ├─ metrics.py                # 年化 / Sharpe / 回撤 / Calmar / 胜率 / 盈亏比
   └─ backtrader_runner.py      # Backtrader 交叉验证
```

## 因子模块约定

- 输入：单股票 `pd.Series`；
- 参数：统一 `window`；
- 输出：与输入等长的 `pd.Series`；
- 暖机期不足返回 `NaN`；
- 滚动窗口 `min_periods` 与 `window` 一致；
- 阶段二最终 8 因子方向已统一为"值越大 → 预期收益越高"，翻转只需乘 −1。

## PIT 对齐

财务数据必须按公告日 `ann_date` 生效，而非报告期 `end_date`。  
实现：`src/mfalpha/data/pit_align.py`。

- `roe`、`netprofit_yoy`、`or_yoy` 是年内累计值，不是单季值；
- 同一 `ann_date + end_date` 可能有多条，需要去重；
- 未来公告日（追溯公告 / IPO 披露）在 PIT 下天然不生效。

## 阶段三核心模块

### `composite/`

- 三种线性合成：等权 / IC 加权 / IR 加权；
- 非线性：Lasso / XGBoost；
- **权重只能用截至当月的历史数据计算**；
- **按时间切训练 / 验证，禁止随机打散**。

### `backtest/engine.py`（自研事件驱动引擎）

四大类起步：

| 类 | 职责 |
|---|---|
| `DataFeed` | 按日期依次喂数据，绝不提前暴露未来数据 |
| `Signal` | 基于当日数据生成信号 |
| `Broker` | 在信号日之后成交，扣成本 0.3% + 滑点 0.1% |
| `Portfolio` | 持仓、权重、净值维护 |

**两条铁律（写死为注释）**：

```python
# RULE 1: 信号只允许使用当日及之前的数据
# RULE 2: 成交只能发生在信号日之后（T+1 及以后），不得当日成交
```

### `backtest/tradable_filter.py`

- 涨跌停过滤；
- 停牌过滤；
- 月度调仓；
- 持仓 50 只。

### `backtest/metrics.py`

自实现绩效指标（配单测）：

- 年化收益
- Sharpe
- 最大回撤
- Calmar
- 胜率
- 盈亏比

### `backtest/backtrader_runner.py`

- 用 Backtrader 重跑同一策略；
- 与自研引擎误差 **< 2%**；
- 超 2% 时逐级对账：持仓 → 单笔 → 净值。

## 导入方式

项目采用 `src` 布局，需先可编辑安装：

```powershell
pip install -e .
```

之后即可：

```python
from mfalpha.data.pit_align import ...
from mfalpha.factors import ...
from mfalpha.composite import ...          # 阶段三
from mfalpha.backtest import ...           # 阶段三
```

## 测试

```powershell
python -m pytest tests
```

当前核心包相关测试均通过，总计 59 passed。阶段三会为 `composite/`、`backtest/`、`metrics.py` 增加新单测。

## 与阶段二 / 三的衔接

- 阶段二最终因子库：`data/processed/factor_panel_final.parquet`（5,045,205 × 8，MultiIndex，方向已统一）。
- 阶段三在此之上做合成与回测，所有中间产物写入 `data/processed/composite_*.parquet`。