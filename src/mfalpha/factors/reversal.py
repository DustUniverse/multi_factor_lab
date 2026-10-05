"""价量类因子：反转（reversal）。"""

import pandas as pd

from mfalpha.factors.momentum import momentum


def reversal(close: pd.Series, window: int = 20) -> pd.Series:
    """计算 N 日反转因子（动量因子的相反数）。

    反转 = -(当前收盘价 / window 期前收盘价 - 1)。
    因子值越高，代表近期跌幅越大，预期未来反弹。

    Args:
        close: 收盘价序列，要求为 DatetimeIndex 且按日期升序。
        window: 回看窗口长度（交易日数），必须为正整数，默认 20。

    Returns:
        与输入等长、索引相同的反转序列；
        前 window 期因窗口不足为 NaN。

    Raises:
        ValueError: window 不为正整数时抛出。

    Example:
        >>> close = pd.Series([100.0, 110.0, 121.0])
        >>> reversal(close, window=2).iloc[-1]
        -0.21
    """
    if window <= 0:
        raise ValueError(f"window 必须为正整数，当前为 {window}")
    return -momentum(close, window=window)
