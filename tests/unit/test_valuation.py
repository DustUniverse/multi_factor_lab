"""测试估值因子（E/P、B/P）。"""

import numpy as np
import pandas as pd
import pytest

from mfalpha.factors.valuation import bp, ep_ttm


# ---------- ep_ttm ----------
def test_ep_ttm_normal():
    pe = pd.Series([10.0, 20.0, 5.0])
    result = ep_ttm(pe)
    expected = pd.Series([0.1, 0.05, 0.2])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_ep_ttm_zero_and_negative_are_nan():
    pe = pd.Series([0.0, -5.0, 10.0])
    result = ep_ttm(pe)
    assert pd.isna(result.iloc[0])
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == pytest.approx(0.1)


def test_ep_ttm_nan_propagates():
    pe = pd.Series([np.nan, 10.0])
    result = ep_ttm(pe)
    assert pd.isna(result.iloc[0])
    assert result.iloc[1] == pytest.approx(0.1)


def test_ep_ttm_preserves_index():
    pe = pd.Series([10.0, 20.0], index=["a", "b"])
    result = ep_ttm(pe)
    assert list(result.index) == ["a", "b"]


# ---------- bp ----------
def test_bp_normal():
    pb = pd.Series([2.0, 5.0, 0.5])
    result = bp(pb)
    expected = pd.Series([0.5, 0.2, 2.0])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_bp_zero_and_negative_are_nan():
    pb = pd.Series([0.0, -1.0, 4.0])
    result = bp(pb)
    assert pd.isna(result.iloc[0])
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == pytest.approx(0.25)


def test_bp_nan_propagates():
    pb = pd.Series([np.nan, 2.0])
    result = bp(pb)
    assert pd.isna(result.iloc[0])
    assert result.iloc[1] == pytest.approx(0.5)
