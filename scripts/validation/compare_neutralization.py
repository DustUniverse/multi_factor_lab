"""M4 Step4: 对比中性化前后的 IC 和分层回测。

对 12 个因子，分别用原始面板和中性化面板，计算：
    - IC 均值、ICIR、IC 保留率
    - Q10 年化收益、多空夏普、分层单调性

输出：
    data/processed/neutralization_comparison.csv

用法（项目根目录、激活 .venv 后）：
    python scripts/validation/compare_neutralization.py
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_THIS.parent))

from run_quantile_backtest import (  # noqa: E402
    FACTOR_DIRECTIONS,
    MIN_STOCKS_PER_DAY,
    N_QUANTILES,
    PERIOD,
    compute_forward_returns,
    daily_quantile_returns,
    load_prices,
    nav_stats,
    to_daily_nav,
)

NEU_PATH = _ROOT / "data" / "processed" / "factor_panel_neutralized.parquet"
ORIG_PATH = _ROOT / "data" / "processed" / "factor_panel.parquet"
OUT_PATH = _ROOT / "data" / "processed" / "neutralization_comparison.csv"
FACTORS = list(FACTOR_DIRECTIONS.keys())


def load_factor(path: Path, name: str) -> pd.Series:
    """兼容两种存储格式：列里带 date/symbol，或已是 MultiIndex。"""
    head = pd.read_parquet(path)
    if "date" in head.columns and "symbol" in head.columns:
        return head.set_index(["date", "symbol"])[name]
    return head[name]


def compute_ic(factor: pd.Series, fwd_ret: pd.DataFrame) -> tuple[float, float]:
    """返回 (IC 均值, ICIR)。"""
    fw = factor.unstack(level=-1).reindex(index=fwd_ret.index, columns=fwd_ret.columns)
    ics = []
    for dt in fw.index:
        f = fw.loc[dt].values
        r = fwd_ret.loc[dt].values
        valid = np.isfinite(f) & np.isfinite(r)
        if valid.sum() < 100:
            continue
        ics.append(spearmanr(f[valid], r[valid])[0])
    s = pd.Series(ics).dropna()
    return float(s.mean()), float(s.mean() / s.std())


def compute_quantile(
    factor: pd.Series, fwd_ret: pd.DataFrame, prices: pd.DataFrame, sign: int
) -> dict:
    """返回分层回测指标。静默 daily_quantile_returns 的逐日打印。"""
    fw = (
        (factor * sign)
        .unstack(level=-1)
        .reindex(index=prices.index, columns=prices.columns)
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        qret = daily_quantile_returns(fw, fwd_ret, N_QUANTILES, MIN_STOCKS_PER_DAY)
    if qret.empty:
        return {
            "Q10_ann": np.nan,
            "spread": np.nan,
            "ls_sharpe": np.nan,
            "mono": np.nan,
        }

    nav = to_daily_nav(qret, PERIOD)
    stats = nav_stats(nav)
    long_col = nav.columns.max()
    short_col = nav.columns.min()

    spread = stats.loc[long_col, "ann_return"] - stats.loc[short_col, "ann_return"]

    daily = nav.pct_change().dropna(how="all")
    ls = daily[long_col] - daily[short_col]
    ls_sharpe = ls.mean() / ls.std() * np.sqrt(242.0)

    mean_qret = qret.mean()
    rho = spearmanr(mean_qret.index.values, mean_qret.values)[0]

    return {
        "Q10_ann": float(stats.loc[long_col, "ann_return"]),
        "spread": float(spread),
        "ls_sharpe": float(ls_sharpe),
        "mono": float(rho),
    }


def main() -> None:
    print("[M4 Step4] 中性化前后对比")
    print("  加载价格与 forward return ...")
    prices = load_prices()
    fwd_ret = compute_forward_returns(prices, PERIOD)

    rows = []
    for i, fname in enumerate(FACTORS, 1):
        print(f"\n  [{i}/{len(FACTORS)}] {fname}")
        sign = FACTOR_DIRECTIONS[fname]

        f_orig = load_factor(ORIG_PATH, fname)
        ic_o, icir_o = compute_ic(f_orig, fwd_ret)
        q_o = compute_quantile(f_orig, fwd_ret, prices, sign)
        print(
            f"     orig: IC={ic_o:+.4f}  ICIR={icir_o:+.3f}  "
            f"spread={q_o['spread']:+.3f}  LS={q_o['ls_sharpe']:+.2f}  "
            f"mono={q_o['mono']:+.2f}"
        )

        f_neu = load_factor(NEU_PATH, fname)
        ic_n, icir_n = compute_ic(f_neu, fwd_ret)
        q_n = compute_quantile(f_neu, fwd_ret, prices, sign)
        print(
            f"     neu : IC={ic_n:+.4f}  ICIR={icir_n:+.3f}  "
            f"spread={q_n['spread']:+.3f}  LS={q_n['ls_sharpe']:+.2f}  "
            f"mono={q_n['mono']:+.2f}"
        )

        ic_ret = abs(ic_n) / abs(ic_o) * 100 if abs(ic_o) > 1e-9 else np.nan

        rows.append(
            {
                "factor": fname,
                "IC_orig": ic_o,
                "IC_neu": ic_n,
                "IC_retention%": ic_ret,
                "ICIR_orig": icir_o,
                "ICIR_neu": icir_n,
                "spread_orig": q_o["spread"],
                "spread_neu": q_n["spread"],
                "ls_sharpe_orig": q_o["ls_sharpe"],
                "ls_sharpe_neu": q_n["ls_sharpe"],
                "mono_orig": q_o["mono"],
                "mono_neu": q_n["mono"],
                "Q10_ann_orig": q_o["Q10_ann"],
                "Q10_ann_neu": q_n["Q10_ann"],
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("IC_retention%", ascending=False).reset_index(drop=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, float_format="%.4f")
    print(f"\n[M4 Step4] 汇总已保存：{OUT_PATH}")

    print("\n  IC 对比（按保留率排序）：")
    cols1 = ["factor", "IC_orig", "IC_neu", "IC_retention%", "ICIR_orig", "ICIR_neu"]
    print(df[cols1].round(4).to_string(index=False))

    print("\n  分层 / 多空对比：")
    cols2 = [
        "factor",
        "spread_orig",
        "spread_neu",
        "ls_sharpe_orig",
        "ls_sharpe_neu",
        "mono_orig",
        "mono_neu",
        "Q10_ann_orig",
        "Q10_ann_neu",
    ]
    print(df[cols2].round(3).to_string(index=False))

    print("\n[M4 Step4] 完成。")


if __name__ == "__main__":
    main()
