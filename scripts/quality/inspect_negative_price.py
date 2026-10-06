"""排查 close <= 0 的行，确认是前复权负价格还是数据错误。

用法：
    python scripts/inspect_negative_price.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "processed" / "daily_panel_tencent_clean.parquet"


def main() -> None:
    df = pd.read_parquet(SRC)

    neg = df[df["close"] <= 0].copy()
    print(f"close <= 0 共 {len(neg)} 行，涉及 {neg['symbol'].nunique()} 只股票\n")

    print("涉及股票数最多的 20 只：")
    cnt = neg.groupby("symbol").size().sort_values(ascending=False)
    print(cnt.head(20).to_string())

    print("\n随便挑一只看它的历史（前后 5 行）：")
    sample_symbol = cnt.index[0]
    s = df[df["symbol"] == sample_symbol].sort_values("date")
    neg_dates = neg[neg["symbol"] == sample_symbol]["date"]
    idx = s.index[s["date"] == neg_dates.iloc[0]][0]
    pos = s.index.get_loc(idx)
    print(f"symbol = {sample_symbol}")
    print(
        s.iloc[max(0, pos - 3) : pos + 4][
            ["symbol", "date", "close", "pct_chg"]
        ].to_string()
    )

    print("\n负价格股票按板块分布：")
    print(neg["board"].value_counts().to_string())

    print("\n负价格日期分布（按年）：")
    print(neg["date"].dt.year.value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
