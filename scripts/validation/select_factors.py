"""M5: 剔除冗余因子，落盘最终因子清单与选中面板。

输入:
    data/processed/factor_panel_neutralized.parquet
    data/processed/vif_summary.csv

输出:
    data/processed/selected_factors.json        # 保留清单 + 剔除记录
    data/processed/factor_panel_selected.parquet # 仅含保留因子的面板

用法:
    python scripts/validation/select_factors.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

NEUTRALIZED_PATH = DATA_PROCESSED / "factor_panel_neutralized.parquet"
VIF_SUMMARY_PATH = DATA_PROCESSED / "vif_summary.csv"

SELECTED_JSON_PATH = DATA_PROCESSED / "selected_factors.json"
SELECTED_PANEL_PATH = DATA_PROCESSED / "factor_panel_selected.parquet"

# 最终保留（按 VIF 分析 + M4 业绩综合决策）
KEEP_FACTORS = [
    "turnover",
    "volatility_20",
    "amihud_20",
    "bp",
    "corr_pv_20",
    "reversal_20",
    "bias_20",
    "ep_ttm",
]

# 剔除记录（因子 -> 剔除理由）
DROPPED_FACTORS = {
    "momentum_20": "与 reversal_20 完全镜像（VIF=inf）",
    "amplitude_20": "与 volatility_20 孪生（同族同单调性，vif_mean 5.44）",
    "rsi_14": "与 bias_20 同族，IR/Sharpe/单调性全面更弱（vif_mean 6.30）",
    "boll_dev_20": "与 bias_20 分子相同，单调性 0.394 全组最差（vif_mean 5.04）",
}


def load_neutralized_panel() -> pd.DataFrame:
    df = pd.read_parquet(NEUTRALIZED_PATH)
    if not isinstance(df.index, pd.MultiIndex):
        if "date" in df.columns and "symbol" in df.columns:
            df = df.set_index(["date", "symbol"])
        else:
            raise ValueError("无法识别面板索引格式。")
    return df.sort_index()


def main() -> None:
    panel = load_neutralized_panel()
    print(f"中性化面板: {panel.shape}，列={list(panel.columns)}")

    # 校验：KEEP + DROPPED 应覆盖全部列
    all_cols = set(panel.columns)
    keep_set = set(KEEP_FACTORS)
    drop_set = set(DROPPED_FACTORS.keys())

    missing = keep_set - all_cols
    if missing:
        raise ValueError(f"KEEP_FACTORS 中有面板里不存在的列: {missing}")

    uncovered = all_cols - keep_set - drop_set
    if uncovered:
        raise ValueError(f"以下列既未保留也未说明剔除理由: {uncovered}")

    # 生成选中面板（保持原索引顺序，只保留 KEEP 列）
    selected = panel[KEEP_FACTORS].copy()
    selected.to_parquet(SELECTED_PANEL_PATH)
    print(f"选中面板已保存: {SELECTED_PANEL_PATH}")
    print(f"选中面板 shape: {selected.shape}")

    # 读取 VIF 汇总，附在 JSON 里作为决策依据
    vif_note = {}
    if VIF_SUMMARY_PATH.exists():
        vif_df = pd.read_csv(VIF_SUMMARY_PATH, index_col=0)
        for f in KEEP_FACTORS:
            if f in vif_df.index:
                vif_note[f] = {
                    "vif_mean": float(vif_df.loc[f, "vif_mean"]),
                    "vif_median": float(vif_df.loc[f, "vif_median"]),
                }

    payload = {
        "method": "M5 VIF 共线性检验 + M4 中性化业绩综合决策",
        "vif_threshold": 5,
        "keep": KEEP_FACTORS,
        "keep_count": len(KEEP_FACTORS),
        "dropped": DROPPED_FACTORS,
        "dropped_count": len(DROPPED_FACTORS),
        "vif_reference": vif_note,
        "note": (
            "vif_reference 来自剔除前的 vif_summary.csv，仅作决策依据留档；"
            "最终 8 因子的 VIF 全部 < 5。"
        ),
    }

    with open(SELECTED_JSON_PATH, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    print(f"清单已保存: {SELECTED_JSON_PATH}")
    print(f"保留 {len(KEEP_FACTORS)} 个，剔除 {len(DROPPED_FACTORS)} 个")


if __name__ == "__main__":
    main()
