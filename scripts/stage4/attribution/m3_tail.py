"""M3c: 下行/尾部风险（日频）。

基于 bt_nav_lasso_horizon_all8_daily.parquet（1035 个交易日）。
指标：
- 年化波动、偏度、超额峰度
- 下行波动（semi-deviation，仅负收益日）
- 历史 VaR / CVaR (95%, 99%)
- 参数 VaR（正态假设，对照）
- 最大单日亏损 / 涨幅、最差/最好 5 日均值
- 滚动 60 日年化波动（保存供画图）
- 年度分解
"""

import os

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

NAV_FILE = os.path.join(PROC, "bt_nav_lasso_horizon_all8_daily.parquet")
OUT_TAIL = os.path.join(PROC, "m3_tail_risk.csv")
OUT_ROLL = os.path.join(PROC, "m3_rolling_vol.csv")

ANN = np.sqrt(243)


def tail_metrics(r, label):
    r = r.dropna()
    n = len(r)
    mu, sd = r.mean(), r.std(ddof=1)
    skew, kurt = r.skew(), r.kurt()
    downside = r[r < 0]
    dd_std = downside.std(ddof=1) if len(downside) > 1 else np.nan
    var95 = float(np.percentile(r, 5))
    var99 = float(np.percentile(r, 1))
    cvar95 = float(r[r <= var95].mean())
    cvar99 = float(r[r <= var99].mean())
    pvar95 = float(mu + norm.ppf(0.05) * sd)
    pvar99 = float(mu + norm.ppf(0.01) * sd)
    return {
        "label": label,
        "n_days": n,
        "mean_daily": mu,
        "std_daily": sd,
        "vol_ann": sd * ANN,
        "skew": skew,
        "excess_kurt": kurt,
        "downside_std_daily": dd_std,
        "downside_vol_ann": dd_std * ANN if pd.notna(dd_std) else np.nan,
        "var95_hist": var95,
        "var99_hist": var99,
        "cvar95_hist": cvar95,
        "cvar99_hist": cvar99,
        "var95_param": pvar95,
        "var99_param": pvar99,
        "min_daily": float(r.min()),
        "max_daily": float(r.max()),
        "worst5_mean": float(r.nsmallest(5).mean()),
        "best5_mean": float(r.nlargest(5).mean()),
    }


def fmt(d):
    return (
        f"  {d['label']:6s}  n={d['n_days']:4d}  vol={d['vol_ann']:6.2%}  "
        f"skew={d['skew']:+.2f}  kurt={d['excess_kurt']:+.2f}  "
        f"VaR95={d['var95_hist']:+.2%}  CVaR95={d['cvar95_hist']:+.2%}  "
        f"VaR99={d['var99_hist']:+.2%}  CVaR99={d['cvar99_hist']:+.2%}"
    )


def main():
    print("[M3c] 下行/尾部风险（日频）...")
    nav = pd.read_parquet(NAV_FILE)
    r = nav["daily_ret"].dropna()
    print(
        f"  日收益行数: {len(r)}，区间: {r.index.min().date()} -> {r.index.max().date()}"
    )

    full = tail_metrics(r, "全期")
    yearly = []
    for yr, g in r.groupby(r.index.year):
        if len(g) < 20:
            print(f"  [skip] {yr} 年样本不足 ({len(g)} 天)")
            continue
        yearly.append(tail_metrics(g, str(yr)))

    roll = (r.rolling(60).std() * ANN).dropna()

    print("\n  === 全期 ===")
    print(fmt(full))
    print(f"  下行年化波动: {full['downside_vol_ann']:.2%}")
    print(
        f"  最大单日亏损: {full['min_daily']:+.2%}，"
        f"最大单日涨幅: {full['max_daily']:+.2%}"
    )
    print(
        f"  最差 5 日均值: {full['worst5_mean']:+.2%}，"
        f"最好 5 日均值: {full['best5_mean']:+.2%}"
    )
    print(
        f"  参数 VaR95: {full['var95_param']:+.2%}，"
        f"VaR99: {full['var99_param']:+.2%}"
    )
    print(
        f"  滚动 60 日年化波动: 均值 {roll.mean():.2%}，"
        f" 最大 {roll.max():.2%}（{roll.idxmax().date()}）"
    )

    print("\n  === 分年度 ===")
    for d in yearly:
        print(fmt(d))

    pd.DataFrame([full] + yearly).to_csv(OUT_TAIL, index=False)
    roll.to_frame("vol_ann_60d").to_csv(OUT_ROLL)
    print(f"\n  尾部指标保存: {OUT_TAIL}")
    print(f"  滚动波动保存: {OUT_ROLL}")


if __name__ == "__main__":
    main()
