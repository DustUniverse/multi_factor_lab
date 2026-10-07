"""一键生成全市场因子面板。

输入：data/processed/daily_panel_tencent_clean.parquet
输出：data/processed/factor_panel_11f.parquet

包含 11 个因子（turnover 因缺流通股本，本期暂不计算）：

价量类（7 个）：
- momentum_20      动量
- reversal_20      反转
- volatility_20    波动率
- corr_pv_20       量价相关性
- volume_ratio     量比（5/20）
- amplitude_20     振幅
- amihud_20        Amihud 非流动性（成交额用 close × volume 近似）

技术类（4 个）：
- rsi_14           RSI 相对强弱（Wilder 平滑）
- bias_20          乖离率
- boll_dev_20      布林带偏离
- macd_dev         MACD 偏离（归一化）

用法：
    python scripts/factors/build_factor_panel.py
"""

import sys
from pathlib import Path

import pandas as pd

# 允许从 src 导入 mfalpha
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from mfalpha.factors.amihud import amihud  # noqa: E402
from mfalpha.factors.amplitude import amplitude  # noqa: E402
from mfalpha.factors.bias import bias  # noqa: E402
from mfalpha.factors.boll_dev import boll_dev  # noqa: E402
from mfalpha.factors.corr_pv import corr_pv  # noqa: E402
from mfalpha.factors.macd_dev import macd_dev  # noqa: E402
from mfalpha.factors.momentum import momentum  # noqa: E402
from mfalpha.factors.reversal import reversal  # noqa: E402
from mfalpha.factors.rsi import rsi  # noqa: E402
from mfalpha.factors.volatility import volatility  # noqa: E402
from mfalpha.factors.volume_ratio import volume_ratio  # noqa: E402

# 统一窗口
WINDOW = 20
VR_SHORT = 5
VR_LONG = 20
RSI_WINDOW = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IN_PATH = PROJECT_ROOT / "data" / "processed" / "daily_panel_tencent_clean.parquet"
OUT_PATH = PROJECT_ROOT / "data" / "processed" / "factor_panel_11f.parquet"


def _compute_one(symbol: str, g: pd.DataFrame) -> pd.DataFrame:
    """对单只股票的日线数据计算全部因子，返回含 symbol/date + 因子列的 DataFrame。"""
    g = g.sort_values("date").reset_index(drop=True)

    close = g["close"]
    volume = g["volume"]
    high = g["high"]
    low = g["low"]

    # 振幅序列：当日振幅（%） = (高 - 低) / 昨收 × 100
    prev_close = close.shift(1)
    amplitude_series = (high - low) / prev_close * 100.0

    # 成交额近似：腾讯日线无成交额字段，用 收盘价 × 成交量 估算
    amount = close * volume

    out = pd.DataFrame(
        {
            "symbol": symbol,
            "date": g["date"],
            # 价量类
            "momentum_20": momentum(close, WINDOW),
            "reversal_20": reversal(close, WINDOW),
            "volatility_20": volatility(close, WINDOW),
            "corr_pv_20": corr_pv(close, volume, WINDOW),
            "volume_ratio": volume_ratio(volume, VR_SHORT, VR_LONG),
            "amplitude_20": amplitude(amplitude_series, WINDOW),
            "amihud_20": amihud(close, amount, WINDOW),
            # 技术类
            "rsi_14": rsi(close, RSI_WINDOW),
            "bias_20": bias(close, WINDOW),
            "boll_dev_20": boll_dev(close, WINDOW),
            "macd_dev": macd_dev(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL),
        }
    )
    return out


def main() -> None:
    print(f"[1/4] 读取清洗后面板：{IN_PATH}")
    df = pd.read_parquet(IN_PATH)
    print(f"      行数={len(df):,}  股票数={df['symbol'].nunique()}")

    print("[2/4] 按 symbol 逐只计算因子……")
    parts = []
    total = df["symbol"].nunique()
    for i, (symbol, g) in enumerate(df.groupby("symbol", sort=False), start=1):
        parts.append(_compute_one(symbol, g))
        if i % 500 == 0 or i == total:
            print(f"      进度：{i}/{total}")

    factor_df = pd.concat(parts, ignore_index=True)
    print(f"[3/4] 因子面板形状：{factor_df.shape}")

    # 缺失率速览
    factor_cols = [c for c in factor_df.columns if c not in ("symbol", "date")]
    na_rate = factor_df[factor_cols].isna().mean().sort_values(ascending=False)
    print("      各因子缺失率：")
    for col, rate in na_rate.items():
        print(f"        {col:<15} {rate:.4%}")

    print(f"[4/4] 写出：{OUT_PATH}")
    factor_df.to_parquet(OUT_PATH, index=False)
    print("完成。")


if __name__ == "__main__":
    main()
