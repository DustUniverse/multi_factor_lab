"""M2 前置：因子归因数据结构验证。

只确认结构，不做归因计算：
1. factor_panel_neutralized 的 index/columns/日期范围；
2. 8 因子是否齐全、符号方向；
3. quantile_returns 日期语义；
4. 取一期持仓，看因子快照能否对上。

运行：
    python scripts/stage4/attribution/m2_precheck.py
"""

from pathlib import Path

import pandas as pd

PROCESSED = Path("data/processed")
GROUP = "lasso_horizon_all8"
TGT_TRADE = "2023-01-03"
TGT_SIGNAL = "2022-12-30"


def main():
    # 1. 因子清单
    fl = pd.read_csv(PROCESSED / "final_factor_list.csv")
    print("=== final_factor_list.csv ===")
    print(fl.to_string())
    factor_cols = fl["factor"].tolist()

    # 2. factor_panel_neutralized 结构（272MB，耐心等）
    print("\n=== factor_panel_neutralized.parquet ===")
    fp = pd.read_parquet(PROCESSED / "factor_panel_neutralized.parquet")
    print("shape:", fp.shape)
    print("index type:", type(fp.index).__name__)
    print("index names:", getattr(fp.index, "names", None))
    print("columns 数:", len(fp.columns))
    print("columns 前 20:", list(fp.columns)[:20])
    if isinstance(fp.index, pd.MultiIndex):
        lv0 = fp.index.get_level_values(0)
        lv1 = fp.index.get_level_values(1)
        print(f"level0 范围: {lv0.min()} ~ {lv0.max()}, 唯一数={lv0.nunique()}")
        print(f"level1 样例: {lv1.unique()[:5].tolist()}")
    else:
        print(f"index 范围: {fp.index.min()} ~ {fp.index.max()}")
        print("index 样例:", fp.index[:5].tolist())

    # 3. 因子齐全性
    missing = [f for f in factor_cols if f not in fp.columns]
    print("\n缺失因子:", missing if missing else "无")
    print("flipped:", fl[["factor", "flipped"]].to_dict("records"))

    # 4. quantile_returns 日期语义
    print("\n=== quantile_returns_volatility_20.csv ===")
    qr = pd.read_csv(PROCESSED / "quantile_returns_volatility_20.csv")
    print("shape:", qr.shape)
    print("columns 前 15:", list(qr.columns)[:15])
    print("date 首 3:", qr["Unnamed: 0"].head(3).tolist())
    print("date 尾 3:", qr["Unnamed: 0"].tail(3).tolist())
    print("Q0 vs Q9 首行:", qr.iloc[0, 1], qr.iloc[0, 10])

    # 5. 因子快照与持仓对齐
    print("\n=== 2023-01-03 持仓 vs 2022-12-30 因子快照 ===")
    h = pd.read_csv(
        PROCESSED / f"composite_holdings_{GROUP}.csv", dtype={"symbol": str}
    )
    h["symbol"] = h["symbol"].str.zfill(6)
    h_t = h[h["trade_date"] == TGT_TRADE]
    print(f"持仓 {len(h_t)} 只，前 5:", h_t["symbol"].tolist()[:5])

    if isinstance(fp.index, pd.MultiIndex):
        try:
            fp_t = fp.xs(pd.Timestamp(TGT_SIGNAL), level=0)
            print("快照行数:", len(fp_t))
            print("快照 index 样例:", fp_t.index[:5].tolist())
            print("快照前 3 行:\n", fp_t.head(3).to_string())
            # 持仓能否对上
            syms = h_t["symbol"].tolist()
            overlap = len(set(syms) & set(fp_t.index.astype(str)))
            print(f"持仓与快照 symbol 重合: {overlap}/{len(syms)}")
        except KeyError:
            print(
                f"快照 {TGT_SIGNAL} 不在 index 中，可用日期样例:",
                fp.index.get_level_values(0).unique()[:5].tolist(),
            )
    else:
        print("非 MultiIndex，需要进一步确认结构")


if __name__ == "__main__":
    main()
