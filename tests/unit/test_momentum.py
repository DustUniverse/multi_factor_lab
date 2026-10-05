"""momentum 因子的单元测试。"""

import pandas as pd
import pytest

from mfalpha.factors.momentum import momentum


def test_momentum_basic() -> None:
    """手算可验证的简单案例：121/100 - 1 = 0.21。"""
    # Arrange：构造已知答案的小数据
    close = pd.Series([100.0, 110.0, 121.0])

    # Act
    result = momentum(close, window=2)

    # Assert：最后一期 = 0.21；前 2 期窗口不足为 NaN
    assert result.iloc[-1] == pytest.approx(0.21)
    assert result.iloc[:2].isna().all()


def test_momentum_rejects_bad_window() -> None:
    """window 非正整数时应抛 ValueError。"""
    with pytest.raises(ValueError):
        momentum(pd.Series([1.0, 2.0]), window=0)
