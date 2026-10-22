"""T1.1-prep: 探查行业与基准成分数据源可用性。

测试 Tushare 三个接口能否调通：
1. index_classify  申万一级行业列表（积分要求低）
2. stock_basic     个股行业映射（积分要求低）
3. index_weight    HS300 成分权重（积分要求高，可能失败）

用法（项目根目录、激活 .venv 后）：
    python scripts/attribution/probe_data_sources.py
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
    """从环境变量或 .env 读取 Tushare token。"""
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
        "1. index_classify 申万一级",
        lambda: pro.index_classify(level="L1", src="SW2021"),
    )
    probe(
        "2. stock_basic 个股行业",
        lambda: pro.stock_basic(fields="ts_code,symbol,name,industry,list_date"),
    )
    probe(
        "3. index_weight HS300 成分权重 2020-06",
        lambda: pro.index_weight(
            index_code="399300.SZ", start_date="20200601", end_date="20200630"
        ),
    )
    print("\n探查结束。")


if __name__ == "__main__":
    main()
