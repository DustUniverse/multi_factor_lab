"""在 10 股票面板上计算 20 日动量，并做一次手工核算。

输入：data/raw/daily_panel_10.parquet
输出：data/processed/daily_panel_10_momentum.parquet
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))  # noqa: E402

from mfalpha.common.constants import DATA_DIR  # noqa: E402
from mfalpha.factors.momentum import momentum  # noqa: E402


def main() -> None:
    """读面板 → 每只股票内部算动量 → 落盘 + 抽一只手工核算。"""
    panel = pd.read_parquet(DATA_DIR / "daily_panel_10.parquet")
    panel = panel.sort_values(["symbol", "date"]).reset_index(drop=True)

    # 关键：按 symbol 分组，组内用 momentum() 算 20 日动量
    # transform 会把每个组的结果"贴回"原始行，索引自动对齐
    panel["momentum_20"] = panel.groupby("symbol", group_keys=False)["close"].transform(
        lambda s: momentum(s, window=20)
    )

    # 落盘：processed 目录
    out_dir = PROJECT_ROOT / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "daily_panel_10_momentum.parquet"
    panel.to_parquet(out_path, index=False)
    print(f"已写入 {out_path}，shape = {panel.shape}")

    # 手工核算：拿 600519 最后一行，看是否与函数算的一致
    sub = panel[panel["symbol"] == "600519"].sort_values("date").reset_index(drop=True)
    manual = sub["close"].iloc[-1] / sub["close"].iloc[-21] - 1
    auto = sub["momentum_20"].iloc[-1]
    print(f"600519 手算 = {manual:.6f}")
    print(f"600519 函数 = {auto:.6f}")
    assert abs(manual - auto) < 1e-9, "手算与函数结果不一致！"

    # 顺便检查每只股票的动量 NaN 数，应该都 = 20
    print("\n每只股票动量 NaN 数（应都=20）：")
    print(panel.groupby("symbol")["momentum_20"].apply(lambda s: s.isna().sum()))

    print("\n✅ 手工核算通过")


if __name__ == "__main__":
    main()
