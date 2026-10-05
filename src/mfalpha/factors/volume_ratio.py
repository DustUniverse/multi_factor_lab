"""价量类因子：量比（volume_ratio）。"""

import pandas as pd


def volume_ratio(
    volume: pd.Series,
    short_window: int = 5,
    long_window: int = 20,
) -> pd.Series:
    """计算量比因子：短期平均成交量 / 长期平均成交量。

    量比 > 1 表示近期成交量相比长期放大，市场关注度上升；
    量比 < 1 表示近期成交量萎缩。

    Args:
        volume: 日成交量序列，DatetimeIndex 且按日期升序。
        short_window: 短期窗口长度，正整数，默认 5。
        long_window: 长期窗口长度，正整数，默认 20。

    Returns:
        与输入等长、索引相同的量比序列，前 long_window-1 期为 NaN。

    Raises:
        ValueError: 窗口不为正整数时抛出。
        ValueError: short_window >= long_window 时抛出。

    Example:
        >>> s = pd.Series([100.0] * 20 + [200.0] * 5)
        >>> volume_ratio(s, short_window=5, long_window=20).iloc[-1] > 1
        True
    """
    if short_window <= 0 or long_window <= 0:
        raise ValueError(
            f"窗口必须为正整数，当前 short={short_window}, long={long_window}"
        )
    if short_window >= long_window:
        raise ValueError(
            f"short_window 必须小于 long_window，当前 {short_window} >= {long_window}"
        )
    short_ma = volume.rolling(window=short_window, min_periods=short_window).mean()
    long_ma = volume.rolling(window=long_window, min_periods=long_window).mean()
    return short_ma / long_ma
