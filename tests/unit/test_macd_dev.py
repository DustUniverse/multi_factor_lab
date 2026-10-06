"""macd_dev 因子的单元测试。"""

import pandas as pd
import pytest

from mfalpha.factors.macd_dev import macd_dev


def test_macd_dev_flat_price_is_zero() -> None:
    """价格恒定 → DIF=0, DEA=0 → 因子值为 0。"""
    close = pd.Series([10.0] * 50)

    result = macd_dev(close, fast=12, slow=26, signal=9)

    assert result.iloc[-1] == pytest.approx(0.0)
    assert result.iloc[:25].isna().all()


def test_macd_dev_uptrend_is_positive() -> None:
    """价格单调上涨 → DIF > 0 且 DEA 滞后 → MACD 柱 > 0。"""
    close = pd.Series(range(1, 61), dtype=float)  # 1..60 线性增长

    result = macd_dev(close, fast=12, slow=26, signal=9)

    assert result.iloc[-1] > 0


def test_macd_dev_rejects_bad_params() -> None:
    """周期非正整数或 fast >= slow 时应抛 ValueError。"""
    s = pd.Series([1.0, 2.0])
    with pytest.raises(ValueError):
        macd_dev(s, fast=0, slow=26, signal=9)
    with pytest.raises(ValueError):
        macd_dev(s, fast=26, slow=12, signal=9)
