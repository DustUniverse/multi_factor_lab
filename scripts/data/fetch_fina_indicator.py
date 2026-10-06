"""拉取 Tushare fina_indicator 财务指标（按股票逐只，分批保存）。

输出：
    data/raw/financial/fina_indicator_part_00.parquet
    data/raw/financial/fina_indicator_part_01.parquet
    ...

特性：
- 断点续传：某批 part 文件已存在则跳过
- 股票代码自动转换：000001 → 000001.SZ
- 去重：drop_duplicates() 全列去重

运行：
    python scripts/data/fetch_fina_indicator.py
"""

import os
import time
from pathlib import Path

import pandas as pd
import tushare as ts
from dotenv import load_dotenv

# ---------- 路径 ----------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FACTOR_PANEL = PROJECT_ROOT / "data" / "processed" / "factor_panel.parquet"
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "financial"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Token ----------
load_dotenv(PROJECT_ROOT / ".env")
token = os.getenv("TUSHARE_TOKEN")
if not token:
    raise SystemExit("没读到 TUSHARE_TOKEN，检查根目录 .env")
ts.set_token(token)
pro = ts.pro_api()


# ---------- 股票代码转换 ----------
def to_ts_code(symbol: str) -> str:
    """把 6 位纯数字 symbol 转成 Tushare 格式。

    60xxxx / 68xxxx -> .SH
    00xxxx / 30xxxx -> .SZ
    8xxxxx / 4xxxxx -> .BJ（北交所）
    """
    if symbol.startswith(("60", "68", "9")):
        return f"{symbol}.SH"
    if symbol.startswith(("00", "30", "20")):
        return f"{symbol}.SZ"
    if symbol.startswith(("8", "4")):
        return f"{symbol}.BJ"
    return f"{symbol}.SZ"  # fallback


# ---------- 股票列表 ----------
print("读取现有面板的股票列表...")
symbols = sorted(
    pd.read_parquet(FACTOR_PANEL, columns=["symbol"])["symbol"].unique().tolist()
)
print(f"股票数：{len(symbols)}")

# ---------- 参数 ----------
FIELDS = "ts_code,ann_date,end_date,roe,roe_dt,netprofit_yoy,or_yoy,debt_to_assets"
START_DATE = "20180101"
END_DATE = "20240930"
BATCH_SIZE = 500
REQUEST_INTERVAL = 0.5  # 秒
MAX_RETRIES = 3

n_batches = (len(symbols) + BATCH_SIZE - 1) // BATCH_SIZE
print(f"总批次数：{n_batches}（每批 {BATCH_SIZE} 只）")

# ---------- 分批拉取 ----------
for b in range(n_batches):
    out_file = OUTPUT_DIR / f"fina_indicator_part_{b:02d}.parquet"
    if out_file.exists():
        print(f"[跳过] {out_file.name} 已存在")
        continue

    batch = symbols[b * BATCH_SIZE : (b + 1) * BATCH_SIZE]
    print(f"\n[批次 {b + 1}/{n_batches}] {len(batch)} 只股票")

    rows = []
    for i, sym in enumerate(batch):
        code = to_ts_code(sym)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                df = pro.fina_indicator(
                    ts_code=code,
                    start_date=START_DATE,
                    end_date=END_DATE,
                    fields=FIELDS,
                )
                if df is not None and len(df) > 0:
                    rows.append(df)
                break
            except Exception as e:
                if attempt < MAX_RETRIES:
                    delay = 3 * attempt  # 3s, 6s
                    time.sleep(delay)
                else:
                    print(f"  [错误] {code} 重试 {MAX_RETRIES} 次仍失败：{e}")

        time.sleep(REQUEST_INTERVAL)

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(batch)}")

    if rows:
        part_df = pd.concat(rows, ignore_index=True).drop_duplicates()
        part_df.to_parquet(out_file, index=False)
        print(f"[保存] {out_file.name}：{len(part_df)} 行")
    else:
        print(f"[警告] 批次 {b + 1} 无数据")

print("\n[完成] fina_indicator 全部拉取完毕。")
