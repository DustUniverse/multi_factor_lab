"""T1.1-prep: 拉取申万一级行业映射与 HS300 成分权重。

输出：
    data/processed/industry_map.parquet
        ts_code, l1_code, l1_name, in_date, out_date
    data/processed/hs300_weight.parquet
        trade_date, con_code, weight

用法（项目根目录、激活 .venv 后）：
    python scripts/attribution/fetch_industry.py
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
INDUSTRY_OUT = PROCESSED / "industry_map.parquet"
HS300_OUT = PROCESSED / "hs300_weight.parquet"

HS300_START = "20200101"
HS300_END = "20241231"


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


def fetch_industry_map(pro) -> pd.DataFrame:
    print("[1/2] 拉取申万一级行业历史成分 ...")
    l1 = pro.index_classify(level="L1", src="SW2021")
    print(f"  申万一级行业数: {len(l1)}")

    frames = []
    for i, row in l1.iterrows():
        code = row["index_code"]
        name = row["industry_name"]
        try:
            df = pro.index_member(index_code=code)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i + 1}/{len(l1)}] {code} {name} 失败: {e}")
            continue
        if df is None or len(df) == 0:
            print(f"  [{i + 1}/{len(l1)}] {code} {name} 空")
            continue
        df = df.copy()
        df["l1_code"] = code
        df["l1_name"] = name
        frames.append(df)
        print(f"  [{i + 1}/{len(l1)}] {code} {name}: {len(df)} 行")
        time.sleep(0.3)

    if not frames:
        raise RuntimeError("所有申万一级行业都拉取失败")

    out = pd.concat(frames, ignore_index=True)
    out = out.rename(columns={"con_code": "ts_code"})
    out["ts_code"] = out["ts_code"].astype(str)
    out["in_date"] = pd.to_datetime(out["in_date"], format="%Y%m%d", errors="coerce")
    out["out_date"] = pd.to_datetime(out["out_date"], format="%Y%m%d", errors="coerce")
    out = out[["ts_code", "l1_code", "l1_name", "in_date", "out_date"]]
    out = out.sort_values(["ts_code", "in_date"]).reset_index(drop=True)

    out.to_parquet(INDUSTRY_OUT, index=False)
    print(f"  保存: {INDUSTRY_OUT}")
    print(f"  总行数: {len(out)}，股票数: {out['ts_code'].nunique()}")
    print(f"  行业数: {out['l1_code'].nunique()}")
    return out


def fetch_hs300_weight(pro) -> pd.DataFrame:
    print("\n[2/2] 拉取 HS300 成分权重 ...")
    df = pro.index_weight(
        index_code="399300.SZ", start_date=HS300_START, end_date=HS300_END
    )
    if df is None or len(df) == 0:
        raise RuntimeError("HS300 成分权重拉取为空")
    df = df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    df["con_code"] = df["con_code"].astype(str)
    df = df[["trade_date", "con_code", "weight"]]
    df = df.sort_values(["trade_date", "con_code"]).reset_index(drop=True)

    df.to_parquet(HS300_OUT, index=False)
    print(f"  保存: {HS300_OUT}")
    print(f"  总行数: {len(df)}")
    print(f"  调整日数: {df['trade_date'].nunique()}")
    print(f"  调整日: {sorted(df['trade_date'].dt.strftime('%Y-%m-%d').unique())}")
    return df


def main() -> None:
    ts.set_token(get_token())
    pro = ts.pro_api()
    fetch_industry_map(pro)
    fetch_hs300_weight(pro)
    print("\n完成。")


if __name__ == "__main__":
    main()
