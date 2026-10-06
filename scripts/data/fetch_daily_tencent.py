"""腾讯日线抓取脚本（前复权，分段拼合，支持断点续传）。

用法：
    # 先测 5 只（推荐第一次这么跑）
    python scripts/fetch_daily_tencent.py --limit 5

    # 全量（5000+ 只，预计 2~3 小时）
    python scripts/fetch_daily_tencent.py

数据源：腾讯 https://web.ifzq.gtimg.cn/appstock/app/fqkline/get
字段顺序（腾讯原始）：[date, open, close, high, low, volume]
输出字段：symbol, date, open, high, low, close, volume
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import requests

# ---------- 路径 ----------
ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = ROOT / "data" / "raw" / "universe.parquet"
OUT_DIR = ROOT / "data" / "raw" / "daily_tencent"

# ---------- 参数 ----------
START = "2019-09-30"
END = "2024-09-30"

# 分段：每段 <= 640 交易日，避免腾讯单次 640 上限
SEGMENTS = [
    ("2019-09-30", "2021-09-30"),
    ("2021-10-01", "2023-09-30"),
    ("2023-10-01", "2024-09-30"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://gu.qq.com/",
}
URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

# 请求间隔（秒），腾讯不激进，0.5 够了
SLEEP_BETWEEN_SEGMENTS = 0.3  # 同一只股票段与段之间
SLEEP_BETWEEN_STOCKS = 0.5  # 股票与股票之间


def symbol_to_tencent(symbol: str) -> str:
    """把 6 位代码转成腾讯格式：沪市 6 开头 -> sh，其他 -> sz。"""
    return f"sh{symbol}" if symbol.startswith("6") else f"sz{symbol}"


def fetch_segment(code: str, start: str, end: str, retries: int = 3) -> list:
    """抓单段，失败重试 retries 次。"""
    params = {"param": f"{code},day,{start},{end},640,qfq"}
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(URL, params=params, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            node = (data.get("data") or {}).get(code) or {}
            return node.get("qfqday") or node.get("day") or []
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(2)
    raise RuntimeError(f"{code} {start}~{end} 抓取失败：{last_err}")


def fetch_one(symbol: str) -> pd.DataFrame | None:
    """抓一只股票的全部 3 段并拼合。失败返回 None。"""
    code = symbol_to_tencent(symbol)
    all_rows: list = []
    for start, end in SEGMENTS:
        try:
            rows = fetch_segment(code, start, end)
            all_rows.extend(rows)
        except Exception as e:
            print(f"    ! 段 {start}~{end} 失败：{e}")
        time.sleep(SLEEP_BETWEEN_SEGMENTS)

    if not all_rows:
        return None

        # 腾讯部分股票每行会多返回一个"成交额"字段，统一只取前 6 列
    rows_6col = [row[:6] for row in all_rows]
    df = pd.DataFrame(
        rows_6col,
        columns=["date", "open", "close", "high", "low", "volume"],
    )
    df = df.drop_duplicates(subset="date").sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "close", "high", "low", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.insert(0, "symbol", symbol)
    # 调整列顺序，和后续面板习惯一致
    df = df[["symbol", "date", "open", "high", "low", "close", "volume"]]
    return df


def load_symbols() -> list[str]:
    df = pd.read_parquet(UNIVERSE_PATH)
    for col in ["symbol", "code"]:
        if col in df.columns:
            return df[col].astype(str).tolist()
    raise ValueError(
        f"universe.parquet 找不到 symbol/code 列，实际列：{list(df.columns)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只抓前 N 只（测试用）")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    symbols = load_symbols()
    if args.limit:
        symbols = symbols[: args.limit]

    total = len(symbols)
    print(f"共 {total} 只股票，输出目录：{OUT_DIR}")
    print(f"时间范围：{START} ~ {END}（前复权）\n")

    ok = skip = fail = 0
    t_start = time.time()
    for i, symbol in enumerate(symbols, 1):
        out_path = OUT_DIR / f"{symbol}.parquet"
        if out_path.exists():
            skip += 1
            print(f"[{i:>4}/{total}] {symbol}  已存在，跳过")
            continue

        t0 = time.time()
        try:
            df = fetch_one(symbol)
            if df is None or df.empty:
                fail += 1
                print(f"[{i:>4}/{total}] {symbol}  无数据")
            else:
                df.to_parquet(out_path, index=False)
                ok += 1
                print(
                    f"[{i:>4}/{total}] {symbol}  {len(df):>4} 行  "
                    f"{df['date'].min().date()} ~ {df['date'].max().date()}  "
                    f"{time.time() - t0:.2f}s"
                )
        except Exception as e:
            fail += 1
            print(f"[{i:>4}/{total}] {symbol}  失败：{e}")

        time.sleep(SLEEP_BETWEEN_STOCKS)

    elapsed = time.time() - t_start
    print(f"\n完成：成功 {ok}  跳过 {skip}  失败 {fail}  用时 {elapsed/60:.1f} 分钟")


if __name__ == "__main__":
    main()
