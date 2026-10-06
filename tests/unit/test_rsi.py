"""rsi 因子的单元测试。"""

import pandas as pd
import pytest

from mfalpha.factors.rsi import rsi


def test_rsi_all_up_is_100() -> None:
    """价格单调上涨时，avg_loss = 0，RSI 应为 100。"""
    close = pd.Series(range(1, 20), dtype=float)  # 1..19

    result = rsi(close, window=14)

    assert result.iloc[-1] == pytest.approx(100.0)
    # 前 14 期窗口不足为 NaN
    assert result.iloc[:14].isna().all()


def test_rsi_all_down_is_0() -> None:
    """价格单调下跌时，avg_gain = 0，RSI 应为 0。"""
    close = pd.Series(range(19, 0, -1), dtype=float)  # 19..1

    result = rsi(close, window=14)

    assert result.iloc[-1] == pytest.approx(0.0)


def test_rsi_rejects_bad_window() -> None:
    """window 非正整数时应抛 ValueError。"""
    with pytest.raises(ValueError):
        rsi(pd.Series([1.0, 2.0]), window=0)
