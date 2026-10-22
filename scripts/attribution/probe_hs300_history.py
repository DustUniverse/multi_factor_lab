"""T1.1-prep-3: 探查 HS300 成分权重历史数据缺失原因。

测试：
1. 000300.SH 拉 2020 年
2. 399300.SZ 分年份拉 2020 / 2021 / 2022
3. index_member_all 拉 HS300 历史成分（可能只有成分无权重）

用法：
    python scripts/attribution/probe_hs300_history.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd  # noqa: F401

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))

try:
    import tushare as ts
except ImportError:
    print("请先安装 tushare：pip install tushare")
    raise


def get_token() -> str:
    token = os.environ.get("TUSHARE_TOKEN", "")
    if token:
        return token
    env_path = _ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TUSHARE_TOKEN"):
                return line.split("=", 1)[1].strip().strip("\"'")
    raise RuntimeError("未找到 TUSHARE_TOKEN，请检查项目根目录 .env")


def probe(name: str, func) -> None:
    print(f"\n--- {name} ---")
    try:
        df = func()
        if df is None or len(df) == 0:
            print("  返回空 DataFrame")
            return
        print(f"  成功，shape={df.shape}")
        print(f"  列: {df.columns.tolist()}")
        if "trade_date" in df.columns:
            print(f"  日期范围: {df['trade_date'].min()} ~ {df['trade_date'].max()}")
            print(f"  调整日数: {df['trade_date'].nunique()}")
        print(df.head(3).to_string())
    except Exception as e:  # noqa: BLE001
        print(f"  失败: {type(e).__name__}: {e}")


def main() -> None:
    ts.set_token(get_token())
    pro = ts.pro_api()

    probe(
        "1. 000300.SH 2020 全年",
        lambda: pro.index_weight(
            index_code="000300.SH", start_date="20200101", end_date="20201231"
        ),
    )
    probe(
        "2. 399300.SZ 2020 全年",
        lambda: pro.index_weight(
            index_code="399300.SZ", start_date="20200101", end_date="20201231"
        ),
    )
    probe(
        "3. 399300.SZ 2021 全年",
        lambda: pro.index_weight(
            index_code="399300.SZ", start_date="20210101", end_date="20211231"
        ),
    )
    probe(
        "4. 399300.SZ 2022 全年",
        lambda: pro.index_weight(
            index_code="399300.SZ", start_date="20220101", end_date="20221231"
        ),
    )
    probe(
        "5. index_member_all HS300 历史成分",
        lambda: pro.index_member_all(index_code="399300.SZ"),
    )
    print("\n探查结束。")


if __name__ == "__main__":
    main()
