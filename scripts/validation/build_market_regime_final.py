"""
M6 S1b: 构建牛/熊/震荡市场状态标签并落盘

规则（与探查脚本一致）：
    1. 等权市场指数：每日全市场股票 pct_chg 的等权均值，累乘得净值。
    2. 市场状态：120 日滚动收益
        > +10%  -> bull
        < -10%  -> bear
        其余     -> flat
    3. 前 120 日无滚动收益 -> regime 缺失（NaN），落盘时剔除。

产出：
    data/processed/market_regime.csv
        columns: [date, nav, ret_120d, regime]
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRICE_PATH = PROJECT_ROOT / "data" / "processed" / "daily_panel_tencent_clean.parquet"
OUT_PATH = PROJECT_ROOT / "data" / "processed" / "market_regime.csv"

WINDOW = 120
BULL_THRESHOLD = 0.10
BEAR_THRESHOLD = -0.10


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
    work = df.copy()
    if exclude_suspended:
        work = work[~work["is_suspended"]]
    work = work.dropna(subset=["pct_chg"])
    daily_ret = work.groupby("date")["pct_chg"].mean() / 100.0
    daily_ret = daily_ret.sort_index()
    nav = (1.0 + daily_ret).cumprod()
    return nav


def classify(rolling_ret: pd.Series) -> pd.Series:
    regime = pd.Series(index=rolling_ret.index, dtype="object")
    regime[rolling_ret > BULL_THRESHOLD] = "bull"
    regime[rolling_ret < BEAR_THRESHOLD] = "bear"
    regime[(rolling_ret >= BEAR_THRESHOLD) & (rolling_ret <= BULL_THRESHOLD)] = "flat"
    return regime


def main() -> None:
    print(f"[1/3] 读取价格面板: {PRICE_PATH}")
    df = load_prices(PRICE_PATH)
    print(f"      shape: {df.shape}")

    print("[2/3] 构建等权指数 + 120 日滚动收益 + 分类")
    nav = build_equal_weight_index(df)
    ret_120 = nav / nav.shift(WINDOW) - 1.0
    regime = classify(ret_120)

    out = pd.DataFrame(
        {
            "date": nav.index,
            "nav": nav.values,
            "ret_120d": ret_120.values,
            "regime": regime.values,
        }
    )
    # 丢掉前 WINDOW 天（ret_120 为 NaN，regime 也为 NaN）
    before = len(out)
    out = out.dropna(subset=["regime"]).reset_index(drop=True)
    print(f"      原始 {before} 行，剔除前 {WINDOW} 天后剩 {len(out)} 行")

    print("[3/3] 落盘 + 统计")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"      写入: {OUT_PATH}")

    print("\n  regime 分布:")
    counts = out["regime"].value_counts()
    for k in ("bull", "flat", "bear"):
        n = int(counts.get(k, 0))
        print(f"    {k:5s}: {n:5d} 天 ({n / len(out) * 100:.1f}%)")

    print("\n  分段边界（连续同状态视为一段）:")
    out["seg"] = (out["regime"] != out["regime"].shift()).cumsum()
    segs = (
        out.groupby("seg")
        .agg(
            start=("date", "min"),
            end=("date", "max"),
            regime=("regime", "first"),
            n=("date", "size"),
        )
        .reset_index(drop=True)
    )
    # 只打印长度 >= 20 天的段（太碎的段无意义）
    segs = segs[segs["n"] >= 20]
    print(f"    共 {len(segs)} 段（>=20 天）:")
    for _, r in segs.iterrows():
        print(
            f"    {r['regime']:5s}"
            f"{r['start'].date()} ~ {r['end'].date()}  "
            f"({r['n']} 天)"
        )

    print("\n完成。")


if __name__ == "__main__":
    main()
