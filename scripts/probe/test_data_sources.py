"""数据源探路脚本：对比新浪 / 腾讯 / 东财三个日线接口的可用性。

用法：
    python scripts/test_data_sources.py

只抓 1 只股票（000001 平安银行），打印每个源的成功/失败、耗时、行数、前几行。
"""

from __future__ import annotations

import time
from datetime import datetime

import requests

# 统一用平安银行测试，时间范围与项目一致
SYMBOL = "000001"
START = "2019-09-30"
END = "2024-09-30"

# 模拟浏览器，避免最基础的 403
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


def test_sina() -> None:
    """新浪接口：https://finance.sina.com.cn/realstock/company/{symbol}/hisdata/klc_kl.js"""
    print("\n" + "=" * 60)
    print("【1】新浪财经")
    print("=" * 60)
    url = (
        "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        f"CN_MarketData.getKLineData?symbol=sz{SYMBOL}&scale=240&ma=no&datalen=2000"
    )
    headers = {**HEADERS, "Referer": "https://finance.sina.com.cn/"}
    t0 = time.time()
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        elapsed = time.time() - t0
        print(f"状态码：{resp.status_code}    耗时：{elapsed:.2f}s")
        print(f"响应前 200 字符：{resp.text[:200]}")
        if resp.status_code == 200 and resp.text.strip():
            print("✅ 新浪：有返回")
        else:
            print("❌ 新浪：空返回或状态码异常")
    except Exception as e:
        print(f"❌ 新浪：请求异常 -> {type(e).__name__}: {e}")


def test_tencent() -> None:
    """腾讯接口：https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"""
    print("\n" + "=" * 60)
    print("【2】腾讯财经")
    print("=" * 60)
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "param": f"sz{SYMBOL},day,{START},{END},640,qfq",
    }
    headers = {**HEADERS, "Referer": "https://gu.qq.com/"}
    t0 = time.time()
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        elapsed = time.time() - t0
        print(f"状态码：{resp.status_code}    耗时：{elapsed:.2f}s")
        data = resp.json()
        # 腾讯返回结构：data -> sz000001 -> qfqday 或 day
        node = data.get("data", {}).get(f"sz{SYMBOL}", {})
        rows = node.get("qfqday") or node.get("day") or []
        print(f"解析到 K 线行数：{len(rows)}")
        if rows:
            print(f"第一行：{rows[0]}")
            print(f"最后一行：{rows[-1]}")
            print("✅ 腾讯：有返回")
        else:
            print(f"❌ 腾讯：无 K 线数据，原始 keys = {list(node.keys())}")
    except Exception as e:
        print(f"❌ 腾讯：请求异常 -> {type(e).__name__}: {e}")


def test_eastmoney() -> None:
    """东财接口（当前脚本用的就是它）：push2his.eastmoney.com"""
    print("\n" + "=" * 60)
    print("【3】东方财富")
    print("=" * 60)
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": f"0.{SYMBOL}",  # 0=深市, 1=沪市
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",  # 日线
        "fqt": "1",  # 前复权
        "beg": START.replace("-", ""),
        "end": END.replace("-", ""),
    }
    headers = {**HEADERS, "Referer": "https://quote.eastmoney.com/"}
    t0 = time.time()
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        elapsed = time.time() - t0
        print(f"状态码：{resp.status_code}    耗时：{elapsed:.2f}s")
        data = resp.json()
        klines = (data.get("data") or {}).get("klines") or []
        print(f"解析到 K 线行数：{len(klines)}")
        if klines:
            print(f"第一行：{klines[0]}")
            print(f"最后一行：{klines[-1]}")
            print("✅ 东财：有返回")
        else:
            print(f"❌ 东财：无 K 线数据，原始 data = {data.get('data')}")
    except Exception as e:
        print(f"❌ 东财：请求异常 -> {type(e).__name__}: {e}")


def main() -> None:
    print(f"测试股票：{SYMBOL}    时间范围：{START} ~ {END}")
    print(f"当前时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
    test_sina()
    time.sleep(1)  # 三个源之间稍微隔一下
    test_tencent()
    time.sleep(1)
    test_eastmoney()
    print("\n" + "=" * 60)
    print("探路完成。请把以上完整输出贴回对话。")
    print("=" * 60)


if __name__ == "__main__":
    main()
