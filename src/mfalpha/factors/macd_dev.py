"""技术类因子：MACD 偏离（macd_dev）。"""

import pandas as pd


def macd_dev(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.Series:
    """计算 MACD 柱相对收盘价的偏离因子。

    计算步骤（标准 MACD）：
        EMA_fast = EMA(close, fast)
        EMA_slow = EMA(close, slow)
        DIF      = EMA_fast - EMA_slow
        DEA      = EMA(DIF, signal)
        MACD 柱  = DIF - DEA

    本因子再做归一化：macd_dev = (DIF - DEA) / close，
    使不同价格水平的股票可横截面比较。

    含义：
        - 因子值 > 0 → DIF 在 DEA 上方（多头动能增强）
        - 因子值 < 0 → DIF 在 DEA 下方（空头动能增强）

    Args:
        close: 收盘价序列，要求为 DatetimeIndex 且按日期升序。
        fast: 快线 EMA 周期，正整数，默认 12。
        slow: 慢线 EMA 周期，正整数，默认 26。
        signal: 信号线 EMA 周期，正整数，默认 9。

    Returns:
        与输入等长、索引相同的偏离序列；
        前 slow-1 期因暖机不足为 NaN。

    Raises:
        ValueError: 任一周期不为正整数时抛出。
        ValueError: fast >= slow 时抛出。

    Example:
        >>> c = pd.Series([10.0] * 40)
        >>> macd_dev(c, 12, 26, 9).iloc[-1]
        0.0
    """
    if fast <= 0 or slow <= 0 or signal <= 0:
        raise ValueError(
            f"周期必须为正整数，当前 fast={fast}, slow={slow}, signal={signal}"
        )
    if fast >= slow:
        raise ValueError(f"fast 必须小于 slow，当前 {fast} >= {slow}")

    ema_fast = close.ewm(span=fast, min_periods=slow, adjust=False).mean()
    ema_slow = close.ewm(span=slow, min_periods=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, min_periods=signal, adjust=False).mean()

    return (dif - dea) / close
