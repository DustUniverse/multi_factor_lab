"""拉取单只股票五年日行情（前复权）并落盘。

Usage:
    python scripts/fetch_single_stock.py
"""

import sys
from pathlib import Path

import akshare as ak
import pandas as pd

# --- 让 Python 找到 src/mfalpha ---
# 本文件位于 scripts/ 下，上一级是项目根。
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mfalpha.common.constants import DATA_DIR  # noqa: E402

# 接口返回的中文列名 → 英文蛇形命名
COLUMN_MAP: dict[str, str] = {
    "日期": "date",
    "股票代码": "code",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "pct_chg",
    "涨跌额": "change",
    "换手率": "turnover",
}


def fetch_daily(symbol: str, start: str, end: str) -> pd.DataFrame:
    """拉取前复权日行情并整理成规范 DataFrame。

    Args:
        symbol: 六位股票代码，如 "600519"。
        start: 开始日期，YYYYMMDD 格式字符串。
        end: 结束日期，YYYYMMDD 格式字符串。

    Returns:
        按日期升序的行情表，DatetimeIndex 名为 date，
        列为英文蛇形命名。

    Raises:
        ValueError: 接口返回空数据时抛出（不静默吞异常）。
    """
    raw = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start,
        end_date=end,
        adjust="qfq",
    )
    if raw.empty:
        raise ValueError(f"接口未返回 {symbol} 的行情数据，请检查代码与日期区间")

    df = raw.rename(columns=COLUMN_MAP)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df = df.drop(columns=["code"])  # symbol 参数已记录代码，code 列冗余
    df["symbol"] = symbol
    return df


def main() -> None:
    """脚本入口：拉取 600519 五年日行情并保存为 parquet。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)  # 路径不存在则创建
    df = fetch_daily("600519", "20190930", "20240930")
    out = DATA_DIR / "daily_600519.parquet"
    df.to_parquet(out)
    print(f"已保存 {len(df)} 行 → {out}")
    print(f"日期范围：{df.index.min().date()} ~ {df.index.max().date()}")
    print(df.head(3))


if __name__ == "__main__":
    main()
