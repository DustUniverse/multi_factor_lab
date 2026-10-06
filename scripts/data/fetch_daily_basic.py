"""拉取 Tushare daily_basic 全市场数据（稳健版）。

特性：
- 大幅降低请求频率：每次调用间隔 2 秒
- 指数退避重试：失败后等待时间逐次翻倍（2s, 4s, 8s, 16s, 32s）
- 断点续传：某年文件已存在则跳过
- 失败记录：每日拉取失败会记录并跳过，不中断整体任务
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
FAILED_LOG = OUTPUT_DIR / "daily_basic_failed_dates.txt"

# ---------- Token ----------
load_dotenv(PROJECT_ROOT / ".env")
token = os.getenv("TUSHARE_TOKEN")
if not token:
    raise SystemExit("没读到 TUSHARE_TOKEN，检查根目录 .env")
ts.set_token(token)
pro = ts.pro_api()

# ---------- 交易日列表 ----------
print("读取现有面板的交易日...")
panel_dates = pd.read_parquet(FACTOR_PANEL, columns=["date"])
trade_dates = sorted(panel_dates["date"].dt.strftime("%Y%m%d").unique())
years = sorted({d[:4] for d in trade_dates})
print(f"总交易日 {len(trade_dates)} 天，覆盖年份：{years}")

# ---------- 参数 ----------
FIELDS = "ts_code,trade_date,pe_ttm,pb,turnover_rate,float_share"
REQUEST_INTERVAL = 2.0  # 秒，每次请求后的固定等待时间
MAX_RETRIES = 5  # 最大重试次数
INITIAL_RETRY_DELAY = 2.0  # 秒，首次重试等待时间

# ---------- 逐年拉取 ----------
failed_dates = []
for year in years:
    out_file = OUTPUT_DIR / f"daily_basic_{year}.parquet"
    if out_file.exists():
        print(f"[跳过] {out_file.name} 已存在")
        continue

    dates_this_year = [d for d in trade_dates if d.startswith(year)]
    print(f"\n[拉取] {year} 年，{len(dates_this_year)} 个交易日")

    rows = []
    for i, d in enumerate(dates_this_year):
        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                df = pro.daily_basic(trade_date=d, fields=FIELDS)
                if df is not None and len(df) > 0:
                    rows.append(df)
                    success = True
                break
            except Exception as e:
                if attempt < MAX_RETRIES:
                    delay = INITIAL_RETRY_DELAY * (2 ** (attempt - 1))  # 指数退避
                    print(
                        f"  [重试 {attempt}/{MAX_RETRIES}] {d} 失败：{e}，等待 {delay:.1f} 秒"
                    )
                    time.sleep(delay)
                else:
                    print(f"  [错误] {d} 重试 {MAX_RETRIES} 次仍失败，记录并跳过")
                    failed_dates.append(d)

        if not success:
            pass  # 已记录

        time.sleep(REQUEST_INTERVAL)  # 固定间隔，避免密集请求

        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(dates_this_year)}")

    if rows:
        year_df = pd.concat(rows, ignore_index=True)
        year_df.to_parquet(out_file, index=False)
        print(f"[保存] {out_file.name}：{len(year_df)} 行")
    else:
        print(f"[警告] {year} 年没有任何数据")

# ---------- 记录失败日期 ----------
if failed_dates:
    with open(FAILED_LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(failed_dates))
    print(f"\n[注意] 有 {len(failed_dates)} 个交易日拉取失败，已记录到 {FAILED_LOG}")
else:
    print("\n[完成] daily_basic 全部拉取完毕，无失败日期。")
