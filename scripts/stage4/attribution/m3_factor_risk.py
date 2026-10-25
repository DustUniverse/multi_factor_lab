"""M3b: 因子波动解释（期频，与 M2 同源）。

恒等式：
    R_t = alpha_t + Σ_f contrib_{f,t}
    contrib_{f,t} = exposure_{f,t} * beta_{f,t}   （M2 已算）
    alpha_t = R_t - Σ_f contrib_{f,t}

MCTR（期频）：
    MCTR_f = Cov(contrib_f, R) / sigma_R
    MCTR_alpha = Cov(alpha, R) / sigma_R
    Σ MCTR = sigma_R  （精确）

报告口径：因子波动解释基于月频 51 期，与 M2 因子归因同源；
行业/个股 MCTR 基于日频 1035 个观测（M3a）。
"""

import os

import numpy as np
import pandas as pd

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

FACTOR_ATTR = os.path.join(PROC, "factor_attr_lasso_horizon_all8.csv")
BT_FILE = os.path.join(PROC, "composite_bt_lasso_horizon_all8.csv")
OUT_FILE = os.path.join(PROC, "m3_factor_risk.csv")


def main():
    print("[M3b] 因子波动解释（期频，与 M2 同源）...")

    fa = pd.read_csv(FACTOR_ATTR, parse_dates=["trade_date", "signal_date"])
    bt = pd.read_csv(
        BT_FILE, parse_dates=["signal_date", "trade_date", "next_trade_date"]
    )

    # 对齐：M2 的 trade_date（持仓期开始）= bt 的 trade_date（期初）
    r_map = bt.set_index("trade_date")["gross_ret"]
    fa["R"] = fa["trade_date"].map(r_map)
    miss = int(fa["R"].isna().sum())
    print(f"  因子归因行数: {len(fa)}，R 缺失行: {miss}")
    if miss > 0:
        bad = fa.loc[fa["R"].isna(), "trade_date"].unique()
        print(f"  [warn] R 缺失的 trade_date: {list(bad)[:5]}")

    # 宽表：每期一行 × 8 因子贡献列
    wide = fa.pivot_table(
        index="trade_date", columns="factor", values="contrib", aggfunc="sum"
    )
    R = fa.groupby("trade_date")["R"].first().reindex(wide.index)
    n_periods = len(wide)
    n_factors = wide.shape[1]

    # 因子外 alpha
    alpha = R - wide.sum(axis=1)

    # 精度校验
    diff = float((wide.sum(axis=1) + alpha - R).abs().max())
    print(f"  期数: {n_periods}，因子数: {n_factors}")
    print(f"  Σcontrib + alpha vs R  max abs diff = {diff:.6e}")

    # 期频波动（月频 → 年化 x sqrt(12)）
    sigma = R.std(ddof=1)
    ann = np.sqrt(12)
    print(f"  期频组合波动: {sigma:.6f}，年化 (x√12): {sigma * ann:.2%}")

    # MCTR
    rows = []
    for f in wide.columns:
        c = wide[f].cov(R) / sigma
        rows.append((f, c))
    rows.append(("alpha", alpha.cov(R) / sigma))

    out = pd.DataFrame(rows, columns=["item", "mctr_period"]).set_index("item")
    out["mctr_ann"] = out["mctr_period"] * ann
    out["mctr_pct"] = out["mctr_period"] / sigma

    # 参考统计
    mean_list, std_list = [], []
    for f in out.index:
        s = wide[f] if f in wide.columns else alpha
        mean_list.append(s.mean())
        std_list.append(s.std(ddof=1))
    out["contrib_mean"] = mean_list
    out["contrib_std"] = std_list

    out = out.sort_values("mctr_period", ascending=False)

    print("\n  === 因子波动 MCTR（期频）===")
    show = out.copy()
    for c in ["mctr_ann", "mctr_pct", "contrib_mean", "contrib_std"]:
        show[c] = (show[c] * 100).round(3)
    print(show.to_string())

    s = out["mctr_period"].sum()
    print(f"\n  Σ MCTR_period = {s:.6f}，σ_R = {sigma:.6f}，diff = {s - sigma:.3e}")
    if abs(s - sigma) / sigma < 1e-9:
        print("  [ok] 因子 MCTR 分解精确（Σ = σ_R）")
    else:
        print("  [warn] 分解不精确，检查 contrib / alpha 对齐")

    # 贡献占比（解读用）
    print("\n  === 因子波动占比（MCTR_pct，%）===")
    share = out["mctr_pct"].sort_values(ascending=False)
    print(share.map(lambda x: f"{x * 100:6.2f}%").to_string())
    print(f"  Σ = {share.sum() * 100:.2f}%")

    out.to_csv(OUT_FILE)
    print(f"\n  保存: {OUT_FILE}")


if __name__ == "__main__":
    main()
