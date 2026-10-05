"""测试 amplitude 因子。"""

import numpy as np
import pandas as pd
import pytest

from mfalpha.factors.amplitude import amplitude


def test_amplitude_basic():
    """3 日窗口，手工验证平均振幅。"""
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = amplitude(s, window=3)
    assert np.isnan(result.iloc[0])
    assert np.isnan(result.iloc[1])
    assert result.iloc[2] == pytest.approx(2.0)
    assert result.iloc[3] == pytest.approx(3.0)
    assert result.iloc[4] == pytest.approx(4.0)


def test_amplitude_invalid_window():
    """非法 window 抛 ValueError。"""
    s = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        amplitude(s, window=0)
    with pytest.raises(ValueError):
        amplitude(s, window=-1)


def test_amplitude_length_and_index():
    """输出与输入等长、索引一致。"""
    s = pd.Series(np.random.rand(100), index=pd.date_range("2020-01-01", periods=100))
    result = amplitude(s, window=20)
    assert len(result) == len(s)
    assert (result.index == s.index).all()


def test_amplitude_default_window():
    """默认 window=20。"""
    s = pd.Series(np.random.rand(50))
    result = amplitude(s)
    assert np.isnan(result.iloc[18])
    assert not np.isnan(result.iloc[19])
