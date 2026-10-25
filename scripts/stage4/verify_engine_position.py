"""M4a: 验证 engine.py 的 position_series 改动向后兼容。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from scripts.backtest.engine import run_backtest  # noqa: E402


def make_synthetic():
    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2020-01-01", periods=30)
    symbols = [f"S{i:02d}" for i in range(10)]
    calendar = pd.DataFrame({"signal_date": dates[:-1], "trade_date": dates[1:]})
    scores = pd.DataFrame(
        rng.standard_normal((len(dates), len(symbols))), index=dates, columns=symbols
    )
    rows = []
    for d in dates:
        for s in symbols:
            rows.append(
                {
                    "symbol": s,
                    "date": d,
                    "open": 10 + rng.standard_normal(),
                    "is_limit_up": False,
                    "is_suspended": False,
                }
            )
    prices = pd.DataFrame(rows)
    return scores, calendar, prices


def main():
    scores, calendar, prices = make_synthetic()

    # 1) 不传 position_series：应与"无 pos 逻辑"完全一致
    r_none = run_backtest(scores, calendar, prices, top_n=5)
    print("None: n_periods =", len(r_none["periods"]))
    print(
        r_none["periods"][
            ["trade_date", "gross_ret", "turnover", "cost", "net_ret", "pos"]
        ].head()
    )

    # 2) 传满仓序列：应与 None 完全相等
    pos_full = pd.Series(1.0, index=pd.to_datetime(calendar["trade_date"]))
    r_full = run_backtest(scores, calendar, prices, top_n=5, position_series=pos_full)
    assert np.allclose(
        r_none["periods"]["net_ret"], r_full["periods"]["net_ret"]
    ), "满仓序列应与 None 等价"
    print("OK: position_series=1.0 与 None 完全等价")

    # 3) 传半仓序列：net_ret 应约为 0.5×gross - 半仓换手成本
    pos_half = pd.Series(0.5, index=pd.to_datetime(calendar["trade_date"]))
    r_half = run_backtest(scores, calendar, prices, top_n=5, position_series=pos_half)
    p = r_half["periods"]
    assert np.allclose(p["pos"], 0.5), "pos 列应全为 0.5"
    # 首期无 pos_cost；后续 pos 恒 0.5 → pos_cost=0
    assert np.allclose(
        p["cost"], p["turnover"] * 2.0 * 0.004 * 0.5
    ), "成本应按 0.5 缩放"
    print("OK: 半仓成本按 0.5 缩放，pos 列正确")
    print("\n全部通过。")


if __name__ == "__main__":
    main()
