"""批量抓取沪深 A 股日频行情（前复权）。

数据源：东方财富 K 线接口（绕过 AKShare，直连更稳定）
输入：data/raw/universe.parquet
输出：data/raw/daily/{symbol}.parquet（按股票一只一个文件）

支持断点续传：已存在的文件默认跳过。
"""

import argparse
import random
import sys
import time
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mfalpha.common.constants import DATA_DIR  # noqa: E402

DAILY_DIR = DATA_DIR / "daily"
KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"


def build_secid(symbol: str) -> str:
    """把 6 位代码转成东财 secid。6 开头为沪市(1.)，其余为深市(0.)。"""
    symbol = str(symbol).zfill(6)
    market = "1" if symbol.startswith("6") else "0"
    return f"{market}.{symbol}"


def fetch_one(symbol: str, start: str, end: str, max_retry: int = 3):
    """抓取单只股票日线，失败返回 None。"""
    params = {
        "secid": build_secid(symbol),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "beg": start,
        "end": end,
        "lmt": "10000",
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://quote.eastmoney.com/",
    }

    for attempt in range(max_retry):
        try:
            r = requests.get(KLINE_URL, params=params, headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            klines = data.get("data", {}).get("klines") if data.get("data") else None
            if not klines:
                return None

            rows = [line.split(",") for line in klines]
            df = pd.DataFrame(
                rows,
                columns=[
                    "date",
                    "open",
                    "close",
                    "high",
                    "low",
                    "volume",
                    "amount",
                    "amplitude",
                    "pct_chg",
                    "change",
                    "turnover",
                ],
            )
            df["date"] = pd.to_datetime(df["date"])
            for col in df.columns[1:]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["symbol"] = str(symbol).zfill(6)
            return df
        except Exception as e:
            wait = 2 * (attempt + 1) + random.uniform(0, 1)
            print(f"    第 {attempt+1} 次失败: {e}，等 {wait:.1f}s 重试")
            time.sleep(wait)

    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="20190930", help="起始日期 YYYYMMDD")
    parser.add_argument("--end", default="20240930", help="结束日期 YYYYMMDD")
    parser.add_argument("--limit", type=int, default=None, help="只抓前 N 只")
    parser.add_argument("--sleep", type=float, default=3.0, help="每只间隔秒数")
    parser.add_argument("--force", action="store_true", help="已存在也重抓")
    args = parser.parse_args()

    universe = pd.read_parquet(DATA_DIR / "universe.parquet")
    if args.limit:
        universe = universe.head(args.limit)
    print(f"待抓股票数: {len(universe)}")

    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    success, skip, fail = 0, 0, 0
    fail_list = []
    consecutive_fail = 0

    for i, row in universe.iterrows():
        symbol = str(row["symbol"]).zfill(6)
        out_path = DAILY_DIR / f"{symbol}.parquet"

        if out_path.exists() and not args.force:
            skip += 1
            continue

        print(f"[{i+1}/{len(universe)}] {symbol} {row['name']}", end=" ")
        df = fetch_one(symbol, args.start, args.end)
        if df is None:
            print("空")
            fail += 1
            fail_list.append(symbol)
            consecutive_fail += 1
        else:
            df.to_parquet(out_path, index=False)
            print(f"{len(df)} 行")
            success += 1
            consecutive_fail = 0

        # 连续失败 3 只，暂停 30 秒
        if consecutive_fail >= 3:
            print("    ⚠ 连续失败 3 只，暂停 30 秒让 IP 冷却...")
            time.sleep(30)
            consecutive_fail = 0

        # 随机间隔，避免固定节奏被识别
        time.sleep(args.sleep + random.uniform(0, 0.5))

    print("\n=== 完成 ===")
    print(f"成功: {success}, 跳过: {skip}, 失败: {fail}")
    if fail_list:
        print(f"失败列表: {fail_list[:20]}{'...' if len(fail_list) > 20 else ''}")


if __name__ == "__main__":
    main()
