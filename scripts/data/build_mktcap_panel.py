"""M4 Step2：从 daily_basic 的 float_share 和价格面板的 close 计算 log 市值。

市值公式：
    total_mktcap(元) = close(元) × float_share(万股) × 10000

输出：
    data/processed/mktcap_panel.parquet
        宽表，index=date，columns=symbol，值=log(total_mktcap)
        供 M4 中性化回归当自变量用。

用法（项目根目录、激活 .venv 后）：
    python scripts/data/build_mktcap_panel.py
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))

RAW_DIR = _ROOT / "data" / "raw" / "financial"
OUT_PATH = _ROOT / "data" / "processed" / "mktcap_panel.parquet"
PRICE_PATH = _ROOT / "data" / "processed" / "daily_panel_tencent_clean.parquet"


def load_float_share() -> pd.DataFrame:
    """读 6 个 daily_basic 文件，返回 (date, symbol, float_share) 长表。"""
    files = sorted(glob.glob(str(RAW_DIR / "daily_basic_*.parquet")))
    print(f"  找到 {len(files)} 个 daily_basic 文件")
    dfs = []
    for f in files:
        df = pd.read_parquet(f, columns=["ts_code", "trade_date", "float_share"])
        dfs.append(df)
        print(f"    {Path(f).name}: {len(df)} 行")
    df = pd.concat(dfs, ignore_index=True)
    print(f"  合并后：{len(df)} 行")

    # ts_code -> symbol（6 位纯数字）
    df["symbol"] = df["ts_code"].str.split(".").str[0]

    # trade_date -> datetime（原始是 '20190930' 这种 8 位字符串/整数）
    df["date"] = pd.to_datetime(df["trade_date"].astype(str), format="%Y%m%d")

    df = df[["date", "symbol", "float_share"]]
    # 去重：同一 (date, symbol) 只保留第一条
    before = len(df)
    df = df.drop_duplicates(subset=["date", "symbol"], keep="first")
    print(f"  去重后：{len(df)} 行（删除 {before - len(df)} 条重复）")

    # float_share 单位是万股，可能为 0 或 NaN，过滤掉
    df = df[df["float_share"].notna() & (df["float_share"] > 0)]
    print(f"  过滤 float_share<=0/NaN 后：{len(df)} 行")
    return df


def load_close() -> pd.DataFrame:
    """读价格面板，返回 (date, symbol, close) 长表。"""
    df = pd.read_parquet(PRICE_PATH, columns=["date", "symbol", "close"])
    print(f"  价格面板：{len(df)} 行")
    print(f"  date 范围：{df['date'].min()} ~ {df['date'].max()}")
    return df


def main() -> None:
    print("[M4 Step2] 计算 log 市值面板")

    print("  1) 读 daily_basic float_share ...")
    fs = load_float_share()

    print("  2) 读价格面板 close ...")
    close = load_close()

    print("  3) 按 (date, symbol) 合并 ...")
    merged = close.merge(fs, on=["date", "symbol"], how="inner")
    print(f"  合并后：{len(merged)} 行")
    print(
        f"  合并前价格面板：{len(close)} 行，保留率：{len(merged)/len(close)*100:.1f}%"
    )

    if merged.empty:
        print("  [ERROR] 合并为空，检查 date / symbol 格式是否对齐")
        return

    print("  4) 计算市值和 log 市值 ...")
    merged["mktcap"] = merged["close"] * merged["float_share"] * 10000.0
    # 市值必须为正才能取 log
    n_bad = (merged["mktcap"] <= 0).sum()
    if n_bad > 0:
        print(f"  [WARN] {n_bad} 行市值 <= 0，已剔除")
    merged = merged[merged["mktcap"] > 0]
    merged["log_mktcap"] = np.log(merged["mktcap"])

    print("  log_mktcap 统计：")
    print(merged["log_mktcap"].describe().round(3).to_string())

    print("  5) 转宽表（date × symbol）...")
    wide = merged.pivot(index="date", columns="symbol", values="log_mktcap")
    print(f"  宽表 shape：{wide.shape}（date × symbol）")

    print("  6) 保存 ...")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    wide.to_parquet(OUT_PATH)
    print(f"  已保存：{OUT_PATH}")

    # 抽 3 个日期看看市值量级
    print("\n  抽样（log_mktcap，转成亿元便于理解）：")
    sample_dates = [wide.index[0], wide.index[len(wide) // 2], wide.index[-1]]
    for d in sample_dates:
        row = wide.loc[d].dropna()
        if len(row) > 0:
            mid = np.exp(row.median()) / 1e8
            print(f"    {d.date()}  中位市值={mid:.1f} 亿元  有效股票={len(row)}")

    print("\n[M4 Step2] 完成。")


if __name__ == "__main__":
    main()
