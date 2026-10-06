"""技术类因子：RSI 相对强弱指标（Wilder 1978 原始定义）。"""

import pandas as pd


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """计算 N 日 RSI 相对强弱指标。

    RSI 衡量近期上涨与下跌力量的对比，取值 0~100：
    - RSI > 70 通常视为超买
    - RSI < 30 通常视为超卖

    计算步骤（Wilder 1978 原始定义）：
        1. delta = 相邻收盘价之差
        2. gain = max(delta, 0)，loss = max(-delta, 0)
        3. avg_gain / avg_loss 使用 ewm(alpha=1/N) 平滑
        4. RS = avg_gain / avg_loss
        5. RSI = 100 - 100 / (1 + RS)

    Args:
        close: 收盘价序列，要求为 DatetimeIndex 且按日期升序。
        window: 回看窗口长度（交易日数），必须为正整数，默认 14。

    Returns:
        与输入等长、索引相同的 RSI 序列，取值 [0, 100]；
        前 window 期为 NaN（diff 与 ewm 各引入起始 NaN）。

    Raises:
        ValueError: window 不为正整数时抛出。

    Example:
        >>> c = pd.Series(range(1, 20), dtype=float)  # 单调上涨
        >>> rsi(c, window=14).iloc[-1]
        100.0
    """
    if window <= 0:
        raise ValueError(f"window 必须为正整数，当前为 {window}")

    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)
