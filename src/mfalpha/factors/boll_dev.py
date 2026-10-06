"""技术类因子：布林带偏离（boll_dev）。"""

import pandas as pd


def boll_dev(close: pd.Series, window: int = 20) -> pd.Series:
    """计算 N 日布林带偏离因子。

    boll_dev = (收盘价 - N 日均价) / N 日标准差

    含义：
        - 因子值 = 0  → 收盘价在均线上
        - 因子值 = +2 → 收盘价接近布林带上轨（超买）
        - 因子值 = -2 → 收盘价接近布林带下轨（超卖）

    相比 BIAS，本因子用标准差标准化，能自动适应个股波动性差异。

    Args:
        close: 收盘价序列，要求为 DatetimeIndex 且按日期升序。
        window: 均线与标准差窗口长度（交易日数），必须为正整数，默认 20。

    Returns:
        与输入等长、索引相同的偏离序列；
        前 window-1 期因窗口不足为 NaN；
        若某窗口内价格完全不变（std=0），结果为 NaN。

    Raises:
        ValueError: window 不为正整数时抛出。

    Example:
        >>> c = pd.Series([1.0, 2.0, 3.0])
        >>> boll_dev(c, window=3).iloc[-1]
        1.0
    """
    if window <= 0:
        raise ValueError(f"window 必须为正整数，当前为 {window}")

    ma = close.rolling(window=window, min_periods=window).mean()
    std = close.rolling(window=window, min_periods=window).std()
    return (close - ma) / std
