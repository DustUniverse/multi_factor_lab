"""从 stock_list.parquet 构建干净的股票池。

过滤规则：
1. 剔除退市股票（list_status == 'D'）
2. 剔除 ST/*ST（is_st == True）
3. 仅保留沪深 A 股（symbol 以 0/3/6 开头）

输出：data/raw/universe.parquet
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mfalpha.common.constants import DATA_DIR  # noqa: E402


def main() -> None:
    src = DATA_DIR / "stock_list.parquet"
    df = pd.read_parquet(src)
    print(f"读取全量股票列表: {len(df)} 只")

    # 1. 剔除退市
    df = df[df["list_status"] == "L"].copy()
    print(f"  剔除退市后: {len(df)} 只")

    # 2. 剔除 ST/*ST
    df = df[~df["is_st"]].copy()
    print(f"  剔除 ST/*ST 后: {len(df)} 只")

    # 3. 仅保留沪深 A 股（0=深主板/中小板，3=创业板，6=沪主板/科创板）
    df = df[df["symbol"].str.match(r"^(0|3|6)\d{5}$")].copy()
    print(f"  仅保留沪深 A 股后: {len(df)} 只")

    # 重置索引
    df = df.reset_index(drop=True)

    out_path = DATA_DIR / "universe.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\n已保存到: {out_path}")
    print("\n前 5 行预览：")
    print(df.head())

    # 按交易所统计
    df["exchange"] = df["symbol"].str[:1].map({"0": "深市", "3": "创业板", "6": "沪市"})
    print("\n按板块统计：")
    print(df["exchange"].value_counts())


if __name__ == "__main__":
    main()
