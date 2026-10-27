"""M5.1c 口径对账：定位 Sharpe 偏差与日频/期频终值差异的根因。"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402

from scripts.backtest.engine import nav_stats  # noqa: E402

PROC = Path("data/processed")


def main() -> None:
    print("=" * 80)
    print("[1] engine.nav_stats 源码")
    print("=" * 80)
    print(inspect.getsource(nav_stats))

    print("=" * 80)
    print("[2] 用 nav_stats 直接对 baseline periods 重算")
    print("=" * 80)
    per = pd.read_csv(PROC / "composite_bt_lasso_horizon_all8.csv")
    nav = (1.0 + per["net_ret"]).cumprod()
    nav.index = pd.to_datetime(per["trade_date"])
    st = nav_stats(nav, periods_per_year=12.0)
    for k, v in st.items():
        print(f"  {k:<16} {v}")

    print("\n  对比：阶段三笔记 Sharpe = 1.4611，年化 = 0.5369")

    print("=" * 80)
    print("[3] 年化期数 n vs n-1 测试（定位 off-by-one）")
    print("=" * 80)
    r = per["net_ret"].astype(float)
    final = float((1.0 + r).cumprod().iloc[-1])
    vol = float(r.std(ddof=1) * 12.0**0.5)
    for n_eff in [len(r), len(r) - 1, len(r) - 2]:
        ann = final ** (12.0 / n_eff) - 1.0
        print(
            f"  n_eff={n_eff:<3d}  ann={ann:.4f}  "
            f"vol={vol:.4f}  sharpe={ann / vol:.4f}"
        )

    print("\n  若某 n_eff 的 ann≈0.5369、sharpe≈1.4611，即定位到阶段三口径。")

    print("=" * 80)
    print("[4] 日频 vs 期频收益对账（检查是否扣成本）")
    print("=" * 80)
    daily = pd.read_parquet(PROC / "bt_nav_lasso_horizon_all8_daily.parquet")
    dr = daily["daily_ret"].astype(float)
    print(f"  日频累计（net 口径）  : {float((1+dr).cumprod().iloc[-1]):.6f}")
    print(f"  期频累计 net_ret      : {final:.6f}")
    print(
        f"  期频累计 gross_ret    : {float((1+per['gross_ret']).cumprod().iloc[-1]):.6f}"
    )
    print(f"  期频成本累计          : {float(per['cost'].sum()):.6f}")
    print(
        "\n  若日频累计 ≈ 期频 gross 累计，说明日频未扣成本；"
        "\n  若日频累计 ≈ 期频 net 累计，说明口径一致，问题在别处。"
    )

    print("=" * 80)
    print("[5] 首尾日期与交易日对齐")
    print("=" * 80)
    print(
        f"  periods trade_date: "
        f"{per['trade_date'].iloc[0]} ~ {per['trade_date'].iloc[-1]}"
    )
    print(f"  daily   index     : {daily.index[0].date()} ~ {daily.index[-1].date()}")
    print(f"  periods n={len(per)}  daily n={len(daily)}")

    print("\n[完成] 把以上输出贴回。")


if __name__ == "__main__":
    main()
