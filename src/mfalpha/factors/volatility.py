"""价量类因子：波动率（volatility）。"""

import pandas as pd


def volatility(close: pd.Series, window: int = 20) -> pd.Series:
    """计算 N 日波动率因子（过去 window 日收益率的标准差）。

    波动率 = std(日收益率, window 期)，未年化。
    因子值越高，代表近期波动越大。

    Args:
        close: 收盘价序列，要求为 DatetimeIndex 且按日期升序。
        window: 回看窗口长度（交易日数），必须为正整数，默认 20。

    Returns:
        与输入等长、索引相同的波动率序列；
        前 window 期因窗口不足为 NaN。

    Raises:
        ValueError: window 不为正整数时抛出。

    Example:
        >>> close = pd.Series([100.0, 100.0, 100.0, 100.0])
        >>> float(volatility(close, window=2).iloc[-1])
        0.0
    """
    if window <= 0:
        raise ValueError(f"window 必须为正整数，当前为 {window}")
    returns = close.pct_change(fill_method=None)
    return returns.rolling(window=window, min_periods=window).std()
