"""价量类因子：振幅（amplitude）。"""

import pandas as pd


def amplitude(amplitude_series: pd.Series, window: int = 20) -> pd.Series:
    """计算 N 日平均振幅因子。

    振幅 = (当日最高 - 当日最低) / 昨收，反映股价日内波动幅度。
    因子值越高，代表近期股价波动越剧烈。

    Args:
        amplitude_series: 日振幅序列（单位：%），要求为 DatetimeIndex 且按日期升序。
        window: 回看窗口长度（交易日数），必须为正整数，默认 20。

    Returns:
        与输入等长、索引相同的平均振幅序列，
        前 window-1 期因窗口不足为 NaN。

    Raises:
        ValueError: window 不为正整数时抛出。

    Example:
        >>> s = pd.Series([1.0, 2.0, 3.0, 4.0])
        >>> amplitude(s, window=3).iloc[-1]
        3.0
    """
    if window <= 0:
        raise ValueError(f"window 必须为正整数，当前为 {window}")
    return amplitude_series.rolling(window=window, min_periods=window).mean()
