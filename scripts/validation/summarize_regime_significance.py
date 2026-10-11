"""
M7 S2: 稳健性显著性汇总

读 regime_ic_summary.csv，对每个因子在每个持有期统计:
    - 在几种市场状态下 |t_stat| > 1.96 (5% 显著性)
    - 各状态 IC 符号是否一致
    - 是否满足"至少 2 种市场环境显著"的验收标准

输出:
    data/processed/regime_significance_summary.csv

用法:
    python scripts/validation/summarize_regime_significance.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = PROJECT_ROOT / "data" / "processed"

IN_PATH = PROCESSED / "regime_ic_summary.csv"
OUT_PATH = PROCESSED / "regime_significance_summary.csv"

T_THRESHOLD = 1.96
REGIMES = ("bull", "flat", "bear")
PERIODS = ("1D", "5D", "20D")


def main() -> None:
    print(f"[1/2] 读取: {IN_PATH}")
    df = pd.read_csv(IN_PATH)
    print(f"      shape={df.shape}, periods={sorted(df['period'].unique())}")

    rows = []
    for period in PERIODS:
        sub_p = df[df["period"] == period]
        if sub_p.empty:
            continue
        for factor, g in sub_p.groupby("factor"):
            g = g.set_index("regime")
            # 各状态是否显著
            sig = {
                reg: bool(abs(g.loc[reg, "t_stat"]) > T_THRESHOLD)
                for reg in REGIMES
                if reg in g.index
            }
            n_sig = sum(sig.values())
            # IC 符号是否一致
            ic_signs = set(
                np.sign(g.loc[reg, "IC_mean"]) for reg in REGIMES if reg in g.index
            )
            sign_consistent = len(ic_signs) == 1

            rows.append(
                {
                    "period": period,
                    "factor": factor,
                    "n_regimes": len(sig),
                    "n_significant": n_sig,
                    "sig_bull": sig.get("bull", False),
                    "sig_flat": sig.get("flat", False),
                    "sig_bear": sig.get("bear", False),
                    "sign_consistent": sign_consistent,
                    "IC_mean_bull": (
                        g.loc["bull", "IC_mean"] if "bull" in g.index else np.nan
                    ),
                    "IC_mean_flat": (
                        g.loc["flat", "IC_mean"] if "flat" in g.index else np.nan
                    ),
                    "IC_mean_bear": (
                        g.loc["bear", "IC_mean"] if "bear" in g.index else np.nan
                    ),
                    "min_abs_t": float(g["t_stat"].abs().min()),
                }
            )

    out = pd.DataFrame(rows)
    out = out.sort_values(
        ["period", "n_significant", "factor"], ascending=[True, False, True]
    ).reset_index(drop=True)
    out.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n[2/2] 写入: {OUT_PATH}")

    # 打印汇总
    for period in PERIODS:
        sub = out[out["period"] == period]
        if sub.empty:
            continue
        n_pass_2 = int((sub["n_significant"] >= 2).sum())
        n_pass_3 = int((sub["n_significant"] == 3).sum())
        print(f"\n=== 持有期 {period} ===")
        print(f"  因子总数: {len(sub)}")
        print(f"  ≥2 种状态显著 (达标): {n_pass_2} / {len(sub)}")
        print(f"  3 种状态全部显著:     {n_pass_3} / {len(sub)}")
        print(
            f"  符号全部一致:         "
            f"{int(sub['sign_consistent'].sum())} / {len(sub)}"
        )

    # 20D 明细
    sub20 = out[out["period"] == "20D"]
    if not sub20.empty:
        print("\n=== 20D 明细 ===")
        cols = [
            "factor",
            "n_significant",
            "sig_bull",
            "sig_flat",
            "sig_bear",
            "sign_consistent",
            "min_abs_t",
        ]
        print(sub20[cols].to_string(index=False))

    # 验收标准
    print("\n=== 带教验收标准核对 ===")
    ok = True
    for period in PERIODS:
        sub = out[out["period"] == period]
        if sub.empty:
            continue
        n_pass = int((sub["n_significant"] >= 2).sum())
        target = len(sub)
        status = "✅" if n_pass == target else f"⚠️ ({n_pass}/{target})"
        print(f"  {period}: 全部因子 ≥2 种状态显著  {status}")
        if n_pass != target:
            ok = False
    print(f"\n总体: {'✅ 满足带教验收标准' if ok else '⚠️ 部分因子需关注'}")


if __name__ == "__main__":
    main()
