"""
M7 S4: 构建最终因子库

1. 读 factor_panel_selected.parquet (8 因子)
2. 按"值越大 -> 预期收益越高"统一方向:
   - 负向因子 (IC < 0) 翻转: turnover, volatility_20, corr_pv_20, bias_20
   - 正向因子保持不变: amihud_20, bp, reversal_20, ep_ttm
3. 落盘:
   - data/processed/factor_panel_final.parquet
   - data/processed/final_factor_list.csv

用法:
    python scripts/validation/build_final_factor_panel.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = PROJECT_ROOT / "data" / "processed"

IN_PATH = PROCESSED / "factor_panel_selected.parquet"
OUT_PANEL = PROCESSED / "factor_panel_final.parquet"
OUT_LIST = PROCESSED / "final_factor_list.csv"

# 因子方向与类别（依据 M2/M6/M7 结论人工确定）
FACTOR_META = {
    "turnover": {
        "flip": True,
        "category": "核心稳健",
        "note": "高换手 -> 低收益；全状态全板块稳健",
    },
    "amihud_20": {
        "flip": False,
        "category": "核心稳健",
        "note": "非流动性溢价；科创板除外",
    },
    "bp": {"flip": False, "category": "进攻型", "note": "价值因子；牛市更强"},
    "ep_ttm": {
        "flip": False,
        "category": "进攻型",
        "note": "盈利收益率；牛市更强，熊市衰减",
    },
    "reversal_20": {
        "flip": False,
        "category": "防御型",
        "note": "短期反转；熊市显著更强",
    },
    "bias_20": {
        "flip": True,
        "category": "防御型",
        "note": "乖离率；熊市更强，翻转后正向",
    },
    "corr_pv_20": {
        "flip": True,
        "category": "防御型",
        "note": "价量相关；熊市更强，翻转后正向",
    },
    "volatility_20": {
        "flip": True,
        "category": "待观察",
        "note": "低波动；三状态均偏弱",
    },
}

# 用于因子清单的 20D IC/ICIR (来自 regime_ic_summary 全样本均值)
# 这里直接从历史 factor_ic_summary 读，若无则留空
FACTOR_IC_REF = {
    "turnover": -0.1054,
    "volatility_20": -0.0947,
    "corr_pv_20": -0.0481,
    "bias_20": -0.0470,
    "amihud_20": 0.0763,
    "bp": 0.0813,
    "reversal_20": 0.0540,
    "ep_ttm": 0.0581,
}


def main() -> None:
    print(f"[1/3] 读取选中面板: {IN_PATH}")
    panel = pd.read_parquet(IN_PATH)
    if not isinstance(panel.index, pd.MultiIndex):
        panel = panel.set_index(["date", "symbol"])
    print(f"      shape={panel.shape}, columns={list(panel.columns)}")

    print("[2/3] 统一因子方向（值越大 -> 预期收益越高）")
    final = panel.copy()
    flip_info = []
    for f in panel.columns:
        if f not in FACTOR_META:
            raise ValueError(f"FACTOR_META 缺少 {f!r}")
        meta = FACTOR_META[f]
        if meta["flip"]:
            final[f] = -final[f]
        flip_info.append((f, meta["flip"], meta["category"]))
        tag = "翻转" if meta["flip"] else "保持"
        print(f"      {f:16s} {tag}  类别={meta['category']}")

    print("[3/3] 落盘")
    OUT_PANEL.parent.mkdir(parents=True, exist_ok=True)
    final.to_parquet(OUT_PANEL)
    print(f"      写入面板: {OUT_PANEL}  shape={final.shape}")

    rows = []
    for f, flip, cat in flip_info:
        ic_raw = FACTOR_IC_REF.get(f, None)
        ic_flip = -ic_raw if (flip and ic_raw is not None) else ic_raw
        rows.append(
            {
                "factor": f,
                "flipped": bool(flip),
                "category": cat,
                "IC_20D_raw": ic_raw,
                "IC_20D_final": ic_flip,
                "note": FACTOR_META[f]["note"],
            }
        )
    list_df = (
        pd.DataFrame(rows).sort_values(["category", "factor"]).reset_index(drop=True)
    )
    list_df.to_csv(OUT_LIST, index=False, encoding="utf-8-sig")
    print(f"      写入清单: {OUT_LIST}")
    print("\n=== 最终因子清单 ===")
    print(list_df.to_string(index=False))

    print("\n完成。最终 8 因子，方向统一为正向。")


if __name__ == "__main__":
    main()
