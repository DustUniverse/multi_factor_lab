"""M4d 回测：只跑 ic_rotation_all8 对比组，裁剪到主线 51 期做公平对比。"""

import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"C:\Users\16075\code\multi_factor_lab"
sys.path.insert(0, os.path.join(ROOT, "scripts", "backtest"))
from engine import nav_stats, run_backtest  # noqa: E402

PROC = os.path.join(ROOT, "data", "processed")
PRICE_COLS = ["symbol", "date", "open", "close", "is_limit_up", "is_suspended"]


def normalize_symbol(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.split(".").str[0]
    return s.str.zfill(6)


def main() -> None:
    scores = pd.read_parquet(
        os.path.join(PROC, "composite_scores_ic_rotation_all8.parquet")
    )
    scores.index = pd.to_datetime(scores.index)

    cal = pd.read_csv(
        os.path.join(PROC, "rebalance_calendar.csv"),
        parse_dates=["signal_date", "trade_date"],
    )

    # 公平对比：裁到主线 51 个 signal_date
    main_periods = pd.read_csv(
        os.path.join(PROC, "m4_final_periods.csv"),
        parse_dates=["signal_date", "trade_date", "next_trade_date"],
    )
    main_sigs = set(main_periods["signal_date"])
    scores = scores.loc[scores.index.isin(main_sigs)]
    cal = cal[cal["signal_date"].isin(main_sigs)].reset_index(drop=True)
    print(f"[M4d-BT] 裁剪后 scores: {scores.shape}, cal: {cal.shape}")

    px = pd.read_parquet(
        os.path.join(PROC, "daily_panel_tencent_clean.parquet"), columns=PRICE_COLS
    )
    px["symbol"] = normalize_symbol(px["symbol"])
    px["date"] = pd.to_datetime(px["date"])

    print("[M4d-BT] 回测 ic_rotation_all8（51 期公平对比）...")
    result = run_backtest(
        scores=scores,
        calendar=cal,
        prices=px,
        top_n=50,
        buffer_n=0,
        cost_per_side=0.003,
        slippage_per_side=0.001,
        position_series=None,
    )
    print("[M4d-BT] result keys:", list(result.keys()))

    nav = pd.Series(result["nav"]).astype(float)
    st = nav_stats(nav, periods_per_year=12)
    print("[M4d-BT] stats:")
    for k, v in st.items():
        print(f"  {k}: {v}")

    out = os.path.join(PROC, "m4d_ic_rotation_perf_51.csv")
    pd.DataFrame([st]).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"[M4d-BT] 已写 {out}")


if __name__ == "__main__":
    main()
