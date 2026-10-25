"""阶段四数据检查：扫描关键数据产物，输出数据画像。

运行：
    python scripts/stage4/check_data.py

输出：
    docs/stage4_data_check.md（同时终端打印）
"""

from pathlib import Path

import pandas as pd

PROCESSED = Path("data/processed")
RAW_FIN = Path("data/raw/financial")
OUT_MD = Path("docs/stage4_data_check.md")

# 只检查阶段四归因/优化真正会用到的文件，避免读 272MB 因子面板时等太久
KEY_FILES = [
    # 策略输出
    "composite_holdings_lasso_horizon_all8.csv",
    "composite_bt_lasso_horizon_all8.csv",
    "composite_bt_summary.csv",
    "composite_weights_lasso_horizon_all8.csv",
    # 归因基础设施
    "industry_map.parquet",
    "hs300_weight.parquet",
    "hs300_benchmark.parquet",
    "mktcap_panel.parquet",
    "stock_basic.parquet",
    # 因子（中性化面板很大，放最后，读的时候提示）
    "final_factor_list.csv",
    "factor_ic_daily_1d.parquet",
    "quantile_returns_volatility_20.csv",
    # 已有 Brinson 试点
    "brinson_lasso_all8_2023.csv",
]

DATE_COLS = ["trade_date", "date", "signal_date", "next_trade_date", "cal_date"]


def profile_df(df: pd.DataFrame, name: str) -> str:
    """打印一个 DataFrame 的画像。"""
    lines = [f"### {name}", f"- shape: {df.shape}"]
    cols = list(df.columns)
    lines.append(
        f"- columns({len(cols)}): {cols[:25]}{' ...' if len(cols) > 25 else ''}"
    )

    # 日期列范围
    for col in DATE_COLS:
        if col in df.columns:
            try:
                s = pd.to_datetime(df[col], errors="coerce")
                if s.notna().any():
                    lines.append(f"- {col} 范围: {s.min().date()} ~ {s.max().date()}")
            except Exception:
                pass
    # index 日期范围
    if isinstance(df.index, pd.DatetimeIndex):
        lines.append(f"- index 范围: {df.index.min().date()} ~ {df.index.max().date()}")

    # 缺失率 Top8（只列 >0 的）
    na = df.isna().mean().sort_values(ascending=False)
    top_na = na[na > 0].head(8)
    if len(top_na):
        lines.append(
            "- 缺失率 Top: " + ", ".join(f"{k}={v:.1%}" for k, v in top_na.items())
        )

    # 主键样例（帮助判断 symbol 格式、ts_code 格式）
    for col in ["symbol", "ts_code", "industry", "trade_date"]:
        if col in df.columns:
            vals = df[col].dropna().astype(str).unique()[:3]
            lines.append(f"- {col} 样例: {list(vals)}")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    md = [
        "# 阶段四数据检查报告",
        f"生成时间: {pd.Timestamp.now():%Y-%m-%d %H:%M:%S}",
        "",
    ]

    for fname in KEY_FILES:
        path = PROCESSED / fname
        if not path.exists():
            md.append(f"### {fname}\n- **缺失**\n")
            continue
        print(f"[读取] {fname} ...", flush=True)
        try:
            if fname.endswith(".csv"):
                df = pd.read_csv(path, dtype={"symbol": str, "ts_code": str})
            else:
                df = pd.read_parquet(path)
            md.append(profile_df(df, fname))
        except Exception as e:
            md.append(f"### {fname}\n- 读取失败: {type(e).__name__}: {e}\n")

    # daily_basic 逐年检查列名一致性
    md.append("## daily_basic 逐年检查\n")
    for year in [2020, 2021, 2022, 2023, 2024]:
        path = RAW_FIN / f"daily_basic_{year}.parquet"
        if not path.exists():
            md.append(f"### daily_basic_{year}\n- **缺失**\n")
            continue
        print(f"[读取] daily_basic_{year} ...", flush=True)
        df = pd.read_parquet(
            path, columns=["ts_code", "trade_date", "pb", "pe_ttm", "turnover_rate"]
        )
        md.append(
            f"### daily_basic_{year}\n"
            f"- shape: {df.shape}\n"
            f"- ts_code 样例: {df['ts_code'].dropna().unique()[:3].tolist()}\n"
            f"- trade_date 样例: {df['trade_date'].dropna().unique()[:3].tolist()}\n"
            f"- 缺失率: pb={df['pb'].isna().mean():.1%}, "
            f"pe_ttm={df['pe_ttm'].isna().mean():.1%}, "
            f"turnover_rate={df['turnover_rate'].isna().mean():.1%}\n"
        )

    text = "\n".join(md)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(text, encoding="utf-8")
    print("\n" + text)
    print(f"[OK] 已写入 {OUT_MD}")


if __name__ == "__main__":
    main()
