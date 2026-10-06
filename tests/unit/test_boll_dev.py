"""boll_dev 因子的单元测试。"""

import pandas as pd
import pytest

from mfalpha.factors.boll_dev import boll_dev


def test_boll_dev_known_value() -> None:
    """三值 [1, 2, 3]，MA=2，样本 std=1，(3-2)/1 = 1.0。"""
    close = pd.Series([1.0, 2.0, 3.0])

    result = boll_dev(close, window=3)

    assert result.iloc[-1] == pytest.approx(1.0)
    assert result.iloc[:2].isna().all()


def test_boll_dev_flat_price_is_nan() -> None:
    """价格完全不变时 std=0，结果应为 NaN（0/0）。"""
    close = pd.Series([10.0] * 20)

    result = boll_dev(close, window=20)

    assert result.iloc[-1] != result.iloc[-1]  # NaN 不等于自身


def test_boll_dev_rejects_bad_window() -> None:
    """window 非正整数时应抛 ValueError。"""
    with pytest.raises(ValueError):
        boll_dev(pd.Series([1.0, 2.0]), window=0)
