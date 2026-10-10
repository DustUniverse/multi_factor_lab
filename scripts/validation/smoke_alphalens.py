"""M1-b smoke test: 用 momentum_20 跑通 alphalens 全流程。

只验证 IC、分层收益、图能否正常输出。
不做批量、不落报告，出图保存在 docs/figures/stage2/。
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")  # 无窗口后端，只存文件
import matplotlib.pyplot as plt  # noqa: E402

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# 把 scripts/validation 加入 sys.path，方便 import alphalens_io
sys.path.insert(0, str(Path(__file__).resolve().parent))

from alphalens.performance import (  # noqa: E402
    factor_information_coefficient,
    mean_return_by_quantile,
)
from alphalens.utils import get_clean_factor_and_forward_returns  # noqa: E402
from alphalens_io import load_factor_series, load_prices  # noqa: E402

# 中文字体（Windows 自带）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

FACTOR_NAME = "momentum_20"
PERIODS = (1, 5, 20)
QUANTILES = 10

FIG_DIR = PROJECT_ROOT / "docs" / "figures" / "stage2"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    print(f"[1/5] 读取 prices 与因子 {FACTOR_NAME} ...")
    prices = load_prices()
    factor = load_factor_series(FACTOR_NAME)
    print(f"      prices: {prices.shape}, factor: {factor.shape}")

    print("[2/5] get_clean_factor_and_forward_returns ...")
    factor_data = get_clean_factor_and_forward_returns(
        factor=factor,
        prices=prices,
        quantiles=QUANTILES,
        periods=PERIODS,
        max_loss=0.5,
    )
    print(f"      factor_data: {factor_data.shape}")
    print("      前 3 行：")
    print(factor_data.head(3).to_string())

    print("[3/5] 计算 IC ...")
    ic = factor_information_coefficient(factor_data)
    # 手动计算汇总统计，绕过 mean_information_coefficient 的兼容性问题
    ic_mean = ic.mean()
    ic_std = ic.std()
    icir = ic_mean / ic_std
    ic_win = (ic > 0).mean()

    summary = pd.DataFrame(
        {
            "IC_mean": ic_mean,
            "IC_std": ic_std,
            "ICIR": icir,
            "IC_win": ic_win,
        }
    )
    print("IC 汇总（按持有期）：")
    print(summary.to_string())

    print("[4/5] 计算分层平均收益 ...")
    mean_ret, _std_err = mean_return_by_quantile(factor_data)
    print("      各层平均收益（前 10 行）：")
    print(mean_ret.head(10).to_string())

    print("[5/5] 画图 ...")
    # 图 1：IC 时序（自己画，避开 alphalens plot 函数的兼容性问题）
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, col in zip(axes, ic.columns):
        ax.bar(ic.index, ic[col], width=1.0, color="steelblue", alpha=0.7)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_title(f"IC - {col}")
        ax.set_xlabel("date")
        ax.set_ylabel("IC")
    fig.suptitle(f"{FACTOR_NAME} IC 时序")
    fig.tight_layout()
    ic_path = FIG_DIR / f"smoke_{FACTOR_NAME}_ic_ts.png"
    fig.savefig(ic_path, dpi=120)
    plt.close(fig)
    print(f"      已保存: {ic_path}")

    # 图 2：分层平均收益柱状图
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, col in zip(axes, mean_ret.columns):
        ax.bar(mean_ret.index, mean_ret[col], color="steelblue", alpha=0.7)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_title(f"Quantile Return - {col}")
        ax.set_xlabel("factor_quantile")
        ax.set_ylabel("mean return")
    fig.suptitle(f"{FACTOR_NAME} 分层平均收益")
    fig.tight_layout()
    qr_path = FIG_DIR / f"smoke_{FACTOR_NAME}_quantile_returns.png"
    fig.savefig(qr_path, dpi=120)
    plt.close(fig)
    print(f"      已保存: {qr_path}")

    print("完成。")


if __name__ == "__main__":
    main()
