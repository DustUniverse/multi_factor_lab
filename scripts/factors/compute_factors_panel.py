"""在 10 股票面板上计算 3 个因子：动量 / 反转 / 波动率。

输入：data/raw/daily_panel_10.parquet
输出：data/processed/daily_panel_10_factors.parquet
      新增列：momentum_20、reversal_20、volatility_20
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))  # noqa: E402

from mfalpha.common.constants import DATA_DIR  # noqa: E402
from mfalpha.factors.momentum import momentum  # noqa: E402
from mfalpha.factors.reversal import reversal  # noqa: E402
from mfalpha.factors.volatility import volatility  # noqa: E402


def main() -> None:
    """读面板 → 每只股票内部算 3 个因子 → 落盘 + 手工核算。"""
    panel = pd.read_parquet(DATA_DIR / "daily_panel_10.parquet")
    panel = panel.sort_values(["symbol", "date"]).reset_index(drop=True)

    # 关键：按 symbol 分组，组内用因子函数算值
    # transform 把每组结果贴回原始行，索引自动对齐，不会串
    grouped = panel.groupby("symbol", group_keys=False)["close"]
    panel["momentum_20"] = grouped.transform(lambda s: momentum(s, window=20))
    panel["reversal_20"] = grouped.transform(lambda s: reversal(s, window=20))
    panel["volatility_20"] = grouped.transform(lambda s: volatility(s, window=20))

    # 落盘
    out_dir = PROJECT_ROOT / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "daily_panel_10_factors.parquet"
    panel.to_parquet(out_path, index=False)
    print(f"已写入 {out_path}，shape = {panel.shape}")
    print(f"列名：{list(panel.columns)}")

    # 手工核算：600519 最后一行
    sub = panel[panel["symbol"] == "600519"].sort_values("date").reset_index(drop=True)
    manual_mom = sub["close"].iloc[-1] / sub["close"].iloc[-21] - 1
    auto_mom = sub["momentum_20"].iloc[-1]
    print(f"\n600519 动量手算 = {manual_mom:.6f}")
    print(f"600519 动量函数 = {auto_mom:.6f}")
    assert abs(manual_mom - auto_mom) < 1e-9, "动量手算与函数结果不一致！"
    assert abs(sub["reversal_20"].iloc[-1] + auto_mom) < 1e-9, "反转≠-动量"

    # 检查每只股票 NaN 数（3 个因子都应该 = 20）
    print("\n每只股票各因子 NaN 数（应都=20）：")
    nan_summary = panel.groupby("symbol")[
        ["momentum_20", "reversal_20", "volatility_20"]
    ].apply(lambda g: g.isna().sum())
    print(nan_summary)

    print("\n✅ 三个因子计算完成，手工核算通过")


if __name__ == "__main__":
    main()
