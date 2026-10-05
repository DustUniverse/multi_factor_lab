"""测试腾讯接口不同 count 参数，找到能返回完整 5 年数据的值。

用法：
    python scripts/test_tencent.py
"""

from __future__ import annotations

import time

import requests

SYMBOL = "000001"
START = "2019-09-30"
END = "2024-09-30"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://gu.qq.com/",
}

URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"


def fetch(count: int) -> None:
    print(f"\n--- count = {count} ---")
    params = {"param": f"sz{SYMBOL},day,{START},{END},{count},qfq"}
    t0 = time.time()
    try:
        resp = requests.get(URL, params=params, headers=HEADERS, timeout=20)
        elapsed = time.time() - t0
        data = resp.json()
        node = data.get("data", {}).get(f"sz{SYMBOL}", {})
        rows = node.get("qfqday") or node.get("day") or []
        print(
            f"状态码：{resp.status_code}    耗时：{elapsed:.2f}s    行数：{len(rows)}"
        )
        if rows:
            print(f"第一行：{rows[0]}")
            print(f"最后一行：{rows[-1]}")
            first_date = rows[0][0]
            last_date = rows[-1][0]
            print(f"日期范围：{first_date} ~ {last_date}")
            if first_date <= START:
                print("✅ 覆盖了 2019-09-30")
            else:
                print(f"⚠️ 起始日期晚了，实际从 {first_date} 开始")
        else:
            print(f"❌ 无数据，原始 keys = {list(node.keys())}")
    except Exception as e:
        print(f"❌ 异常：{type(e).__name__}: {e}")


def main() -> None:
    print(f"测试股票：{SYMBOL}    目标范围：{START} ~ {END}")
    for count in [640, 1000, 2000, 3000, 5000]:
        fetch(count)
        time.sleep(1)
    print("\n测试完成，请把完整输出贴回。")


if __name__ == "__main__":
    main()
