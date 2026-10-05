"""测试 corr_pv 因子。"""

import numpy as np
import pandas as pd
import pytest

from mfalpha.factors.corr_pv import corr_pv


def test_corr_pv_perfect_positive():
    """完全同向，相关系数应为 1。"""
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = corr_pv(s, s, window=3)
    assert np.isnan(result.iloc[0])
    assert np.isnan(result.iloc[1])
    assert result.iloc[2] == pytest.approx(1.0)
    assert result.iloc[3] == pytest.approx(1.0)
    assert result.iloc[4] == pytest.approx(1.0)


def test_corr_pv_perfect_negative():
    """完全反向，相关系数应为 -1。"""
    close = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    volume = pd.Series([5.0, 4.0, 3.0, 2.0, 1.0])
    result = corr_pv(close, volume, window=3)
    assert result.iloc[-1] == pytest.approx(-1.0)


def test_corr_pv_invalid_window():
    """非法 window 抛 ValueError。"""
    s = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        corr_pv(s, s, window=0)
    with pytest.raises(ValueError):
        corr_pv(s, s, window=-1)


def test_corr_pv_length_mismatch():
    """长度不一致抛 ValueError。"""
    c = pd.Series([1.0, 2.0, 3.0])
    v = pd.Series([1.0, 2.0])
    with pytest.raises(ValueError):
        corr_pv(c, v, window=2)


def test_corr_pv_length_and_index():
    """输出与输入等长、索引一致。"""
    idx = pd.date_range("2020-01-01", periods=100)
    c = pd.Series(np.random.rand(100), index=idx)
    v = pd.Series(np.random.rand(100), index=idx)
    result = corr_pv(c, v, window=20)
    assert len(result) == len(c)
    assert (result.index == c.index).all()
