"""把单股日线文件拼合成一张大面板。

输入：data/raw/daily/*.parquet
输出：data/processed/daily_panel.parquet
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mfalpha.common.constants import DATA_DIR  # noqa: E402

DAILY_DIR = DATA_DIR / "daily"
OUT_DIR = DATA_DIR.parent / "processed"  # data/processed


def main() -> None:
    files = sorted(DAILY_DIR.glob("*.parquet"))
    print(f"读取 {len(files)} 个单股文件")

    dfs = []
    for f in files:
        df = pd.read_parquet(f)
        dfs.append(df)

    panel = pd.concat(dfs, ignore_index=True)
    panel = panel.sort_values(["date", "symbol"]).reset_index(drop=True)

    print(f"面板形状: {panel.shape}")
    print(f"股票数: {panel['symbol'].nunique()}")
    print(f"交易日数: {panel['date'].nunique()}")
    print(f"日期范围: {panel['date'].min()} ~ {panel['date'].max()}")
    print("\n各列缺失率:")
    print(panel.isna().mean().round(4))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "daily_panel.parquet"
    panel.to_parquet(out_path, index=False)
    print(f"\n已保存到: {out_path}")


if __name__ == "__main__":
    main()
