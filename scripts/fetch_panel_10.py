"""抓取 10 只 A 股日行情，落盘为面板 parquet（腾讯数据源）。

面板 = 多只股票纵向拼接，含 symbol 列，索引为 date。
输出：data/raw/daily_panel_10.parquet
"""

import sys
import time
from pathlib import Path

import akshare as ak
import pandas as pd

# scripts/ 下运行时把 src 加进 sys.path，才能 import mfalpha
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))  # noqa: E402

from mfalpha.common.constants import DATA_DIR  # noqa: E402

SYMBOLS = [
    "600519",  # 贵州茅台
    "000858",  # 五粮液
    "600036",  # 招商银行
    "601318",  # 中国平安
    "000333",  # 美的集团
    "600276",  # 恒瑞医药
    "600887",  # 伊利股份
    "000002",  # 万科A
    "601166",  # 兴业银行
    "600309",  # 万华化学
]


def to_tx_symbol(symbol: str) -> str:
    """把 6 位纯数字代码转换成腾讯接口需要的带前缀代码。

    6 开头 → sh（上交所），0/3 开头 → sz（深交所），4/8 开头 → bj（北交所）。

    Args:
        symbol: 6 位股票代码，如 "600519"。

    Returns:
        带市场前缀的代码，如 "sh600519"。
    """
    if symbol.startswith("6"):
        return f"sh{symbol}"
    if symbol.startswith(("0", "3")):
        return f"sz{symbol}"
    if symbol.startswith(("4", "8")):
        return f"bj{symbol}"
    return symbol


def fetch_one(symbol: str) -> pd.DataFrame:
    """抓取单只股票前复权日行情（腾讯数据源，带重试）。

    Args:
        symbol: 6 位股票代码，如 "600519"。

    Returns:
        含 symbol 列的日行情 DataFrame，日期为 DatetimeIndex。

    Raises:
        ValueError: 接口返回空数据时抛出。
        Exception: 3 次重试都失败后，抛出最后一次的异常。
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            raw = ak.stock_zh_a_hist_tx(
                symbol=to_tx_symbol(symbol),
                start_date="20190930",
                end_date="20240930",
                adjust="qfq",
            )
            if raw is None or raw.empty:
                raise ValueError(f"未获取到 {symbol} 的行情数据")
            break
        except Exception as e:
            print(
                f"  {symbol} 第 {attempt + 1}/{max_retries} 次失败: {type(e).__name__}"
            )
            if attempt == max_retries - 1:
                raise
            time.sleep(3)

    raw["date"] = pd.to_datetime(raw["date"])
    raw["symbol"] = symbol
    raw = raw.set_index("date").sort_index()
    return raw


def main() -> None:
    """抓 10 只股票并落盘到 data/raw/daily_panel_10.parquet。"""
    frames = []
    for sym in SYMBOLS:
        print(f"抓取 {sym} ...", flush=True)
        frames.append(fetch_one(sym))
        time.sleep(2)  # 免费接口礼貌限速

    panel = pd.concat(frames)
    panel = panel.sort_values(["symbol", "date"]).reset_index()

    out_path = DATA_DIR / "daily_panel_10.parquet"
    panel.to_parquet(out_path, index=False)
    print(f"已写入 {out_path}，shape = {panel.shape}")
    print("股票数 =", panel["symbol"].nunique())
    print("日期范围 =", panel["date"].min().date(), "~", panel["date"].max().date())


if __name__ == "__main__":
    main()
