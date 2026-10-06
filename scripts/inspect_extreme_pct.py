"""排查 pct_chg 极端值（绝对值 > 21），定位是哪几只股票、什么时候。

用法：
    python scripts/inspect_extreme_pct.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "processed" / "daily_panel_tencent_clean.parquet"


def main() -> None:
    df = pd.read_parquet(SRC)
    ext = df[df["pct_chg"].abs() > 21].copy()
    print(
        f"pct_chg 绝对值 > 21 共 {len(ext)} 行，涉及 {ext['symbol'].nunique()} 只股票\n"
    )

    print("按股票统计（数量最多的 20 只）：")
    cnt = ext.groupby("symbol").size().sort_values(ascending=False)
    print(cnt.head(20).to_string())

    print("\n按板块分布：")
    print(ext["board"].value_counts().to_string())

    print("\n按年份分布：")
    print(ext["date"].dt.year.value_counts().sort_index().to_string())

    print("\npct_chg 分布：")
    print(ext["pct_chg"].describe().to_string())

    print("\n最极端的 10 行：")
    top10 = ext.reindex(ext["pct_chg"].abs().sort_values(ascending=False).index).head(
        10
    )
    print(top10[["symbol", "date", "close", "pct_chg", "board"]].to_string())

    # 挑一只异常最多的股票，打印它异常前后的 5 行
    if len(cnt) > 0:
        worst = cnt.index[0]
        print(f"\n异常最多的股票 {worst} 的前后 5 行：")
        s = df[df["symbol"] == worst].sort_values("date").reset_index(drop=True)
        idxs = ext[ext["symbol"] == worst].index
        for idx in list(idxs)[:3]:
            pos = s.index[s["date"] == df.loc[idx, "date"]]
            if len(pos) > 0:
                p = pos[0]
                print(
                    s.iloc[max(0, p - 2) : p + 3][
                        ["date", "close", "pct_chg"]
                    ].to_string()
                )
                print()


if __name__ == "__main__":
    main()
