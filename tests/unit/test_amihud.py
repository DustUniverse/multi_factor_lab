"""测试 amihud 因子。"""

import numpy as np
import pandas as pd
import pytest

from mfalpha.factors.amihud import amihud


def test_amihud_basic():
    """常数成交额下，Amihud = mean(|收益率|) / 成交额。"""
    c = pd.Series([10.0, 11.0, 12.0, 11.0, 10.0])
    a = pd.Series([1e8, 1e8, 1e8, 1e8, 1e8])
    result = amihud(c, a, window=3)
    # pct_change 引入额外一个 NaN，所以前 3 位都是 NaN
    assert np.isnan(result.iloc[0])
    assert np.isnan(result.iloc[1])
    assert np.isnan(result.iloc[2])
    # index=3：窗口 = returns[1], returns[2], returns[3] = 0.1, 1/11, -1/12
    expected = (0.1 + 1 / 11 + 1 / 12) / 3 / 1e8
    assert result.iloc[3] == pytest.approx(expected, rel=1e-6)


def test_amihud_invalid_window():
    """非法 window 抛 ValueError。"""
    c = pd.Series([10.0, 11.0, 12.0])
    a = pd.Series([1e8, 1e8, 1e8])
    with pytest.raises(ValueError):
        amihud(c, a, window=0)
    with pytest.raises(ValueError):
        amihud(c, a, window=-1)


def test_amihud_length_mismatch():
    """长度不一致抛 ValueError。"""
    c = pd.Series([10.0, 11.0, 12.0])
    a = pd.Series([1e8, 1e8])
    with pytest.raises(ValueError):
        amihud(c, a, window=2)


def test_amihud_length_and_index():
    """输出等长、索引一致。"""
    idx = pd.date_range("2020-01-01", periods=100)
    c = pd.Series(np.random.rand(100) + 10, index=idx)
    a = pd.Series(np.random.rand(100) * 1e8 + 1e7, index=idx)
    result = amihud(c, a, window=20)
    assert len(result) == len(c)
    assert (result.index == c.index).all()
