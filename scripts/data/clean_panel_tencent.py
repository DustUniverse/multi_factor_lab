"""对腾讯日线面板做最小化清洗：加标记，不删行。

输入：data/processed/daily_panel_tencent.parquet
输出：data/processed/daily_panel_tencent_clean.parquet

处理内容：
1. symbol 统一为 6 位字符串
2. 按 symbol 分组计算 pct_chg（%）
3. 加 board（主板/创业板/科创板）
4. 加 is_suspended（成交量为 0）
5. 加 is_limit_up / is_limit_down（按板块判断涨跌幅限制）
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mfalpha.common.constants import DATA_DIR  # noqa: E402

PROCESSED_DIR = DATA_DIR.parent / "processed"


def classify_board(symbol: str) -> str:
    """按代码前缀判断板块。"""
    if symbol.startswith(("688", "689")):
        return "科创板"  # 20% 涨跌幅
    if symbol.startswith("30"):
        return "创业板"  # 20% 涨跌幅
    if symbol.startswith(("00", "60")):
        return "主板"  # 10% 涨跌幅
    return "其他"


def get_limit(board: str) -> float:
    """不同板块涨跌幅限制（百分比）。"""
    if board in ("科创板", "创业板"):
        return 20.0
    return 10.0


def main() -> None:
    t0 = time.time()
    src = PROCESSED_DIR / "daily_panel_tencent.parquet"
    dst = PROCESSED_DIR / "daily_panel_tencent_clean.parquet"

    df = pd.read_parquet(src)
    print(f"读取面板：{df.shape}  用时 {time.time() - t0:.1f}s")

    # 1. symbol 统一为 6 位字符串
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)

    # 1b. 剔除前复权负价格（长期高分红股的数学必然，无意义）
    n_before = len(df)
    df = df[df["close"] > 0].reset_index(drop=True)
    n_drop = n_before - len(df)
    print(f"剔除 close <= 0 的行：{n_drop} 行，剩余 {len(df):,} 行")

    # 2. 按 symbol 分组计算 pct_chg（前收盘 -> 今收盘，单位 %）
    print("计算 pct_chg ...")
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    prev_close = df.groupby("symbol")["close"].shift(1)
    df["pct_chg"] = (df["close"] / prev_close - 1) * 100
    # 每只股票第一个交易日没有前收盘，pct_chg 为 NaN，保持 NaN

    # 2b. 剔除 |pct_chg| > 21% 的行（前复权精度陷阱，A 股单日最大 20%）
    n_before = len(df)
    df = df[df["pct_chg"].isna() | (df["pct_chg"].abs() <= 21)].reset_index(drop=True)
    n_drop = n_before - len(df)
    print(f"剔除 |pct_chg| > 21% 的行：{n_drop} 行，剩余 {len(df):,} 行")

    # 3. 板块
    print("标记板块 ...")
    df["board"] = df["symbol"].map(classify_board)

    # 4. 停牌标记
    df["is_suspended"] = df["volume"] == 0

    # 5. 涨跌停标记（用涨跌幅阈值判断，留 0.5% 余量避免精度问题）
    print("标记涨跌停 ...")
    limit = df["board"].map(get_limit)
    df["is_limit_up"] = df["pct_chg"] >= (limit - 0.5)
    df["is_limit_down"] = df["pct_chg"] <= -(limit - 0.5)
    # NaN 的比较结果是 False，即新股首日不会被标记，符合预期

    # 汇总
    print(f"\n清洗完成，输出形状：{df.shape}")
    print(f"  停牌行数：{int(df['is_suspended'].sum()):,}")
    print(f"  涨停行数：{int(df['is_limit_up'].sum()):,}")
    print(f"  跌停行数：{int(df['is_limit_down'].sum()):,}")
    print(
        f"  pct_chg NaN 行数：{int(df['pct_chg'].isna().sum()):,}（应为股票数 ~4853）"
    )

    dst.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dst, index=False)
    print(f"\n已写入：{dst}")
    print(f"总用时：{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
