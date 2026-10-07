```markdown
# mfalpha — 核心代码包

以可编辑模式安装：`pip install -e .`

## 模块结构
mfalpha/
├── common/ # 通用常量与工具
│ └── constants.py
├── data/ # 数据层
│ └── pit_align.py # Point-in-Time 对齐（按公告日）
├── factors/ # 因子库（18 个）
├── backtest/ # 回测框架（待开发）
├── attribution/ # 归因分析（待开发）
└── models/ # 模型（待开发）
## `factors/` — 因子库

每个因子模块遵循统一风格：

- 输入：单股票 `pd.Series`（或配合 `window` 参数）
- 输出：等长 `pd.Series`（前 `window` 期为 NaN）
- 纯函数，无副作用

### 价量类（7 个）

| 模块 | 因子名 | 说明 |
|---|---|---|
| `momentum.py` | momentum_20 | 20 日动量 |
| `reversal.py` | reversal_20 | 20 日反转 |
| `volatility.py` | volatility_20 | 20 日波动率 |
| `corr_pv.py` | corr_pv_20 | 量价相关性 |
| `volume_ratio.py` | volume_ratio | 量比 |
| `amplitude.py` | amplitude_20 | 20 日振幅 |
| `amihud.py` | amihud_20 | Amihud 非流动性（`close × volume` 近似） |

### 技术类（4 个）

| 模块 | 因子名 | 说明 |
|---|---|---|
| `rsi.py` | rsi_14 | 相对强弱指标（Wilder 平滑） |
| `bias.py` | bias_20 | 20 日乖离率 |
| `boll_dev.py` | boll_dev_20 | 布林带偏离 |
| `macd_dev.py` | macd_dev | MACD 偏离（已归一化） |

### 估值类（2 个）

| 模块 | 因子名 | 说明 |
|---|---|---|
| `valuation.py` | ep_ttm | 1 / PE_TTM（亏损股返 NaN） |
| `valuation.py` | bp | 1 / PB |

### 财务类（4 个，PIT 对齐后在面板中生成）

roe、netprofit_yoy、or_yoy、debt_to_assets（见 `scripts/factors/build_financial_panel.py`）。

### 换手类（1 个）

turnover（见 `factors/turnover.py`）。

## `data/pit_align.py` — Point-in-Time 对齐

**核心函数**：`align_financials_to_daily(daily, financials, financial_cols)`

把季度财务数据按 `ann_date`（公告日）对齐到日频：

> 某个交易日 `t`，只用 `ann_date ≤ t` 的最新一份财报。

**避免前视偏差**——这是财务因子的命根子。

## 测试

每个因子模块在 `tests/unit/` 下有对应单测：

```powershell
python -m pytest tests/unit/test_momentum.py -v      # 单个
python -m pytest                                      # 全部