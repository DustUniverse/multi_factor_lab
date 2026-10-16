"""
M7-b: 用 Backtrader 复现 ic_no_vol 策略，与自研引擎对账。

关键修复：
1. symbol 统一为 6 位字符串（panel '000001' vs holdings 2088 → '002088'）
2. 每只票 reindex 到完整交易日历（1213 天），让主时钟 = 完整日历
   → 解决 next_open 只在所有 data 就绪后才触发的问题
3. 自研净值由 net_ret cumprod 生成

对账目标：与自研引擎净值相关系数 > 0.95，年化差 < 2%
"""

import os

import backtrader as bt
import numpy as np
import pandas as pd

# ---------- 路径 ----------
ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

HOLDINGS_FILE = os.path.join(PROC, "composite_holdings_ic_no_vol.csv")
PRICE_FILE = os.path.join(PROC, "daily_panel_tencent_clean.parquet")
BENCH_FILE = os.path.join(PROC, "hs300_benchmark.parquet")
SELF_FILE = os.path.join(PROC, "composite_bt_ic_no_vol.csv")
OUT_FILE = os.path.join(PROC, "bt_vs_self_ic_no_vol.csv")

# ---------- 参数 ----------
COMMISSION = 0.004
INIT_CASH = 1e8
BUFFER_RATIO = 1.0


# ============================================================
# 策略
# ============================================================
class MultiFactorStrategy(bt.Strategy):
    params = (
        ("holdings_by_date", None),
        ("calendar_name", "CALENDAR"),
    )

    def __init__(self):
        self.holdings_by_date = self.p.holdings_by_date
        self.rebalance_dates = set(self.holdings_by_date.keys())
        self.n_next_open = 0
        self.n_match = 0
        self.n_order = 0
        self.n_filled = 0
        self.n_nan_open = 0

    def notify_order(self, order):
        if order.status == order.Completed:
            self.n_filled += 1

    def next_open(self):
        self.n_next_open += 1
        cur_date = self.datas[0].datetime.date(0)

        if cur_date not in self.rebalance_dates:
            return

        self.n_match += 1
        target_symbols = list(self.holdings_by_date[cur_date])
        print(f"  [dbg] match {cur_date}  target_n={len(target_symbols)}")
        target_set = set(target_symbols)

        # 1. 卖出不在目标列表中的持仓
        for data in self.datas:
            if data._name == self.p.calendar_name:
                continue
            pos = self.getposition(data).size
            if pos > 0 and data._name not in target_set:
                self.order_target_percent(data=data, target=0.0)
                self.n_order += 1

        # 2. 买入 / 调整目标持仓
        n_target = len(target_symbols)
        if n_target == 0:
            return
        target_weight = BUFFER_RATIO / n_target

        for sym in target_symbols:
            try:
                data = self.getdatabyname(sym)
            except KeyError:
                continue
            if len(data) < 1:
                continue

            # ---- 安全取 open，每一步都可能失败，失败就 continue ----
            try:
                op = data.open[0]
            except (IndexError, KeyError):
                self.n_nan_open += 1
                continue
            if op is None:
                self.n_nan_open += 1
                continue
            try:
                op_f = float(op)
            except (TypeError, ValueError):
                self.n_nan_open += 1
                continue
            if np.isnan(op_f) or op_f <= 0:
                self.n_nan_open += 1
                continue
            # ----------------------------------------------------

            self.order_target_percent(data=data, target=target_weight)
            self.n_order += 1

    def stop(self):
        print(f"\n  [debug] next_open 调用次数: {self.n_next_open}")
        print(f"  [debug] 日期匹配次数:     {self.n_match}")
        print(f"  [debug] 下单数:           {self.n_order}")
        print(f"  [debug] 成交数:           {self.n_filled}")
        print(f"  [debug] NaN open 跳过数:  {self.n_nan_open}")


# ============================================================
# 主流程
# ============================================================
def main():
    print("[M7-b] Backtrader 复现 ic_no_vol ...")

    # ---------- 读持仓 ----------
    holdings = pd.read_csv(HOLDINGS_FILE, parse_dates=["trade_date", "signal_date"])
    # !!! 关键修复：int 2088 → '002088'
    holdings["symbol"] = holdings["symbol"].astype(str).str.zfill(6)

    holdings_by_date = (
        holdings.groupby(holdings["trade_date"].dt.date)["symbol"].apply(list).to_dict()
    )
    n_periods = len(holdings_by_date)
    n_stocks = sum(len(v) for v in holdings_by_date.values())
    unique_symbols = sorted(set(holdings["symbol"].unique()))
    print(f"  持仓期数: {n_periods}，股票数: {n_stocks}")
    print(f"  唯一股票数: {len(unique_symbols)}")
    print(f"  symbol 样例: {unique_symbols[:5]}")

    # ---------- 读价格 ----------
    print("  加载价格数据 ...")
    panel = pd.read_parquet(PRICE_FILE)
    if "date" in panel.columns and "trade_date" not in panel.columns:
        panel = panel.rename(columns={"date": "trade_date"})
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    panel["symbol"] = panel["symbol"].astype(str).str.zfill(6)

    unique_set = set(unique_symbols)
    panel = panel[panel["symbol"].isin(unique_set)].copy()
    print(f"  过滤后价格行数: {len(panel):,}")

    print("  按 symbol 分组 ...")
    panel_groups = {sym: g for sym, g in panel.groupby("symbol", sort=False)}
    print(f"  分组完成: {len(panel_groups)} 只")

    # ---------- 读基准（构造日历） ----------
    bench = pd.read_parquet(BENCH_FILE)
    if "date" in bench.columns and "trade_date" not in bench.columns:
        bench = bench.rename(columns={"date": "trade_date"})
    bench["trade_date"] = pd.to_datetime(bench["trade_date"])
    all_dates = np.sort(bench["trade_date"].unique())
    full_idx = pd.DatetimeIndex(all_dates)
    print(f"  交易日历长度: {len(all_dates)}")

    # ---------- Cerebro ----------
    cerebro = bt.Cerebro(cheat_on_open=True)
    cerebro.broker.setcash(INIT_CASH)
    cerebro.broker.setcommission(commission=COMMISSION)

    # 1) 日历 feed 作为主时钟
    cal_df = pd.DataFrame(
        {
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 0,
            "openinterest": 0,
        },
        index=full_idx,
    )
    cerebro.adddata(bt.feeds.PandasData(dataname=cal_df), name="CALENDAR")

    # 2) 股票 feeds（reindex 到全日历，让主时钟 = 完整日历）
    n_added = 0
    n_missing = 0
    need = {"open", "high", "low", "close", "volume"}
    for sym in unique_symbols:
        sub = panel_groups.get(sym)
        if sub is None or sub.empty:
            n_missing += 1
            continue
        if not need.issubset(sub.columns):
            n_missing += 1
            continue
        sub = sub.sort_values("trade_date").set_index("trade_date")
        feed_df = sub[["open", "high", "low", "close", "volume"]].astype(float)
        # reindex 到完整日历，再 ffill/bfill，让每根 bar 都有价格
        # - 上市前：用第一个有效价格 bfill（仅是让 BT 不崩，不会实际下单，因持仓表里无未上市票）
        # - 停牌/退市后：用最后价格 ffill（与真实停牌逻辑一致）
        feed_df = feed_df.reindex(full_idx).ffill().bfill()
        cerebro.adddata(bt.feeds.PandasData(dataname=feed_df), name=sym)
        n_added += 1
    print(f"  股票 feeds: {n_added}（缺数据 {n_missing}）")

    # ---------- 策略 ----------
    cerebro.addstrategy(
        MultiFactorStrategy,
        holdings_by_date=holdings_by_date,
        calendar_name="CALENDAR",
    )
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="timereturn")

    # ---------- 运行 ----------
    print("  开始回测 ...")
    strat = cerebro.run()[0]
    print(f"  终值: {cerebro.broker.getvalue():.2f}")

    # ---------- 提取日净值 ----------
    tr = strat.analyzers.timereturn.get_analysis()
    dates = sorted(tr.keys())
    rets = np.array([tr[d] for d in dates])
    nav = np.cumprod(1.0 + rets)
    bt_nav = pd.DataFrame({"trade_date": pd.to_datetime(dates), "nav_bt": nav})
    print(f"  Backtrader 日净值: {len(bt_nav)} 天，终值 {nav[-1]:.4f}")

    # ---------- 与自研对账 ----------
    self_df = (
        pd.read_csv(
            SELF_FILE,
            parse_dates=["signal_date", "trade_date", "next_trade_date"],
        )
        .sort_values("trade_date")
        .reset_index(drop=True)
    )
    self_df["nav_self"] = (1.0 + self_df["net_ret"]).cumprod()
    self_df["align_date"] = pd.to_datetime(self_df["next_trade_date"])

    merged = pd.merge(
        bt_nav,
        self_df[["align_date", "nav_self"]],
        left_on="trade_date",
        right_on="align_date",
        how="inner",
    )

    if len(merged) == 0:
        print("  [warn] 净值序列无法对齐，跳过对账")
        return

    corr = merged["nav_bt"].corr(merged["nav_self"])
    n = len(merged)
    span_days = (merged["trade_date"].iloc[-1] - merged["trade_date"].iloc[0]).days
    years = max(span_days / 365.25, 1e-6)
    bt_ann = merged["nav_bt"].iloc[-1] ** (1 / years) - 1
    self_ann = merged["nav_self"].iloc[-1] ** (1 / years) - 1

    print("\n  === 对账 ===")
    print(f"  有效期数:      {n}")
    print(f"  净值相关系数:  {corr:.4f}")
    print(f"  自研年化:      {self_ann:+.2%}  终值 {merged['nav_self'].iloc[-1]:.4f}")
    print(f"  BT  年化:      {bt_ann:+.2%}  终值 {merged['nav_bt'].iloc[-1]:.4f}")
    print(f"  年化收益差:    {bt_ann - self_ann:+.2%}")

    merged.to_csv(OUT_FILE, index=False)
    print(f"\n  对账表保存: {OUT_FILE}")


if __name__ == "__main__":
    main()
