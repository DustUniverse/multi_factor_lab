"""获取沪深 A 股股票列表并保存为 parquet。

数据源：AKShare
- 正常上市：stock_info_a_code_name
- 上交所退市：stock_info_sh_delist(symbol="全部")
- 深交所退市：stock_info_sz_delist(symbol="终止上市公司")
- ST 标记：名称包含 "ST" 兜底

保存包含上市状态，避免幸存者偏差。
"""

import sys
import time
from pathlib import Path

import akshare as ak
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mfalpha.common.constants import DATA_DIR  # noqa: E402


def fetch_normal_stocks() -> pd.DataFrame:
    """获取当前正常上市的沪深京 A 股列表。"""
    df = ak.stock_info_a_code_name()
    df = df.rename(columns={"code": "symbol", "name": "name"})
    df["list_status"] = "L"
    return df


def fetch_delisted_sh() -> pd.DataFrame:
    """获取上交所退市股票。列名：公司代码, 公司简称。"""
    for i in range(3):
        try:
            sh_delist = ak.stock_info_sh_delist(symbol="全部")
            sh_delist = sh_delist.rename(
                columns={"公司代码": "symbol", "公司简称": "name"}
            )
            sh_delist["list_status"] = "D"
            print(f"  上交所退市: {len(sh_delist)} 只")
            return sh_delist[["symbol", "name", "list_status"]]
        except Exception as e:
            print(f"  上交所退市第 {i+1} 次失败: {e}")
            time.sleep(2)

    print("  上交所退市获取失败，跳过")
    return pd.DataFrame(columns=["symbol", "name", "list_status"])


def fetch_delisted_sz() -> pd.DataFrame:
    """获取深交所退市股票。列名：证券代码, 证券简称。"""
    for i in range(3):
        try:
            sz_delist = ak.stock_info_sz_delist(symbol="终止上市公司")
            sz_delist = sz_delist.rename(
                columns={"证券代码": "symbol", "证券简称": "name"}
            )
            sz_delist["list_status"] = "D"
            print(f"  深交所退市: {len(sz_delist)} 只")
            return sz_delist[["symbol", "name", "list_status"]]
        except Exception as e:
            print(f"  深交所退市第 {i+1} 次失败: {e}")
            time.sleep(2)

    print("  深交所退市获取失败，跳过")
    return pd.DataFrame(columns=["symbol", "name", "list_status"])


def main() -> None:
    print("正在获取正常上市股票...")
    normal = fetch_normal_stocks()
    print(f"  正常上市: {len(normal)} 只")

    print("正在获取上交所退市股票...")
    delisted_sh = fetch_delisted_sh()

    print("正在获取深交所退市股票...")
    delisted_sz = fetch_delisted_sz()

    df = pd.concat([normal, delisted_sh, delisted_sz], ignore_index=True)

    # 统一 symbol 为字符串
    df["symbol"] = df["symbol"].astype(str)

    # ST 标记：名称包含 "ST"
    df["is_st"] = df["name"].str.contains("ST", na=False)

    # 去重
    df = df.drop_duplicates(subset=["symbol"], keep="first")

    print(f"\n合并后总股票数: {len(df)}")
    print(f"  其中正常上市(L): {(df['list_status'] == 'L').sum()} 只")
    print(f"  其中退市(D):     {(df['list_status'] == 'D').sum()} 只")
    print(f"  其中 ST/*ST:    {df['is_st'].sum()} 只")
    print("\n前 5 行预览：")
    print(df.head())

    out_path = DATA_DIR / "stock_list.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"\n已保存到: {out_path}")


if __name__ == "__main__":
    main()
