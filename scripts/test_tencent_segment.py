"""测试腾讯接口的 start/end 参数是否生效（决定能否分段抓取完整 5 年）。

用法：
    python scripts/test_tencent_segment.py
"""

from __future__ import annotations

import time

import requests

SYMBOL = "000001"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://gu.qq.com/",
}

URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"


def fetch(start: str, end: str, count: int = 640) -> list:
    params = {"param": f"sz{SYMBOL},day,{start},{end},{count},qfq"}
    resp = requests.get(URL, params=params, headers=HEADERS, timeout=20)
    data = resp.json()
    node = data.get("data", {}).get(f"sz{SYMBOL}", {})
    return node.get("qfqday") or node.get("day") or []


def main() -> None:
    print(f"测试股票：{SYMBOL}")
    print(
        "目的：验证 start/end 是否生效。若生效，每段起始日期应接近我们指定的 start。\n"
    )

    segments = [
        ("2019-09-30", "2021-09-30"),
        ("2021-09-30", "2023-09-30"),
        ("2023-09-30", "2024-09-30"),
    ]
    for start, end in segments:
        rows = fetch(start, end)
        if rows:
            print(
                f"请求 {start} ~ {end}  ->  {len(rows)} 行，"
                f"实际 {rows[0][0]} ~ {rows[-1][0]}"
            )
        else:
            print(f"请求 {start} ~ {end}  ->  空返回")
        time.sleep(0.8)

    print("\n如果每段实际起始日期 ≈ 我们请求的 start，说明 start/end 生效，分段可行。")
    print("如果三段都返回同样的 2022-02-15 ~ 2024-09-30，说明 start 被忽略。")


if __name__ == "__main__":
    main()
