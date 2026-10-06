"""把 daily_tencent/ 下的单股 parquet 拼成完整面板。

用法：
    python scripts/build_daily_panel_tencent.py

输出：
    data/processed/daily_panel_tencent.parquet
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DAILY_DIR = ROOT / "data" / "raw" / "daily_tencent"
OUT_PATH = ROOT / "data" / "processed" / "daily_panel_tencent.parquet"


def main() -> None:
    files = sorted(DAILY_DIR.glob("*.parquet"))
    print(f"待拼合文件数：{len(files)}")

    frames = []
    t0 = time.time()
    for i, p in enumerate(files, 1):
        df = pd.read_parquet(p)
        frames.append(df)
        if i % 500 == 0:
            print(f"  已读取 {i}/{len(files)}  用时 {time.time() - t0:.1f}s")

    print("\n开始 concat ...")
    panel = pd.concat(frames, ignore_index=True)
    print(f"拼合完成：{len(panel):,} 行 × {len(panel.columns)} 列")

    # 排序 + 去重
    panel = panel.sort_values(["symbol", "date"]).reset_index(drop=True)
    panel = panel.drop_duplicates(subset=["symbol", "date"]).reset_index(drop=True)
    print(f"排序去重后：{len(panel):,} 行")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT_PATH, index=False)
    print(f"\n已写入：{OUT_PATH}")
    print(f"日期范围：{panel['date'].min().date()} ~ {panel['date'].max().date()}")
    print(f"股票数：{panel['symbol'].nunique()}")
    print(f"总用时：{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
