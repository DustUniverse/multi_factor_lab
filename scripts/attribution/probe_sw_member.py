"""T1.1-prep-2: 补探申万一级行业成分股接口。

测试：
1. index_member_all  申万行业历史成分（积分要求高，含进出日期）
2. index_member      申万行业当前成分（积分要求低）
3. index_weight 换一个调仓日再拉一次，确认 52 期批量可行

用法（项目根目录、激活 .venv 后）：
    python scripts/attribution/probe_sw_member.py
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
        print(df.head(3).to_string())
    except Exception as e:  # noqa: BLE001
        print(f"  失败: {type(e).__name__}: {e}")


def main() -> None:
    ts.set_token(get_token())
    pro = ts.pro_api()

    probe(
        "1. index_member_all 申万一级 801010",
        lambda: pro.index_member_all(l1_code="801010.SI"),
    )
    probe(
        "2. index_member 申万一级 801010",
        lambda: pro.index_member(index_code="801010.SI"),
    )
    probe(
        "3. index_weight HS300 2021-06",
        lambda: pro.index_weight(
            index_code="399300.SZ", start_date="20210601", end_date="20210630"
        ),
    )
    print("\n补探结束。")


if __name__ == "__main__":
    main()
