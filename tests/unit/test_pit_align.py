"""测试 Point-in-Time 对齐逻辑。"""

import pandas as pd
import pytest

from mfalpha.data.pit_align import align_financials_to_daily, to_symbol, to_ts_code


# ---------- symbol 转换 ----------
@pytest.mark.parametrize(
    "symbol,expected",
    [
        ("600000", "600000.SH"),
        ("688001", "688001.SH"),
        ("000001", "000001.SZ"),
        ("300750", "300750.SZ"),
        ("830799", "830799.BJ"),
    ],
)
def test_to_ts_code(symbol, expected):
    assert to_ts_code(symbol) == expected


def test_to_ts_code_invalid():
    with pytest.raises(ValueError):
        to_ts_code("12345")  # 不是 6 位


def test_to_symbol():
    assert to_symbol("000001.SZ") == "000001"
    assert to_symbol("600000.SH") == "600000"


# ---------- PIT 对齐 ----------
def test_align_basic():
    """公告日之前用旧数据，公告日之后用新数据。"""
    daily = pd.DataFrame(
        {
            "symbol": ["000001"] * 5,
            "date": pd.to_datetime(
                ["2024-01-01", "2024-01-10", "2024-01-20", "2024-01-25", "2024-02-01"]
            ),
        }
    )
    financials = pd.DataFrame(
        {
            "ts_code": ["000001.SZ", "000001.SZ"],
            "ann_date": ["20240105", "20240122"],
            "end_date": ["20231231", "20240331"],
            "roe": [10.0, 2.5],
        }
    )

    result = align_financials_to_daily(daily, financials, ["roe"])

    # 2024-01-01：无财报可用（第一个公告在 01-05）→ NaN
    assert pd.isna(result.loc[0, "roe"])
    # 2024-01-10：用 01-05 公告的 10.0
    assert result.loc[1, "roe"] == 10.0
    # 2024-01-20：仍用 10.0（01-22 还没公告）
    assert result.loc[2, "roe"] == 10.0
    # 2024-01-25：用 01-22 公告的 2.5
    assert result.loc[3, "roe"] == 2.5
    # 2024-02-01：仍用 2.5
    assert result.loc[4, "roe"] == 2.5


def test_align_duplicate_ann_date_keeps_latest_end_date():
    """同一 ann_date 多条记录：保留 end_date 最新的。"""
    daily = pd.DataFrame(
        {
            "symbol": ["000001"],
            "date": pd.to_datetime(["2024-01-10"]),
        }
    )
    financials = pd.DataFrame(
        {
            "ts_code": ["000001.SZ", "000001.SZ"],
            "ann_date": ["20240105", "20240105"],  # 同一天公告两条
            "end_date": ["20231231", "20230930"],  # end_date 不同
            "roe": [10.0, 7.0],
        }
    )

    result = align_financials_to_daily(daily, financials, ["roe"])

    # 应保留 end_date 更大的 20231231 那条 → roe = 10.0
    assert result.loc[0, "roe"] == 10.0


def test_align_multiple_symbols():
    """多只股票各自独立对齐，不串数据。"""
    daily = pd.DataFrame(
        {
            "symbol": ["000001", "000002", "000001", "000002"],
            "date": pd.to_datetime(
                ["2024-01-10", "2024-01-10", "2024-01-30", "2024-01-30"]
            ),
        }
    )
    financials = pd.DataFrame(
        {
            "ts_code": ["000001.SZ", "000002.SZ"],
            "ann_date": ["20240105", "20240120"],
            "end_date": ["20231231", "20231231"],
            "roe": [10.0, 20.0],
        }
    )

    result = align_financials_to_daily(daily, financials, ["roe"])

    # 000001 在 01-10 生效：10.0；01-30：10.0
    assert (
        result[(result["symbol"] == "000001") & (result["date"] == "2024-01-10")].iloc[
            0
        ]["roe"]
        == 10.0
    )
    assert (
        result[(result["symbol"] == "000001") & (result["date"] == "2024-01-30")].iloc[
            0
        ]["roe"]
        == 10.0
    )
    # 000002 在 01-10 生效：NaN（公告在 01-20）；01-30：20.0
    assert pd.isna(
        result[(result["symbol"] == "000002") & (result["date"] == "2024-01-10")].iloc[
            0
        ]["roe"]
    )
    assert (
        result[(result["symbol"] == "000002") & (result["date"] == "2024-01-30")].iloc[
            0
        ]["roe"]
        == 20.0
    )
