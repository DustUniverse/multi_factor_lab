"""列出 universe 里没有成功抓到数据的股票，按板块分类，判断原因。

用法：
    python scripts/check_missing.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = ROOT / "data" / "raw" / "universe.parquet"
DAILY_DIR = ROOT / "data" / "raw" / "daily_tencent"


def classify(symbol: str) -> str:
    if symbol.startswith("688"):
        return "科创板 688"
    if symbol.startswith("689"):
        return "科创板 689"
    if symbol.startswith("60"):
        return "沪市主板 60"
    if symbol.startswith("00"):
        return "深市主板 00"
    if symbol.startswith("30"):
        return "创业板 30"
    if symbol.startswith(("8", "4")):
        return "北交所/新三板"
    return "其他"


def main() -> None:
    uni = pd.read_parquet(UNIVERSE_PATH)
    col = "symbol" if "symbol" in uni.columns else "code"
    symbols = uni[col].astype(str).str.zfill(6).tolist()

    have = {p.stem for p in DAILY_DIR.glob("*.parquet")}
    missing = [s for s in symbols if s not in have]

    print(f"universe 共 {len(symbols)} 只")
    print(f"已抓     {len(have)} 只")
    print(f"缺失     {len(missing)} 只\n")

    # 按板块分类统计
    from collections import Counter

    counter = Counter(classify(s) for s in missing)
    print("缺失股票按板块分布：")
    for k, v in sorted(counter.items(), key=lambda x: -x[1]):
        print(f"  {k:<18} {v:>4} 只")

    print("\n前 60 个缺失代码：")
    for i, s in enumerate(missing[:60], 1):
        print(f"  {i:>3}. {s}  ({classify(s)})")

    # 导出到文件，后面补抓用
    out = ROOT / "data" / "raw" / "missing_symbols.txt"
    out.write_text("\n".join(missing), encoding="utf-8")
    print(f"\n完整缺失列表已写入：{out}")


if __name__ == "__main__":
    main()
