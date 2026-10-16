"""M1-A: 拉取沪深 300 基准日线。

调用 Tushare index_daily 接口获取 000300.SH 的日线数据，
落盘为 data/processed/hs300_benchmark.parquet。

用法（项目根目录、激活 .venv 后）：
    python scripts/backtest/fetch_hs300.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))

try:
    import tushare as ts
except ImportError:
    print("请先安装 tushare：pip install tushare")
    raise

OUT_PATH = _ROOT / "data" / "processed" / "hs300_benchmark.parquet"

START_DATE = "20190930"
END_DATE = "20240930"
INDEX_CODE = "000300.SH"


def get_token() -> str:
    """从环境变量或 .env 读取 Tushare token。"""
    token = os.environ.get("TUSHARE_TOKEN", "")
    if token:
        return token
    env_path = _ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TUSHARE_TOKEN"):
                return line.split("=", 1)[1].strip().strip("\"'")
    raise RuntimeError(
        "未找到 TUSHARE_TOKEN。请在项目根目录 .env 文件里加一行：\n"
        "TUSHARE_TOKEN=你的token"
    )


def main() -> None:
    print("[M1-A] 拉取沪深 300 基准日线 ...")
    ts.set_token(get_token())
    pro = ts.pro_api()

    df = pro.index_daily(
        ts_code=INDEX_CODE,
        start_date=START_DATE,
        end_date=END_DATE,
    )
    if df is None or df.empty:
        raise RuntimeError("index_daily 返回空数据，请检查 token 权限或区间。")

    # Tushare 返回按 trade_date 倒序，改为正序
    df = df.sort_values("trade_date").reset_index(drop=True)

    # trade_date 从 "20190930" 字符串转 datetime
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")

    # 只保留需要的列
    keep_cols = [
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "pct_chg",
        "vol",
        "amount",
    ]
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols].copy()

    # 数值列转 float
    for c in df.columns:
        if c != "trade_date":
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.sort_values("trade_date").reset_index(drop=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)

    print(f"  保存到: {OUT_PATH}")
    print(f"  形状:   {df.shape}")
    print(
        f"  区间:   {df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}"
    )
    print(f"  列:     {list(df.columns)}")
    print("  head:")
    print(df.head(3).to_string())
    print("  tail:")
    print(df.tail(3).to_string())


if __name__ == "__main__":
    main()
