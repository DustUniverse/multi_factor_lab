"""M1 Brinson 行业明细与分年度汇总。

复用 brinson.py 的函数，输出：
- data/processed/brinson_detail_lasso_horizon_all8.csv：逐期 x 行业明细
- 终端打印分年度 A/S/I 汇总、行业配置贡献 Top/Bottom

运行：
    python scripts/stage4/attribution/brinson_detail.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from brinson import (  # noqa: E402
    PROCESSED,
    bench_weight_snapshot,
    brinson_one_period,
    calc_returns,
    industry_snapshot,
    load_context,
)

GROUP = "lasso_horizon_all8"


def main():
    ctx = load_context()
    holdings = pd.read_csv(
        PROCESSED / f"composite_holdings_{GROUP}.csv", dtype={"symbol": str}
    )
    holdings["symbol"] = holdings["symbol"].str.zfill(6)
    holdings["trade_date"] = pd.to_datetime(holdings["trade_date"])

    bt = pd.read_csv(PROCESSED / f"composite_bt_{GROUP}.csv")
    bt["trade_date"] = pd.to_datetime(bt["trade_date"])
    bt["next_trade_date"] = pd.to_datetime(bt["next_trade_date"])
    bt["signal_date"] = pd.to_datetime(bt["signal_date"])

    details = []
    for _, row in bt.iterrows():
        trade = row["trade_date"]
        next_trade = row["next_trade_date"]
        sig = row["signal_date"]
        h = holdings[holdings["trade_date"] == trade]
        if len(h) == 0:
            continue
        syms = h["symbol"].tolist()
        port_df = pd.DataFrame({"symbol": syms, "weight": 1.0 / len(syms)})
        port_rets = calc_returns(syms, trade, next_trade, ctx)

        ind_ts = industry_snapshot(ctx["ind"], sig)
        ind_sym = {ctx["ts2sym"].get(ts, ts): name for ts, name in ind_ts.items()}

        bw_ts = bench_weight_snapshot(ctx["bench_w"], sig)
        bw_sym = {ctx["ts2sym"].get(ts, ts): w for ts, w in bw_ts.items()}
        bench_rets = calc_returns(list(bw_sym.keys()), trade, next_trade, ctx)

        res = brinson_one_period(port_df, bw_sym, ind_sym, port_rets, bench_rets)
        d = res["detail"].copy()
        d["trade_date"] = trade
        details.append(d)

    detail = pd.concat(details, ignore_index=True)
    out = PROCESSED / f"brinson_detail_{GROUP}.csv"
    detail.to_csv(out, index=False)
    print(f"[OK] {len(detail)} 行 -> {out}")
    print("columns:", list(detail.columns))

    detail["year"] = detail["trade_date"].dt.year
    yearly = detail.groupby("year")[["A", "S", "I"]].sum()
    yearly["excess_arith"] = yearly["A"] + yearly["S"] + yearly["I"]
    print("\n分年度 A/S/I 汇总（逐期算术和）:")
    print(yearly.round(4).to_string())

    by_ind = detail.groupby("industry")[["A", "S", "I"]].sum()
    by_ind["total"] = by_ind.sum(axis=1)
    print("\n行业配置贡献 A Bottom5:")
    print(by_ind.sort_values("A").head(5).round(4).to_string())
    print("\n行业配置贡献 A Top5:")
    print(by_ind.sort_values("A").tail(5).round(4).to_string())


if __name__ == "__main__":
    main()
