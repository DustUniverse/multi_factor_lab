"""价量类因子：换手率（turnover）。"""

import pandas as pd


def turnover(turnover_series: pd.Series, window: int = 20) -> pd.Series:
    """计算 N 日平均换手率因子。

    换手率 = 成交量 / 流通股本，反映股票的交易活跃度。
    因子值越高，代表近期交易越活跃、流动性越好。

    Args:
        turnover_series: 日换手率序列（单位：%），要求为 DatetimeIndex 且按日期升序。
        window: 回看窗口长度（交易日数），必须为正整数，默认 20。

    Returns:
        与输入等长、索引相同的平均换手率序列，
        前 window-1 期因窗口不足为 NaN。

    Raises:
        ValueError: window 不为正整数时抛出。

    Example:
        >>> s = pd.Series([1.0, 2.0, 3.0, 4.0])
        >>> turnover(s, window=3).iloc[-1]
        3.0
    """
    if window <= 0:
        raise ValueError(f"window 必须为正整数，当前为 {window}")
    return turnover_series.rolling(window=window, min_periods=window).mean()
