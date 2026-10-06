"""抽查 daily_tencent 下的 parquet 文件，确认列名和 dtype 一致。

用法：
    python scripts/inspect_tencent_files.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "data" / "raw" / "daily_tencent"


def main() -> None:
    files = sorted(DAILY_DIR.glob("*.parquet"))
    print(f"文件总数：{len(files)}")

    # 抽 3 个：首、中、尾
    picks = [files[0], files[len(files) // 2], files[-1]]
    for p in picks:
        df = pd.read_parquet(p)
        print(f"\n--- {p.name} ---")
        print(f"行数：{len(df)}")
        print(f"列名：{list(df.columns)}")
        print(f"dtypes：\n{df.dtypes}")
        print(f"日期范围：{df['date'].min()} ~ {df['date'].max()}")
        print(f"前 2 行：\n{df.head(2)}")


if __name__ == "__main__":
    main()
