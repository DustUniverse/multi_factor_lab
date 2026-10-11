"""
M6 S4a: 稳健性检验可视化

读:
    data/processed/regime_ic_summary.csv
    data/processed/regime_ls_sharpe.csv
    data/processed/sector_ic_summary.csv
写:
    docs/figures/stage2/regime/ic_heatmap_regime.png
    docs/figures/stage2/regime/sharpe_heatmap_regime.png
    docs/figures/stage2/sector/ic_heatmap_sector.png

用法:
    python scripts/validation/plot_robustness.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = PROJECT_ROOT / "data" / "processed"
FIG_REGIME = PROJECT_ROOT / "docs" / "figures" / "stage2" / "regime"
FIG_SECTOR = PROJECT_ROOT / "docs" / "figures" / "stage2" / "sector"
FIG_REGIME.mkdir(parents=True, exist_ok=True)
FIG_SECTOR.mkdir(parents=True, exist_ok=True)

REGIME_IC = PROCESSED / "regime_ic_summary.csv"
REGIME_LS = PROCESSED / "regime_ls_sharpe.csv"
SECTOR_IC = PROCESSED / "sector_ic_summary.csv"

REGIMES = ["bull", "flat", "bear"]
SECTORS = ["主板", "创业板", "科创板"]
PERIOD = "20D"


def heatmap(
    mat: pd.DataFrame,
    out_path: Path,
    title: str,
    cbar_label: str,
    fmt: str = "{:.3f}",
    center_zero: bool = True,
    figsize: tuple[float, float] = (7, 6),
) -> None:
    """通用热力图：行=因子，列=分组（regime/sector）。"""
    n_r, n_c = mat.shape
    vmax = (
        float(np.nanmax(np.abs(mat.values)))
        if center_zero
        else float(np.nanmax(mat.values))
    )
    if not np.isfinite(vmax) or vmax == 0:
        vmax = 1.0

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(
        mat.values,
        cmap="RdBu_r" if center_zero else "viridis",
        vmin=-vmax if center_zero else 0,
        vmax=vmax,
        aspect="auto",
    )

    ax.set_xticks(np.arange(n_c))
    ax.set_xticklabels(mat.columns)
    ax.set_yticks(np.arange(n_r))
    ax.set_yticklabels(mat.index)
    ax.set_title(title, fontsize=13)

    # 单元格内写数字
    for i in range(n_r):
        for j in range(n_c):
            v = mat.values[i, j]
            if np.isnan(v):
                s = "NaN"
                color = "gray"
            else:
                s = fmt.format(v)
                color = "white" if abs(v) > vmax * 0.55 else "black"
            ax.text(j, i, s, ha="center", va="center", color=color, fontsize=10)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label(cbar_label)

    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"      写入: {out_path}")


def main() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False

    # ---------- 1. regime IC 热力图 (20D) ----------
    print("[1/3] regime IC 热力图 (20D)")
    ic = pd.read_csv(REGIME_IC)
    sub = ic[ic["period"] == PERIOD]
    mat = sub.pivot(index="factor", columns="regime", values="IC_mean")
    mat = mat.reindex(columns=REGIMES)
    # 按 |IC| 均值降序，视觉上更整齐
    mat = mat.reindex(mat.abs().mean(axis=1).sort_values(ascending=False).index)
    heatmap(
        mat,
        FIG_REGIME / "ic_heatmap_regime.png",
        title=f"{PERIOD} IC 均值 — 因子 × 市场状态",
        cbar_label="IC_mean",
        fmt="{:.3f}",
        center_zero=True,
    )

    # ---------- 2. regime 多空 Sharpe 热力图 (20D) ----------
    print("[2/3] regime 多空 Sharpe 热力图 (20D)")
    ls = pd.read_csv(REGIME_LS)
    mat = ls.pivot(index="factor", columns="regime", values="LS_Sharpe_ann")
    mat = mat.reindex(columns=REGIMES)
    mat = mat.reindex(mat.abs().mean(axis=1).sort_values(ascending=False).index)
    heatmap(
        mat,
        FIG_REGIME / "sharpe_heatmap_regime.png",
        title=f"{PERIOD} 多空 Sharpe (Q10-Q1, 年化) — 因子 × 市场状态",
        cbar_label="Sharpe (ann.)",
        fmt="{:.2f}",
        center_zero=True,
    )

    # ---------- 3. sector IC 热力图 (20D) ----------
    print("[3/3] sector IC 热力图 (20D)")
    sic = pd.read_csv(SECTOR_IC)
    sub = sic[sic["period"] == PERIOD]
    mat = sub.pivot(index="factor", columns="sector", values="IC_mean")
    mat = mat.reindex(columns=SECTORS)
    mat = mat.reindex(mat.abs().mean(axis=1).sort_values(ascending=False).index)
    heatmap(
        mat,
        FIG_SECTOR / "ic_heatmap_sector.png",
        title=f"{PERIOD} IC 均值 — 因子 × 板块",
        cbar_label="IC_mean",
        fmt="{:.3f}",
        center_zero=True,
    )

    print("\n完成。")


if __name__ == "__main__":
    main()
