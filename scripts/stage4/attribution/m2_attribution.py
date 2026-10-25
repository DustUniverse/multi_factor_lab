"""M2 因子归因：组合因子暴露 x 因子多空收益。

口径与 Brinson 同源（open-to-open + 停牌 ffill），与 quantile_returns 无关。

运行：
    # 单期验证
    python scripts/stage4/attribution/m2_attribution.py --verify

    # 全周期
    python scripts/stage4/attribution/m2_attribution.py --full
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from brinson import PROCESSED, calc_returns, load_context  # noqa: E402

GROUP = "lasso_horizon_all8"
VERIFY_TRADE = "2023-01-03"


def load_factor_meta():
    fl = pd.read_csv(PROCESSED / "final_factor_list.csv")
    return {r["factor"]: bool(r["flipped"]) for _, r in fl.iterrows()}, fl[
        "factor"
    ].tolist()


def zscore_flip(s: pd.Series, flipped: bool, z_cap: float = 3.0) -> pd.Series:
    """z-score 标准化，按 z_cap 缩尾（winsorize），再按 flipped 决定是否翻转。"""
    z = (s - s.mean()) / s.std()
    z = z.clip(-z_cap, z_cap)  # winsorize，防止厚尾因子暴露异常
    return -z if flipped else z


def factor_ret_q9_q0(panel_t, factor, flipped, syms, trade, next_trade, ctx):
    """全市场按因子分 10 组，Q9 与 Q0 的 open-to-open 收益差。"""
    z = zscore_flip(panel_t[factor].astype(float).dropna(), flipped)
    if len(z) < 100:
        return np.nan
    try:
        q = pd.qcut(z, 10, labels=False, duplicates="drop")
    except ValueError:
        return np.nan
    rets = calc_returns(z.index.tolist(), trade, next_trade, ctx)
    df = pd.DataFrame({"q": q, "ret": rets}).dropna()
    if df["q"].nunique() < 10:
        return np.nan
    g = df.groupby("q")["ret"].mean()
    return float(g.loc[9] - g.loc[0])


def factor_ret_regression(panel_t, factors, flip_map, trade, next_trade, ctx):
    """截面回归 r_i = a + Σ β_f z_if + ε，返回 β、截距、R²、样本数。"""
    z_df = pd.DataFrame(
        {f: zscore_flip(panel_t[f].astype(float), flip_map[f]) for f in factors}
    )
    rets = calc_returns(z_df.index.tolist(), trade, next_trade, ctx)
    df = z_df.join(rets.rename("ret"), how="inner").dropna()
    if len(df) < 100:
        return None
    X = np.column_stack([np.ones(len(df)), df[factors].values])
    y = df["ret"].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ beta
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return {
        "beta": dict(zip(factors, beta[1:])),
        "alpha": float(beta[0]),
        "r2": r2,
        "n": len(df),
    }


def run_one_period(panel, sig, trade, next_trade, syms, flip_map, factors, ctx):
    panel_t = panel.xs(pd.Timestamp(sig), level=0)
    reg = factor_ret_regression(panel_t, factors, flip_map, trade, next_trade, ctx)
    if reg is None:
        return pd.DataFrame()
    records = []
    for f in factors:
        flipped = flip_map[f]
        z = zscore_flip(panel_t[f].astype(float).dropna(), flipped)
        expo = float(z.reindex(syms).mean())
        beta = reg["beta"][f]
        fret_q9q0 = factor_ret_q9_q0(panel_t, f, flipped, syms, trade, next_trade, ctx)
        records.append(
            {
                "factor": f,
                "flipped": flipped,
                "exposure": expo,
                "beta": beta,
                "factor_ret_q9q0": fret_q9q0,
                "contrib": expo * beta,
            }
        )
    return pd.DataFrame(records)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    ctx = load_context()
    flip_map, factors = load_factor_meta()
    print("因子:", factors)
    print("flipped:", flip_map)

    panel = pd.read_parquet(PROCESSED / "factor_panel_neutralized.parquet")
    print(f"因子面板: {panel.shape}")

    holdings = pd.read_csv(
        PROCESSED / f"composite_holdings_{GROUP}.csv", dtype={"symbol": str}
    )
    holdings["symbol"] = holdings["symbol"].str.zfill(6)
    holdings["trade_date"] = pd.to_datetime(holdings["trade_date"])

    bt = pd.read_csv(PROCESSED / f"composite_bt_{GROUP}.csv")
    bt["trade_date"] = pd.to_datetime(bt["trade_date"])
    bt["next_trade_date"] = pd.to_datetime(bt["next_trade_date"])
    bt["signal_date"] = pd.to_datetime(bt["signal_date"])

    brinson = pd.read_csv(PROCESSED / f"brinson_{GROUP}_v2.csv")
    brinson["trade_date"] = pd.to_datetime(brinson["trade_date"])
    excess_map = dict(zip(brinson["trade_date"], brinson["excess"]))

    if args.verify:
        bt = bt[bt["trade_date"] == pd.Timestamp(VERIFY_TRADE)]
        print(f"\n=== 单期验证 {VERIFY_TRADE} ===")

    all_records = []
    for _, row in bt.iterrows():
        trade = row["trade_date"]
        next_trade = row["next_trade_date"]
        sig = row["signal_date"]
        h = holdings[holdings["trade_date"] == trade]
        if len(h) == 0:
            continue
        syms = h["symbol"].tolist()
        df = run_one_period(panel, sig, trade, next_trade, syms, flip_map, factors, ctx)
        df["trade_date"] = trade
        df["signal_date"] = sig
        all_records.append(df)

        if args.verify:
            df["excess_brinson"] = excess_map.get(trade, np.nan)
            print(df.to_string())
            print(f"\n因子贡献合计: {df['contrib'].sum():.6f}")
            print(f"Brinson 该期 excess: {excess_map.get(trade, np.nan):.6f}")
            print(f"残差: {df['contrib'].sum() - excess_map.get(trade, np.nan):.6f}")

    if args.full:
        out = pd.concat(all_records, ignore_index=True)
        path = PROCESSED / f"factor_attr_{GROUP}.csv"
        out.to_csv(path, index=False)
        print(f"\n[OK] {len(out)} 行 -> {path}")
        total = (
            out.groupby("factor")[["contrib"]]
            .sum()
            .sort_values("contrib", ascending=False)
        )
        print("\n全周期因子贡献累计（expo × beta）:")
        print(total.round(4).to_string())
        factor_sum = float(total["contrib"].sum())
        excess_hs300 = float(brinson["excess"].sum())

        mkt = pd.read_csv(PROCESSED / "m2_diagnose_market.csv")
        mkt["trade_date"] = pd.to_datetime(mkt["trade_date"])
        excess_vs_mkt = float((mkt["gross_ret"] - mkt["mkt_ret"]).sum())
        mkt_minus_hs300 = float((mkt["mkt_ret"] - mkt["Rb"]).sum())

        print("\n=== 归因结构（相对 HS300）===")
        print(f"Brinson 超额:          {excess_hs300:.4f}")
        print(
            f"因子可解释 Σ(expo×β):  {factor_sum:.4f} "
            f"({factor_sum / excess_hs300:.1%})"
        )
        print(
            f"因子外 alpha:          {excess_vs_mkt - factor_sum:.4f} "
            f"({(excess_vs_mkt - factor_sum) / excess_hs300:.1%})"
        )
        print(
            f"市场结构(全市场-HS300): {mkt_minus_hs300:.4f} "
            f"({mkt_minus_hs300 / excess_hs300:.1%})"
        )
        print(
            f"校验: 因子+alpha+结构 = "
            f"{factor_sum + (excess_vs_mkt - factor_sum) + mkt_minus_hs300:.4f} "
            f"(应≈超额 {excess_hs300:.4f})"
        )


if __name__ == "__main__":
    main()
