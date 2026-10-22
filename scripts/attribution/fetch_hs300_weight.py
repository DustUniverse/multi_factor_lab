"""T1.1-prep: 分年份拉取 HS300 成分权重（2020–2024）。

单次查询 5 年超过 tushare 返回行数上限，改为按年份循环。
输出覆盖 data/processed/hs300_weight.parquet。

用法（项目根目录、激活 .venv 后）：
    python scripts/attribution/fetch_hs300_weight.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))

try:
    import tushare as ts
except ImportError:
    print("请先安装 tushare：pip install tushare")
    raise

PROCESSED = _ROOT / "data" / "processed"
HS300_OUT = PROCESSED / "hs300_weight.parquet"

INDEX_CODE = "399300.SZ"
YEARS = [2020, 2021, 2022, 2023, 2024]


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


def main() -> None:
    ts.set_token(get_token())
    pro = ts.pro_api()

    frames = []
    for y in YEARS:
        print(f"[{y}] 拉取 HS300 成分权重 ...")
        try:
            df = pro.index_weight(
                index_code=INDEX_CODE,
                start_date=f"{y}0101",
                end_date=f"{y}1231",
            )
        except Exception as e:  # noqa: BLE001
            print(f"  {y} 失败: {e}")
            continue
        if df is None or len(df) == 0:
            print(f"  {y} 返回空")
            continue
        print(f"  行数: {len(df)}，调整日数: {df['trade_date'].nunique()}")
        frames.append(df)
        time.sleep(0.3)

    if not frames:
        raise RuntimeError("所有年份都拉取失败")

    out = pd.concat(frames, ignore_index=True)
    out["trade_date"] = pd.to_datetime(out["trade_date"], format="%Y%m%d")
    out["con_code"] = out["con_code"].astype(str)
    out = out[["trade_date", "con_code", "weight"]]
    out = out.drop_duplicates(subset=["trade_date", "con_code"])
    out = out.sort_values(["trade_date", "con_code"]).reset_index(drop=True)

    out.to_parquet(HS300_OUT, index=False)
    print(f"\n保存: {HS300_OUT}")
    print(f"总行数: {len(out)}")
    print(f"调整日数: {out['trade_date'].nunique()}")
    print(
        f"日期范围: {out['trade_date'].min().date()} ~ {out['trade_date'].max().date()}"
    )
    year_counts = (
        out.groupby(out["trade_date"].dt.year)["trade_date"].nunique().to_dict()
    )
    print(f"每年调整日: {year_counts}")
    print(f"每年行数: {out.groupby(out['trade_date'].dt.year).size().to_dict()}")
    print("\n完成。")


if __name__ == "__main__":
    main()
