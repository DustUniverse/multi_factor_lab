"""抽查缺失股票的真实最早 K 线日期，判断是否为新上市股。

用法：
    python scripts/verify_missing.py
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
MISSING_PATH = ROOT / "data" / "raw" / "missing_symbols.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://gu.qq.com/",
}
URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"


def code_of(symbol: str) -> str:
    return f"sh{symbol}" if symbol.startswith("6") else f"sz{symbol}"


def earliest_date(symbol: str) -> str:
    """请求极早起点，看返回的第一行日期。"""
    code = code_of(symbol)
    # 从 2000-01-01 开始请求，腾讯会返回它有的最早期数据
    params = {"param": f"{code},day,2000-01-01,2024-09-30,640,qfq"}
    try:
        resp = requests.get(URL, params=params, headers=HEADERS, timeout=20)
        data = resp.json()
        node = (data.get("data") or {}).get(code) or {}
        rows = node.get("qfqday") or node.get("day") or []
        if rows:
            return f"{rows[0][0]}  （共 {len(rows)} 行）"
        return "无任何 K 线数据"
    except Exception as e:
        return f"请求异常：{type(e).__name__}: {e}"


def main() -> None:
    lines = MISSING_PATH.read_text(encoding="utf-8").splitlines()
    symbols = [s.strip() for s in lines if s.strip()]
    print(f"缺失共 {len(symbols)} 只，抽查前 10 只：\n")

    for s in symbols[:10]:
        d = earliest_date(s)
        print(f"  {s}  最早 K 线：{d}")
        time.sleep(0.6)

    print("\n判断：若最早日期都 >= 2024-10-01，说明是范围内没有数据的新股，可放弃。")


if __name__ == "__main__":
    main()
