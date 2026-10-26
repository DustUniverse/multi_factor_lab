# M4a 波动率目标仓位管理（定稿）

## 参数
- 滚动窗口：60 交易日，min_periods=60，年化 ×√252
- 目标波动：`TARGET_VOL = 0.30`（温和）
- 仓位下限：`FLOOR = 0.50`（历史未触发，尾部保险）
- 无前视：`vol60` 窗口右端点 ≤ `signal_date`，`reindex(method="ffill")` 取 ≤ signal_date 的最后一个值
- 前 11 期（日频净值不足 60 日）pos=1.0（满仓，等同基线）

## 绩效（期频）
| 指标 | 基线 | M4a | 变化 |
|---|---|---|---|
| 年化收益 | 53.69% | 49.92% | -3.77pp |
| 年化波动 | 36.75% | 35.95% | -0.80pp |
| Sharpe | 1.461 | 1.388 | -0.073 |
| MDD | -21.84% | -24.18% | -2.34pp |
| Calmar | 2.459 | 2.064 | -0.395 |
| 平均仓位 | 1.000 | 0.955 | — |

## 关键诊断结论（M4b 设计依据）
1. **vol60 vs gross_ret 相关系数 = +0.356**（n=40）：高波动期 gross_ret 均值 Q4=+9.16%，低波动 Q1=-3.27%。**高波动 = 高收益**，vol targeting 系统性砍掉反弹收益。
2. **压仓越狠，MDD 反而越大**：TARGET_VOL 0.20→0.40，MDD -24.12%→-22.98%，基线 -21.84%。根因：2024-01 暴跌时 vol60 滞后（满仓吃 -20%），3 月 vol 飙升压仓时正好削掉反弹。
3. **2024-02-05 日频 MDD 谷底，M4a 未防住**：2024-01-02 调仓满仓，2 月 vol60 尚未飙升，pos 仍 1.0。**波动率是滞后指标，防不住第一次急跌**——这是 M4b（回撤止损，实时可见）的直接动机。

## M4a 定位
- **不追求单独 Sharpe 提升**（诊断证明该策略与 vol targeting 系统性不兼容）
- 价值在于：① 提供 `position_series` 工程框架（M4b 复用）；② 极端波动（vol60>45%）的尾部保险；③ 为 M4b 提供"基础仓位 + 临时压仓"两层结构
- 合并验收（M4a+M4b+M4c）目标：Sharpe ≥ 1.680，MDD ≤ 25%

## 产出
- `scripts/stage4/position/m4a_target_vol.py`：仓位计算
- `scripts/stage4/position/m4a_backtest.py`：回测对比
- `scripts/stage4/position/m4a_diagnose.py`：诊断（vol vs ret 相关、参数扫描）
- `data/processed/m4a_position_series.parquet`（gitignore）
- `data/processed/m4a_bt_periods.csv`、`m4a_bt_nav.parquet`（gitignore）