"""价量类因子：Amihud 非流动性。"""

import pandas as pd


def amihud(close: pd.Series, amount: pd.Series, window: int = 20) -> pd.Series:
    """计算 N 日平均 Amihud 非流动性因子。

    Amihud = mean(|日收益率| / 日成交额)

    因子值越高，代表每单位成交额能推动股价变动越大，
    即流动性越差、冲击成本越高。

    Args:
        close: 收盘价序列，DatetimeIndex 且按日期升序。
        amount: 日成交额序列，索引需与 close 一致。
        window: 回看窗口长度（交易日数），必须为正整数，默认 20。

    Returns:
        与输入等长、索引相同的非流动性序列，前 window 期为 NaN。
        注意：由于 pct_change 引入一个额外 NaN，第一个有效值出现在第 window 位。

    Raises:
        ValueError: window 不为正整数时抛出。
        ValueError: close 与 amount 长度不一致时抛出。

    Example:
        >>> c = pd.Series([10.0, 11.0, 12.0, 11.0])
        >>> a = pd.Series([1e8, 1e8, 1e8, 1e8])
        >>> amihud(c, a, window=3).iloc[-1] > 0
        True
    """
    if window <= 0:
        raise ValueError(f"window 必须为正整数，当前为 {window}")
    if len(close) != len(amount):
        raise ValueError(f"close 与 amount 长度不一致：{len(close)} vs {len(amount)}")
    returns = close.pct_change(fill_method=None)
    illiq = returns.abs() / amount
    return illiq.rolling(window=window, min_periods=window).mean()
