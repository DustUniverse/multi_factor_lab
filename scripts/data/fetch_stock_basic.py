"""M4 Step1：拉取 Tushare stock_basic，保存行业映射表。

stock_basic 返回全市场股票的基础信息，本项目只用到三个字段：
    ts_code   : 股票代码（如 000001.SZ），与 factor_panel 的 symbol 对齐
    industry  : 所属行业（Tushare 自己的分类，如 "银行" "全国地产"）
    market    : 市场类型（主板/创业板/科创板等）

保存路径：data/processed/stock_basic.parquet

用法（项目根目录、激活 .venv 后）：
    python scripts/data/fetch_stock_basic.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))

try:
    import tushare as ts
except ImportError:
    print("请先安装 tushare：pip install tushare")
    raise

OUT_PATH = _ROOT / "data" / "processed" / "stock_basic.parquet"


def get_token() -> str:
    """从环境变量或 .env 读取 Tushare token。"""
    token = os.environ.get("TUSHARE_TOKEN", "")
    if token:
        return token
    # 尝试从 .env 读
    env_path = _ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TUSHARE_TOKEN"):
                return line.split("=", 1)[1].strip().strip("\"'")
    raise RuntimeError(
        "未找到 TUSHARE_TOKEN。请在项目根目录 .env 文件里加一行：\n"
        "TUSHARE_TOKEN=你的token"
    )


def main() -> None:
    print("[M4 Step1] 拉取 stock_basic ...")
    ts.set_token(get_token())
    pro = ts.pro_api()

    # 拉取所有正常上市股票，只要三个字段
    df = pro.stock_basic(
        exchange="",
        list_status="L",
        fields="ts_code,symbol,name,industry,market,list_date",
    )
    print(f"  拉取到 {len(df)} 行")
    print(f"  列名：{list(df.columns)}")

    if df.empty:
        print("  [WARN] 返回为空，可能是积分不足或 IP 被限")
        return

    # 检查关键字段
    print(f"  industry 非空数：{df['industry'].notna().sum()}")
    print(f"  market 非空数：{df['market'].notna().sum()}")
    print("  market 取值分布：")
    print(df["market"].value_counts().to_string())

    # 行业数量
    n_industry = df["industry"].nunique()
    print(f"  行业数量（去重）：{n_industry}")

    # 保存
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)
    print(f"  已保存：{OUT_PATH}")

    print("\n[M4 Step1] 完成。")


if __name__ == "__main__":
    main()
