"""估值类因子：E/P、B/P。

这两个是逐行变换（非时序滚动），输入输出均为等长 Series。
"""

import numpy as np
import pandas as pd


def ep_ttm(pe_ttm: pd.Series) -> pd.Series:
    """E/P = 1 / PE_TTM（市盈率倒数）。

    PE_TTM <= 0 或 NaN 时返回 NaN（负 PE 无经济含义，亏损股没有有效的 E/P）。
    相比直接用 PE，E/P 在横截面上更接近正态、更适合标准化。
    """
    pe = pd.to_numeric(pe_ttm, errors="coerce")
    result = pd.Series(np.nan, index=pe.index, dtype="float64")
    valid = pe > 0
    result.loc[valid] = 1.0 / pe.loc[valid]
    return result


def bp(pb: pd.Series) -> pd.Series:
    """B/P = 1 / PB（市净率倒数）。

    PB <= 0 或 NaN 时返回 NaN（净资产为负的公司无有效 B/P）。
    """
    pb_num = pd.to_numeric(pb, errors="coerce")
    result = pd.Series(np.nan, index=pb_num.index, dtype="float64")
    valid = pb_num > 0
    result.loc[valid] = 1.0 / pb_num.loc[valid]
    return result
