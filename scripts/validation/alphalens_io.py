"""alphalens 输入构造工具：把项目里的 parquet 面板转成 alphalens 需要的输入。

alphalens-reloaded 的两个核心输入：
- prices:  DataFrame，index = DatetimeIndex，columns = asset（这里用 6 位 symbol），values = 收盘价
- factor:  pd.Series，MultiIndex = (date, asset)，values = 因子值

本模块只负责构造输入，不做检验、不落盘。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# 项目根目录：本文件位于 scripts/validation/ 下，向上两级即根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

FACTOR_PANEL_PATH = PROCESSED_DIR / "factor_panel.parquet"
PRICE_PANEL_PATH = PROCESSED_DIR / "daily_panel_tencent_clean.parquet"

# 18 个基础因子
FACTOR_COLUMNS = [
    "momentum_20",
    "reversal_20",
    "volatility_20",
    "corr_pv_20",
    "volume_ratio",
    "amplitude_20",
    "amihud_20",
    "rsi_14",
    "bias_20",
    "boll_dev_20",
    "macd_dev",
    "roe",
    "netprofit_yoy",
    "or_yoy",
    "debt_to_assets",
    "ep_ttm",
    "bp",
    "turnover",
]


def _normalize_symbol(s: pd.Series) -> pd.Series:
    """把各种 symbol 形式统一成 6 位数字字符串（去掉 .SH / .SZ / .BJ 后缀）。

    000001.SZ -> 000001
    000001    -> 000001
    """
    s = s.astype(str).str.strip()
    # 去掉后缀
    s = s.str.split(".").str[0]
    # 补零到 6 位
    s = s.str.zfill(6)
    return s


def load_prices() -> pd.DataFrame:
    """从 daily_panel 读出 close，构造 date × symbol 的价格矩阵。"""
    df = pd.read_parquet(PRICE_PANEL_PATH, columns=["symbol", "date", "close"])
    df["symbol"] = _normalize_symbol(df["symbol"])
    df["date"] = pd.to_datetime(df["date"])

    prices = df.pivot(index="date", columns="symbol", values="close")
    prices = prices.sort_index().sort_index(axis=1)
    return prices


def load_factor_series(factor_name: str) -> pd.Series:
    """从 factor_panel 读出某个因子，返回 MultiIndex (date, asset) 的 Series。

    参数
    ----
    factor_name : str
        必须属于 FACTOR_COLUMNS 之一。

    返回
    ----
    pd.Series
        index = MultiIndex [date, asset]，values = 因子值，已去除 NaN。
    """
    if factor_name not in FACTOR_COLUMNS:
        raise ValueError(f"未知因子 {factor_name!r}，可选：{FACTOR_COLUMNS}")

    df = pd.read_parquet(FACTOR_PANEL_PATH, columns=["symbol", "date", factor_name])
    df["symbol"] = _normalize_symbol(df["symbol"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=[factor_name])

    series = df.set_index(["date", "symbol"])[factor_name]
    series.name = factor_name
    series = series.sort_index()
    return series


def load_all_factors() -> dict[str, pd.Series]:
    """一次性把所有因子读成 {factor_name: MultiIndex Series}。"""
    return {name: load_factor_series(name) for name in FACTOR_COLUMNS}


if __name__ == "__main__":
    # 简单自检
    prices = load_prices()
    print("prices shape :", prices.shape)
    print("prices index :", prices.index.min().date(), "~", prices.index.max().date())
    print("prices columns (前 5):", list(prices.columns[:5]))

    s = load_factor_series("momentum_20")
    print("factor series shape :", s.shape)
    print("factor index levels :", s.index.names)
    print(s.head(3))
