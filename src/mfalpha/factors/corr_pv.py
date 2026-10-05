"""价量类因子：量价相关性（corr_pv）。"""

import pandas as pd


def corr_pv(close: pd.Series, volume: pd.Series, window: int = 20) -> pd.Series:
    """计算 N 日滚动量价相关系数。

    量价相关性 = 收盘价与成交量在过去 window 日的 Pearson 相关系数。
    因子值接近 +1 表示价涨量增、价跌量减；
    接近 -1 表示价涨量减、价跌量增；
    接近 0 表示量价关系不明显。

    Args:
        close: 收盘价序列，DatetimeIndex 且按日期升序。
        volume: 成交量序列，索引需与 close 一致。
        window: 回看窗口长度（交易日数），必须为正整数，默认 20。

    Returns:
        与输入等长、索引相同的相关系数序列，
        前 window-1 期因窗口不足为 NaN。

    Raises:
        ValueError: window 不为正整数时抛出。
        ValueError: close 与 volume 长度不一致时抛出。

    Example:
        >>> c = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        >>> v = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        >>> corr_pv(c, v, window=3).iloc[-1]
        1.0
    """
    if window <= 0:
        raise ValueError(f"window 必须为正整数，当前为 {window}")
    if len(close) != len(volume):
        raise ValueError(f"close 与 volume 长度不一致：{len(close)} vs {len(volume)}")
    return close.rolling(window=window, min_periods=window).corr(volume)
