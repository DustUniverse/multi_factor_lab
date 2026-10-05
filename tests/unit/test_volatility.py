"""volatility 因子的单元测试。"""

import pandas as pd
import pytest

from mfalpha.factors.volatility import volatility


def test_volatility_constant_series_is_zero() -> None:
    """常数价格序列的波动率应为 0。"""
    close = pd.Series([100.0] * 5)
    result = volatility(close, window=2)
    assert result.iloc[:2].isna().all()
    assert (result.iloc[2:] == 0).all()


def test_volatility_nan_prefix() -> None:
    """前 window 期应为 NaN。"""
    close = pd.Series([100.0, 105.0, 110.0, 121.0, 115.0])
    result = volatility(close, window=3)
    assert result.iloc[:3].isna().all()
    assert result.iloc[3:].notna().all()


def test_volatility_invalid_window() -> None:
    """window 非正时应抛 ValueError。"""
    close = pd.Series([100.0, 105.0, 110.0])
    with pytest.raises(ValueError):
        volatility(close, window=-1)
