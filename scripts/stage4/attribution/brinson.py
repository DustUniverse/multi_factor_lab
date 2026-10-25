"""M1 Brinson 归因：行业配置 + 个股选择 + 交互项。

运行：
    # 先对账 2023 年 lasso_all8（与阶段二试点结果比较）
    python scripts/stage4/attribution/brinson.py \
        --group lasso_all8 --year 2023 --compare
    # 对账通过后跑主推全周期
    python scripts/stage4/attribution/brinson.py --group lasso_horizon_all8
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED = Path("data/processed")


def load_context():
    prices = pd.read_parquet(
        PROCESSED / "daily_panel_tencent_clean.parquet",
        columns=["symbol", "date", "open"],
    )
    prices["symbol"] = prices["symbol"].astype(str).str.zfill(6)
    prices["date"] = pd.to_datetime(prices["date"])
    prices_by_date = {d: g.set_index("symbol") for d, g in prices.groupby("date")}

    ind = pd.read_parquet(PROCESSED / "industry_map.parquet")
    ind["in_date"] = pd.to_datetime(ind["in_date"])
    ind["out_date"] = pd.to_datetime(ind["out_date"])

    sb = pd.read_parquet(PROCESSED / "stock_basic.parquet")
    sym2ts = sb.set_index("symbol")["ts_code"].to_dict()
    ts2sym = sb.set_index("ts_code")["symbol"].to_dict()

    bench_w = pd.read_parquet(PROCESSED / "hs300_weight.parquet")
    bench_w["trade_date"] = pd.to_datetime(bench_w["trade_date"])

    return {
        "prices": prices,
        "prices_by_date": prices_by_date,
        "ind": ind,
        "sym2ts": sym2ts,
        "ts2sym": ts2sym,
        "bench_w": bench_w,
    }


def industry_snapshot(ind, tgt_ts):
    """PIT 行业快照，缺失用最早记录回填（科创板）。返回 ts_code -> l1_name。"""
    snap = ind[
        (ind["in_date"] <= tgt_ts)
        & (ind["out_date"].isna() | (tgt_ts < ind["out_date"]))
    ]
    snap_map = snap.set_index("ts_code")["l1_name"].to_dict()
    first_map = (
        ind.sort_values("in_date").groupby("ts_code").first()["l1_name"].to_dict()
    )
    result = dict(first_map)
    result.update(snap_map)
    return result


def bench_weight_snapshot(bench_w, tgt_ts):
    """HS300 权重 asof 快照，返回 ts_code -> weight（小数）。"""
    sub = bench_w[bench_w["trade_date"] <= tgt_ts]
    snap_date = sub["trade_date"].max()
    last = sub[sub["trade_date"] == snap_date].copy()
    last["weight"] = last["weight"] / 100.0
    return last.set_index("con_code")["weight"].to_dict()


def calc_returns(symbols, trade, next_trade, ctx):
    """open-to-open 收益，停牌 ffill，与 engine 一致。"""
    trade_p = ctx["prices_by_date"].get(trade)
    next_p = ctx["prices_by_date"].get(next_trade)
    if trade_p is None or next_p is None:
        return pd.Series(dtype=float)
    open_t = trade_p.reindex(symbols)["open"]
    open_next = next_p.reindex(symbols)["open"]
    missing = open_next[open_next.isna()].index
    if len(missing) > 0:
        last_avail = (
            ctx["prices"][
                ctx["prices"]["symbol"].isin(missing)
                & (ctx["prices"]["date"] <= next_trade)
            ]
            .sort_values("date")
            .groupby("symbol")["open"]
            .last()
        )
        open_next = open_next.fillna(last_avail)
    return (open_next / open_t - 1.0).replace([np.inf, -np.inf], np.nan).dropna()


def brinson_one_period(port_df, bench_w_sym, ind_sym, port_rets, bench_rets):
    """单期 Brinson。返回 dict(Rp, Rb, A, S, I, detail)。"""
    port_df = port_df.copy()
    port_df["industry"] = port_df["symbol"].map(lambda s: ind_sym.get(s, "未知"))

    bench_df = pd.DataFrame(
        {"symbol": list(bench_w_sym.keys()), "weight": list(bench_w_sym.values())}
    )
    bench_df["industry"] = bench_df["symbol"].map(lambda s: ind_sym.get(s, "未知"))

    industries = sorted(set(port_df["industry"]) | set(bench_df["industry"]))
    A = S = inter = Rp = Rb = 0.0  # 原来是 A = S = I = Rp = Rb = 0.0
    rows = []
    for i in industries:
        p = port_df[port_df["industry"] == i]
        b = bench_df[bench_df["industry"] == i]
        wp = float(p["weight"].sum())
        wb = float(b["weight"].sum())
        p_rets = port_rets.reindex(p["symbol"]).dropna()
        rp_i = float(p_rets.mean()) if len(p_rets) > 0 else 0.0
        b_rets = bench_rets.reindex(b["symbol"]).dropna()
        if len(b_rets) > 0:
            bw = b.set_index("symbol")["weight"].reindex(b_rets.index)
            rb_i = float((b_rets * bw).sum() / bw.sum()) if bw.sum() > 0 else 0.0
        else:
            rb_i = 0.0
        a = (wp - wb) * rb_i
        s = wb * (rp_i - rb_i)
        it = (wp - wb) * (rp_i - rb_i)
        A += a
        S += s
        inter += it  # 原来是 I += it
        Rp += wp * rp_i
        Rb += wb * rb_i
        rows.append(
            {
                "industry": i,
                "wp": wp,
                "wb": wb,
                "rp_i": rp_i,
                "rb_i": rb_i,
                "A": a,
                "S": s,
                "I": it,
            }
        )
    return {
        "Rp": Rp,
        "Rb": Rb,
        "A": A,
        "S": S,
        "I": inter,  # 原来是 "I": I
        "detail": pd.DataFrame(rows),
    }


def run(group, year=None):
    ctx = load_context()
    holdings = pd.read_csv(
        PROCESSED / f"composite_holdings_{group}.csv", dtype={"symbol": str}
    )
    holdings["symbol"] = holdings["symbol"].str.zfill(6)
    holdings["trade_date"] = pd.to_datetime(holdings["trade_date"])

    bt = pd.read_csv(PROCESSED / f"composite_bt_{group}.csv")
    bt["trade_date"] = pd.to_datetime(bt["trade_date"])
    bt["next_trade_date"] = pd.to_datetime(bt["next_trade_date"])
    bt["signal_date"] = pd.to_datetime(bt["signal_date"])
    if year is not None:
        bt = bt[bt["trade_date"].dt.year == year]

    records = []
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
        records.append(
            {
                "signal_date": sig,
                "trade_date": trade,
                "next_date": next_trade,
                "n_holdings": len(syms),
                "Rp": res["Rp"],
                "Rb": res["Rb"],
                "excess": res["Rp"] - res["Rb"],
                "A": res["A"],
                "S": res["S"],
                "I": res["I"],
                "residual": (res["Rp"] - res["Rb"]) - (res["A"] + res["S"] + res["I"]),
            }
        )

    out = pd.DataFrame(records)
    tag = f"{group}_{year}" if year else group
    out_path = PROCESSED / f"brinson_{tag}_v2.csv"
    out.to_csv(out_path, index=False)
    print(f"[OK] {len(out)} 期 -> {out_path}")
    show = ["trade_date", "Rp", "Rb", "excess", "A", "S", "I", "residual"]
    print(out[show].head(12).to_string())
    print(
        f"\n累计: Rp={out['Rp'].sum():.4f} Rb={out['Rb'].sum():.4f} "
        f"excess={out['excess'].sum():.4f}"
    )
    print(
        f"A={out['A'].sum():.4f} S={out['S'].sum():.4f} I={out['I'].sum():.4f} "
        f"residual={out['residual'].sum():.2e}"
    )
    return out


def compare_with_old(new_df, old_path):
    old = pd.read_csv(old_path)
    old["trade_date"] = pd.to_datetime(old["trade_date"])
    new_df = new_df.copy()
    new_df["trade_date"] = pd.to_datetime(new_df["trade_date"])
    m = new_df.merge(old, on="trade_date", suffixes=("_new", "_old"))
    print(f"\n对账旧结果 {len(m)} 期:")
    for col in ["Rp", "Rb", "A", "S", "I"]:
        if f"{col}_new" in m and f"{col}_old" in m:
            d = (m[f"{col}_new"] - m[f"{col}_old"]).abs()
            print(f"  {col}: max abs diff={d.max():.4e}, mean={d.mean():.4e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="lasso_horizon_all8")
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--compare", action="store_true")
    args = ap.parse_args()
    df = run(args.group, args.year)
    if args.compare:
        old_path = PROCESSED / f"brinson_{args.group}_{args.year}.csv"
        if old_path.exists():
            compare_with_old(df, old_path)


if __name__ == "__main__":
    main()
