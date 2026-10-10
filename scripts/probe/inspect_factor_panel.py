"""探查因子面板与价格面板的结构，为阶段二因子检验做准备。

只读脚本，不修改任何数据文件。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# 项目根目录：本文件位于 scripts/probe/ 下，向上两级即根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

FACTOR_PANEL_PATH = PROCESSED_DIR / "factor_panel.parquet"
PRICE_PANEL_PATH = PROCESSED_DIR / "daily_panel_tencent_clean.parquet"
FIN_PANEL_PATH = PROCESSED_DIR / "financial_panel_pit.parquet"


def describe_panel(name: str, path: Path) -> pd.DataFrame:
    """读取 parquet 并打印结构信息，返回 DataFrame 以便进一步查看。"""
    print("=" * 78)
    print(f"[{name}] {path}")
    print("-" * 78)
    if not path.exists():
        print("!! 文件不存在")
        return pd.DataFrame()

    df = pd.read_parquet(path)
    print(f"shape           : {df.shape}")
    print(f"columns ({len(df.columns)}): {list(df.columns)}")
    print("dtypes          :")
    print(df.dtypes.to_string())
    print("-" * 78)

    # 尝试识别 symbol / date 列
    symbol_col = next(
        (c for c in df.columns if c.lower() in {"symbol", "ts_code", "code"}), None
    )
    date_col = next(
        (c for c in df.columns if c.lower() in {"date", "trade_date", "datetime"}), None
    )

    if symbol_col is not None:
        n_symbol = df[symbol_col].nunique()
        print(f"symbol 列       : {symbol_col}")
        print(f"股票数          : {n_symbol}")
        print(f"symbol 示例     : {df[symbol_col].drop_duplicates().head(5).tolist()}")
    else:
        print("symbol 列       : 未识别")

    if date_col is not None:
        d = pd.to_datetime(df[date_col])
        print(f"date 列         : {date_col}")
        print(f"日期范围        : {d.min().date()} ~ {d.max().date()}")
        print(f"唯一交易日数    : {d.nunique()}")
    else:
        print("date 列         : 未识别")

    return df


def main() -> None:
    factor_df = describe_panel("factor_panel", FACTOR_PANEL_PATH)
    if not factor_df.empty:
        # 把除 symbol/date 之外的列视作因子
        id_cols = {"symbol", "date", "ts_code", "trade_date", "code", "datetime"}
        factor_cols = [c for c in factor_df.columns if c.lower() not in id_cols]
        print("=" * 78)
        print(f"识别出的因子列（{len(factor_cols)} 个）：")
        for i, c in enumerate(factor_cols, 1):
            print(f"  {i:>2}. {c}")
        print("=" * 78)
        print("各因子缺失率（前 20 行）：")
        miss = factor_df[factor_cols].isna().mean().sort_values(ascending=False)
        print(miss.head(20).to_string())

    describe_panel("daily_panel_tencent_clean", PRICE_PANEL_PATH)
    describe_panel("financial_panel_pit", FIN_PANEL_PATH)


if __name__ == "__main__":
    main()
