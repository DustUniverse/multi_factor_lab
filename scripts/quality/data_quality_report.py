"""生成数据质量校验报告（Markdown）。

输入：data/processed/daily_panel_clean.parquet
输出：docs/reports/data_quality_report.md
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mfalpha.common.constants import DATA_DIR  # noqa: E402

PROCESSED_DIR = DATA_DIR.parent / "processed"
REPORT_DIR = PROJECT_ROOT / "docs" / "reports"

# 报告里要统计的数值列
NUMERIC_COLS = [
    "open",
    "close",
    "high",
    "low",
    "volume",
    "amount",
    "amplitude",
    "pct_chg",
    "change",
    "turnover",
]


def build_report(df: pd.DataFrame) -> str:
    lines = []
    lines.append("# 数据质量校验报告\n")
    lines.append(f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n")

    # 一、基础信息
    lines.append("## 一、基础信息\n")
    lines.append("| 项目 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| 股票数量 | {df['symbol'].nunique()} |")
    lines.append(f"| 交易日数量 | {df['date'].nunique()} |")
    lines.append(f"| 总行数 | {len(df)} |")
    lines.append(
        f"| 日期范围 | {df['date'].min():%Y-%m-%d} ~ {df['date'].max():%Y-%m-%d} |"
    )
    board_dist = {k: int(v) for k, v in df["board"].value_counts().items()}
    lines.append(f"| 板块分布 | {board_dist} |")
    lines.append("")

    # 二、缺失率
    lines.append("## 二、字段缺失率\n")
    lines.append("| 字段 | 缺失数 | 缺失率 |")
    lines.append("|---|---|---|")
    miss = df.isna().sum()
    miss_rate = df.isna().mean()
    for col in df.columns:
        lines.append(f"| {col} | {miss[col]} | {miss_rate[col]:.4%} |")
    lines.append("")

    # 三、描述性统计
    lines.append("## 三、数值字段描述性统计\n")
    lines.append("| 字段 | 均值 | 标准差 | 最小值 | 25% | 50% | 75% | 最大值 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for col in NUMERIC_COLS:
        s = df[col].describe()
        lines.append(
            f"| {col} | {s['mean']:.4f} | {s['std']:.4f} | {s['min']:.4f} | "
            f"{s['25%']:.4f} | {s['50%']:.4f} | {s['75%']:.4f} | {s['max']:.4f} |"
        )
    lines.append("")

    # 四、异常检查
    lines.append("## 四、异常检查\n")
    lines.append("| 检查项 | 行数 | 占比 |")
    lines.append("|---|---|---|")
    n = len(df)
    checks = {
        "停牌（volume == 0）": df["is_suspended"].sum(),
        "涨停": df["is_limit_up"].sum(),
        "跌停": df["is_limit_down"].sum(),
        "pct_chg 绝对值 > 11": (df["pct_chg"].abs() > 11).sum(),
        "turnover == 0": (df["turnover"] == 0).sum(),
        "close <= 0": (df["close"] <= 0).sum(),
    }
    for name, cnt in checks.items():
        lines.append(f"| {name} | {cnt} | {cnt / n:.4%} |")
    lines.append("")

    # 五、每只股票行数分布
    lines.append("## 五、每只股票行数分布\n")
    per_stock = df.groupby("symbol").size()
    lines.append(f"- 最多：{per_stock.max()} 行")
    lines.append(f"- 最少：{per_stock.min()} 行")
    lines.append(f"- 均值：{per_stock.mean():.1f} 行")
    lines.append(f"- 中位数：{per_stock.median():.1f} 行")
    short = per_stock[per_stock < per_stock.max() * 0.8]
    lines.append(f"- 行数不足 80% 的股票数：{len(short)} 只")
    if len(short) > 0:
        lines.append(f"- 列表：{list(short.index)[:20]}")
    lines.append("")

    # 六、结论
    lines.append("## 六、结论\n")
    max_miss = miss_rate.max()
    if max_miss < 0.02:
        lines.append("- ✅ 所有字段缺失率均低于 2%，达到验收标准")
    else:
        lines.append(f"- ⚠️ 存在字段缺失率 {max_miss:.2%}，超过 2% 阈值")

    if df["is_suspended"].sum() == 0:
        lines.append("- ✅ 无停牌行（前复权数据已排除）")
    else:
        lines.append(f"- ⚠️ 存在 {df['is_suspended'].sum()} 行停牌数据，已标记")

    lines.append(
        f"- 本报告基于 {df['symbol'].nunique()} 只股票样本，扩到全市场后需重新生成\n"
    )

    return "\n".join(lines)


def main() -> None:
    src = PROCESSED_DIR / "daily_panel_clean.parquet"
    df = pd.read_parquet(src)
    print(f"读取面板: {df.shape}")

    report = build_report(df)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / "data_quality_report.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"已生成报告: {out_path}")


if __name__ == "__main__":
    main()
