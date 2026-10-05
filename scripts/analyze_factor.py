"""Alphalens 因子分析脚本：输入面板 parquet + 因子列名，输出 IC 三类图与汇总表。

用法示例：
    python scripts/analyze_factor.py
    python scripts/analyze_factor.py --factor momentum_20 --quantiles 5
    python scripts/analyze_factor.py --factor volatility_20 \\
        --quantiles 10 --periods 1,5,10,20
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 必须在 import pyplot 之前

import alphalens  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))  # noqa: E402

from mfalpha.common.constants import DATA_DIR  # noqa: E402

DEFAULT_PANEL = DATA_DIR.parent / "processed" / "daily_panel_10_factors.parquet"
DEFAULT_OUTDIR = PROJECT_ROOT / "docs" / "figures" / "alphalens_ic"


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    Returns:
        解析结果，含 panel/factor/quantiles/periods/outdir 五个属性。
    """
    parser = argparse.ArgumentParser(description="Alphalens 因子 IC 分析")
    parser.add_argument(
        "--panel", type=Path, default=DEFAULT_PANEL, help="面板 parquet 路径"
    )
    parser.add_argument("--factor", type=str, default="momentum_20", help="因子列名")
    parser.add_argument("--quantiles", type=int, default=5, help="分层数")
    parser.add_argument(
        "--periods", type=str, default="1,5,10", help="未来收益期，逗号分隔"
    )
    parser.add_argument(
        "--outdir", type=Path, default=DEFAULT_OUTDIR, help="图片输出目录"
    )
    return parser.parse_args()


def _tidy_date_axes(fig: Figure) -> None:
    """针对日期横轴：简化刻度、旋转标签、拉开子图间距。"""
    for ax in fig.axes:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.tick_params(axis="x", rotation=30, labelsize=8)
        ax.tick_params(axis="y", labelsize=8)
    fig.subplots_adjust(hspace=0.55, wspace=0.35)


def _ic_ts_fig_height(n_periods: int) -> float:
    """IC 时间序列图高度：随收益期数增加而增长，避免子图重叠。

    Args:
        n_periods: 收益期个数（如 1,5,10 就是 3 个）。

    Returns:
        建议的画布高度（英寸）。
    """
    n_panels = n_periods + 2  # Alphalens 还会额外画 factor 和 factor_quantile 两栏
    return max(10.0, 2.4 * n_panels)


def _tidy_numeric_axes(fig: Figure) -> None:
    """针对数值横轴：直接 tight_layout，避免与日期轴逻辑打架。"""
    fig.tight_layout()


def main() -> None:
    """主流程：读面板 → 对齐未来收益 → 出 IC 图 → 打印汇总。"""
    args = parse_args()
    periods = tuple(int(p) for p in args.periods.split(","))

    panel = pd.read_parquet(args.panel)
    if args.factor not in panel.columns:
        raise ValueError(
            f"因子列 {args.factor!r} 不在面板中，可用列：{list(panel.columns)}"
        )

    factor = panel.set_index(["date", "symbol"])[args.factor]
    prices = panel.pivot(index="date", columns="symbol", values="close")

    factor_data = alphalens.utils.get_clean_factor_and_forward_returns(
        factor=factor,
        prices=prices,
        quantiles=args.quantiles,
        periods=periods,
    )

    outdir = args.outdir / args.factor
    outdir.mkdir(parents=True, exist_ok=True)

    # 图 1：IC 时间序列
    alphalens.plotting.plot_ic_ts(factor_data)
    fig = plt.gcf()
    fig.set_size_inches(16, _ic_ts_fig_height(len(periods)))  # 随 periods 数量自适应
    _tidy_date_axes(fig)
    fig.savefig(outdir / "ic_ts.png", dpi=110, bbox_inches="tight")
    plt.close("all")

    # 图 2：IC 分布直方图
    alphalens.plotting.plot_ic_hist(factor_data)
    fig = plt.gcf()
    fig.set_size_inches(14, 9)
    _tidy_numeric_axes(fig)
    fig.savefig(outdir / "ic_hist.png", dpi=110, bbox_inches="tight")
    plt.close("all")

    # 图 3：IC QQ 图
    alphalens.plotting.plot_ic_qq(factor_data)
    fig = plt.gcf()
    fig.set_size_inches(14, 10)
    _tidy_numeric_axes(fig)
    fig.savefig(outdir / "ic_qq.png", dpi=110, bbox_inches="tight")
    plt.close("all")

    print(f"图片已保存到: {outdir}")

    ic = alphalens.performance.factor_information_coefficient(factor_data)
    summary = pd.DataFrame(
        {
            "IC_mean": ic.mean(),
            "IC_std": ic.std(),
            "ICIR": ic.mean() / ic.std(),
        }
    )
    print("\n===== IC 汇总 =====")
    print(summary)


if __name__ == "__main__":
    main()
