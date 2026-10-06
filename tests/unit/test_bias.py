"""bias 因子的单元测试。"""

import pandas as pd
import pytest

from mfalpha.factors.bias import bias


def test_bias_price_equals_ma_is_zero() -> None:
    """收盘价恰好等于均线时，BIAS 应为 0。"""
    close = pd.Series([10.0] * 20)

    result = bias(close, window=20)

    assert result.iloc[-1] == pytest.approx(0.0)
    assert result.iloc[:19].isna().all()


def test_bias_above_ma_is_positive() -> None:
    """价格高于均线时，BIAS 应为正，且等于手算值。"""
    # 前 19 天 =10，第 20 天 =11
    # MA20 = (10*19 + 11)/20 = 10.05
    # BIAS = (11 - 10.05)/10.05*100 = 9.4527...
    close = pd.Series([10.0] * 19 + [11.0])

    result = bias(close, window=20)

    assert result.iloc[-1] == pytest.approx((11.0 - 10.05) / 10.05 * 100.0)


def test_bias_rejects_bad_window() -> None:
    """window 非正整数时应抛 ValueError。"""
    with pytest.raises(ValueError):
        bias(pd.Series([1.0, 2.0]), window=0)
