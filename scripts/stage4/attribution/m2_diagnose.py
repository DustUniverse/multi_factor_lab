"""M2 诊断：因子贡献对齐的是"组合相对全市场等权"，而非相对 HS300。

运行：
    python scripts/stage4/attribution/m2_diagnose.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from brinson import PROCESSED, calc_returns, load_context  # noqa: E402

GROUP = "lasso_horizon_all8"


def main():
    ctx = load_context()
    bt = pd.read_csv(PROCESSED / f"composite_bt_{GROUP}.csv")
    bt["trade_date"] = pd.to_datetime(bt["trade_date"])
    bt["next_trade_date"] = pd.to_datetime(bt["next_trade_date"])

    brinson = pd.read_csv(PROCESSED / f"brinson_{GROUP}_v2.csv")
    brinson["trade_date"] = pd.to_datetime(brinson["trade_date"])

    # 全市场等权收益（每期）
    mkt = []
    for _, row in bt.iterrows():
        trade = row["trade_date"]
        next_trade = row["next_trade_date"]
        prices_t = ctx["prices_by_date"].get(trade)
        if prices_t is None:
            continue
        syms = prices_t.index.tolist()
        rets = calc_returns(syms, trade, next_trade, ctx)
        mkt.append({"trade_date": trade, "mkt_ret": float(rets.mean())})
    mkt_df = pd.DataFrame(mkt)

    m = bt.merge(mkt_df, on="trade_date").merge(
        brinson[["trade_date", "Rb", "excess"]], on="trade_date"
    )
    m["excess_vs_mkt"] = m["gross_ret"] - m["mkt_ret"]

    print("=== 累计（逐期算术和）===")
    print(f"组合 gross_ret:        {m['gross_ret'].sum():.4f}")
    print(f"全市场等权 mkt_ret:    {m['mkt_ret'].sum():.4f}")
    print(f"HS300 Rb:             {m['Rb'].sum():.4f}")
    print(f"组合 - 全市场等权:      {m['excess_vs_mkt'].sum():.4f}")
    print(f"组合 - HS300（Brinson）: {m['excess'].sum():.4f}")
    print(f"全市场等权 - HS300:     {(m['mkt_ret'] - m['Rb']).sum():.4f}")

    fa = pd.read_csv(PROCESSED / f"factor_attr_{GROUP}.csv")
    factor_sum = fa["contrib"].sum()
    print(f"\n因子贡献 Σ(expo×β):    {factor_sum:.4f}")
    print(f"残差 vs 组合-全市场:    {factor_sum - m['excess_vs_mkt'].sum():.4f}")
    print(f"残差 vs 组合-HS300:     {factor_sum - m['excess'].sum():.4f}")

    out = PROCESSED / "m2_diagnose_market.csv"
    m.to_csv(out, index=False)
    print(f"\n[OK] 逐期明细 -> {out}")


if __name__ == "__main__":
    main()
