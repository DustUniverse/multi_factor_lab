"""Point-in-Time 对齐工具。

把季度财务数据按公告日（ann_date）对齐到日频面板：
某个交易日 t，只使用 ann_date <= t 的最新一份财报。
"""

import pandas as pd


def to_ts_code(symbol: str) -> str:
    """6 位数字 symbol → Tushare ts_code 格式。

    600xxx / 688xxx / 9xxxxx -> .SH
    000xxx / 300xxx / 200xxx -> .SZ
    8xxxxx / 4xxxxx -> .BJ
    """
    if symbol.startswith(("60", "68", "9")):
        return f"{symbol}.SH"
    if symbol.startswith(("00", "30", "20")):
        return f"{symbol}.SZ"
    if symbol.startswith(("8", "4")):
        return f"{symbol}.BJ"
    raise ValueError(f"无法识别的 symbol：{symbol}")


def to_symbol(ts_code: str) -> str:
    """Tushare ts_code → 6 位数字 symbol。"""
    return ts_code.split(".")[0]


def align_financials_to_daily(
    daily: pd.DataFrame,
    financials: pd.DataFrame,
    financial_cols: list[str],
) -> pd.DataFrame:
    """把财务数据按 ann_date 对齐到日频面板。

    Args:
        daily: 日频面板，必须含 symbol、date 两列。
        financials: 财务数据，必须含 ts_code、ann_date、end_date 三列。
        financial_cols: 要带过来的财务字段列表。

    Returns:
        与 daily 等长的 DataFrame，含 symbol、date 及对齐后的财务字段。
    """
    # --- 预处理 daily ---
    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values(["date", "symbol"]).reset_index(drop=True)

    # --- 预处理 financials ---
    fin = financials.copy()
    fin["symbol"] = fin["ts_code"].map(to_symbol)
    fin["ann_date"] = pd.to_datetime(fin["ann_date"], format="%Y%m%d", errors="coerce")
    fin["end_date"] = pd.to_datetime(fin["end_date"], format="%Y%m%d", errors="coerce")
    fin = fin.dropna(subset=["ann_date"])

    # 同一 (symbol, ann_date) 可能有多条：保留 end_date 最新的
    fin = fin.sort_values(["symbol", "ann_date", "end_date"])
    fin = fin.drop_duplicates(subset=["symbol", "ann_date"], keep="last")

    fin = fin[["symbol", "ann_date", *financial_cols]].sort_values(
        ["ann_date", "symbol"]
    )

    # --- merge_asof ---
    merged = pd.merge_asof(
        daily,
        fin,
        left_on="date",
        right_on="ann_date",
        by="symbol",
        direction="backward",
        allow_exact_matches=True,
    )

    # 清理辅助列
    merged = merged.drop(columns=["ann_date"]).reset_index(drop=True)
    return merged
