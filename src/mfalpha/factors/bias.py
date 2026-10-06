"""技术类因子：乖离率 BIAS。"""

import pandas as pd


def bias(close: pd.Series, window: int = 20) -> pd.Series:
    """计算 N 日乖离率（BIAS）。

    BIAS = (收盘价 - N 日均价) / N 日均价 × 100。

    因子值 > 0 表示价格在均线上方（超买倾向），
    因子值 < 0 表示价格在均线下方（超卖倾向），
    绝对值越大，偏离均线越远，反转可能性越高。

    Args:
        close: 收盘价序列，要求为 DatetimeIndex 且按日期升序。
        window: 均线窗口长度（交易日数），必须为正整数，默认 20。

    Returns:
        与输入等长、索引相同的乖离率序列（单位：%）；
        前 window-1 期因窗口不足为 NaN。

    Raises:
        ValueError: window 不为正整数时抛出。

    Example:
        >>> c = pd.Series([10.0] * 19 + [11.0])
        >>> round(bias(c, window=20).iloc[-1], 4)
        4.7619
    """
    if window <= 0:
        raise ValueError(f"window 必须为正整数，当前为 {window}")

    ma = close.rolling(window=window, min_periods=window).mean()
    return (close - ma) / ma * 100.0
