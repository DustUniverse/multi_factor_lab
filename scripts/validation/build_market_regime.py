"""
M6 S1a: 构建等权市场指数并探查滚动收益分布

目的：为"牛/熊/震荡"划分标准提供数据依据。
本脚本只打印统计量，不落盘。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRICE_PATH = PROJECT_ROOT / "data" / "processed" / "daily_panel_tencent_clean.parquet"


def load_prices(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(
        path,
        columns=["symbol", "date", "close", "pct_chg", "is_suspended"],
    )
    df["date"] = pd.to_datetime(df["date"])
    return df


def build_equal_weight_index(
    df: pd.DataFrame, exclude_suspended: bool = True
) -> pd.Series:
    """等权市场指数：每日全市场股票 pct_chg 的等权均值，累乘得到净值。"""
    work = df.copy()
    if exclude_suspended:
        work = work[~work["is_suspended"]]
    work = work.dropna(subset=["pct_chg"])
    # pct_chg 单位是百分比，转成小数；按日横截面等权平均
    daily_ret = work.groupby("date")["pct_chg"].mean() / 100.0
    daily_ret = daily_ret.sort_index()
    nav = (1.0 + daily_ret).cumprod()
    return nav


def describe_rolling(nav: pd.Series, window: int) -> pd.Series:
    """打印某个窗口的滚动收益分布；返回该滚动收益 Series。"""
    r = nav / nav.shift(window) - 1.0
    valid = r.dropna()

    print(f"\n  --- 窗口 {window} 日 ---")
    print(f"  有效天数: {len(valid)}")
    if len(valid) == 0:
        print("  [跳过] 有效天数不足，无法计算分位数。")
        return r

    print(f"  describe:\n{valid.describe().round(4)}")
    qs = np.percentile(valid.to_numpy(), [10, 25, 50, 75, 90])
    print(f"  分位数 [10,25,50,75,90]%: {np.round(qs, 4)}")
    return r


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="只用前 1 年数据快速验证")
    args = parser.parse_args()

    print(f"[1/4] 读取价格面板: {PRICE_PATH}")
    df = load_prices(PRICE_PATH)
    print(f"      原始 shape: {df.shape}")
    print(f"      日期范围: {df['date'].min().date()} ~ {df['date'].max().date()}")

    if args.smoke:
        # 用 DateOffset 避免 numpy timedelta 的弃用警告
        cutoff = df["date"].min() + pd.DateOffset(days=365)
        df = df[df["date"] <= cutoff]
        print(f"      [smoke] 截取到 {cutoff.date()}, shape: {df.shape}")

    print("[2/4] 构建等权市场指数（剔除停牌 / 剔除 pct_chg NaN）")
    nav = build_equal_weight_index(df)
    print(f"      指数序列长度: {len(nav)}")
    print(f"      首日: {nav.index[0].date()}  nav={nav.iloc[0]:.4f}")
    print(f"      末日: {nav.index[-1].date()}  nav={nav.iloc[-1]:.4f}")
    print(f"      期间总收益: {(nav.iloc[-1] / nav.iloc[0] - 1) * 100:.2f}%")

    print("[3/4] 计算滚动收益 (60/120/250 日)")
    rets: dict[int, pd.Series] = {}
    for w in (60, 120, 250):
        rets[w] = describe_rolling(nav, w)

    print("\n[4/4] 参考：若按 ±10% 阈值划分（仅基于 120 日窗口）")
    r120 = rets[120].dropna()
    if len(r120) == 0:
        print("  120 日窗口无有效数据，跳过。")
    else:
        n_bull = int((r120 > 0.10).sum())
        n_bear = int((r120 < -0.10).sum())
        n_flat = len(r120) - n_bull - n_bear
        print(f"  牛 (>+10%): {n_bull} 天 ({n_bull / len(r120) * 100:.1f}%)")
        print(f"  熊 (<-10%): {n_bear} 天 ({n_bear / len(r120) * 100:.1f}%)")
        print(f"  震荡:       {n_flat} 天 ({n_flat / len(r120) * 100:.1f}%)")

    print("\n完成。未落盘。请把上面输出贴回，据此确定牛熊阈值。")


if __name__ == "__main__":
    main()
