"""价量类因子：动量（momentum）。"""

import pandas as pd


def momentum(close: pd.Series, window: int = 20) -> pd.Series:
    """计算 N 日动量因子（过去 window 个交易日的累计涨跌幅）。

    动量 = 当前收盘价 / window 期前收盘价 - 1。
    因子值越高，代表近期涨幅越大。

    Args:
        close: 收盘价序列，要求为 DatetimeIndex 且按日期升序。
        window: 回看窗口长度（交易日数），必须为正整数，默认 20。

    Returns:
        与输入等长、索引相同的动量序列；
        前 window 期因窗口不足为 NaN。

    Raises:
        ValueError: window 不为正整数时抛出。

    Example:
        >>> close = pd.Series([100.0, 110.0, 121.0])
        >>> momentum(close, window=2).iloc[-1]
        0.21
    """
    if window <= 0:
        raise ValueError(f"window 必须为正整数，当前为 {window}")
    return close.pct_change(periods=window, fill_method=None)
