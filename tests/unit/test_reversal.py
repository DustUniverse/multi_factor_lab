"""reversal 因子的单元测试。"""

import pandas as pd
import pytest

from mfalpha.factors.momentum import momentum
from mfalpha.factors.reversal import reversal


def test_reversal_is_negative_momentum() -> None:
    """反转因子应等于动量因子的相反数。"""
    close = pd.Series([100.0, 105.0, 110.0, 121.0, 115.0])
    result = reversal(close, window=2)
    expected = -momentum(close, window=2)
    pd.testing.assert_series_equal(result, expected)


def test_reversal_nan_prefix() -> None:
    """前 window 期应为 NaN。"""
    close = pd.Series([100.0, 105.0, 110.0, 121.0, 115.0])
    result = reversal(close, window=2)
    assert result.iloc[:2].isna().all()
    assert result.iloc[2:].notna().all()


def test_reversal_invalid_window() -> None:
    """window 非正时应抛 ValueError。"""
    close = pd.Series([100.0, 105.0, 110.0])
    with pytest.raises(ValueError):
        reversal(close, window=0)
