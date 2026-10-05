"""测试 volume_ratio 因子。"""

import numpy as np
import pandas as pd
import pytest

from mfalpha.factors.volume_ratio import volume_ratio


def test_volume_ratio_constant():
    """常数成交量，量比应为 1。"""
    s = pd.Series([100.0] * 30)
    result = volume_ratio(s, short_window=5, long_window=20)
    assert np.isnan(result.iloc[18])
    assert result.iloc[19] == pytest.approx(1.0)
    assert result.iloc[29] == pytest.approx(1.0)


def test_volume_ratio_surge():
    """后期成交量翻倍，量比应 > 1。"""
    s = pd.Series([100.0] * 20 + [200.0] * 10)
    result = volume_ratio(s, short_window=5, long_window=20)
    # 最后 5 日均 = 200；最后 20 日均 = (10*100 + 10*200) / 20 = 150
    assert result.iloc[-1] == pytest.approx(200 / 150)


def test_volume_ratio_invalid_window():
    """非法窗口抛 ValueError。"""
    s = pd.Series([100.0] * 30)
    with pytest.raises(ValueError):
        volume_ratio(s, short_window=0, long_window=20)
    with pytest.raises(ValueError):
        volume_ratio(s, short_window=5, long_window=-1)


def test_volume_ratio_short_ge_long():
    """short >= long 抛 ValueError。"""
    s = pd.Series([100.0] * 30)
    with pytest.raises(ValueError):
        volume_ratio(s, short_window=20, long_window=20)
    with pytest.raises(ValueError):
        volume_ratio(s, short_window=25, long_window=20)


def test_volume_ratio_length_and_index():
    """输出等长、索引一致。"""
    idx = pd.date_range("2020-01-01", periods=100)
    s = pd.Series(np.random.rand(100) * 1e6, index=idx)
    result = volume_ratio(s)
    assert len(result) == len(s)
    assert (result.index == s.index).all()
