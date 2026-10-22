"""M7-c: Backtrader 对账 v2 —— open-to-open 口径 + 手动成本。

修复：v1 用 TimeReturn（close-to-close），与自研 open-to-open 错位。
v2 记录每个调仓日 open 时（调仓前）的组合价值，用该序列算区间收益；
broker 零成本，成本按自研口径 turnover*2*0.4% 手动扣。
"""

import os

import backtrader as bt
import numpy as np
import pandas as pd

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

HOLDINGS_FILE = os.path.join(PROC, "composite_holdings_lasso_horizon_all8.csv")
PRICE_FILE = os.path.join(PROC, "daily_panel_tencent_clean.parquet")
BENCH_FILE = os.path.join(PROC, "hs300_benchmark.parquet")
SELF_FILE = os.path.join(PROC, "composite_bt_lasso_horizon_all8.csv")
OUT_FILE = os.path.join(PROC, "bt_vs_self_lasso_horizon_all8_v2.csv")

INIT_CASH = 1e8
BUFFER_RATIO = 1.0
COST_PER_SIDE = 0.003
SLIPPAGE_PER_SIDE = 0.001


class MultiFactorStrategy(bt.Strategy):
    params = (
        ("holdings_by_date", None),
        ("calendar_name", "CALENDAR"),
    )

    def __init__(self):
        self.holdings_by_date = self.p.holdings_by_date
        self.rebalance_dates = set(self.holdings_by_date.keys())
        self.period_values = []  # (date, value_before_rebalance)
        self.period_turnovers = []  # (date, turnover)
        self.prev_set = set()
        self.cash_ratios = []
        self.n_order = 0
        self.n_filled = 0

    def notify_order(self, order):
        if order.status == order.Completed:
            self.n_filled += 1

    def _value_at_open(self):
        v = self.broker.getcash()
        for data in self.datas:
            if data._name == self.p.calendar_name:
                continue
            pos = self.getposition(data)
            if pos.size != 0:
                try:
                    op = float(data.open[0])
                    if not np.isnan(op) and op > 0:
                        v += pos.size * op
                except (IndexError, KeyError, TypeError, ValueError):
                    pass
        return v

    def next_open(self):
        cur_date = self.datas[0].datetime.date(0)
        if cur_date not in self.rebalance_dates:
            return

        # 用今日 open 估值调仓前组合总价值（现金 + 持仓市值）
        value_open = self._value_at_open()
        self.period_values.append((cur_date, value_open))

        target_symbols = list(self.holdings_by_date[cur_date])
        target_set = set(target_symbols)

        cur_set = set(target_symbols)
        if self.prev_set:
            turnover = len(cur_set - self.prev_set) / len(cur_set)
        else:
            turnover = 1.0
        self.period_turnovers.append((cur_date, turnover))
        self.prev_set = cur_set

        # 先清仓不在目标集合的股票
        for data in self.datas:
            if data._name == self.p.calendar_name:
                continue
            pos = self.getposition(data).size
            if pos > 0 and data._name not in target_set:
                self.order_target_size(data=data, target=0)
                self.n_order += 1

        n_target = len(target_symbols)
        if n_target == 0:
            return

        # 每只目标金额 = 今日 open 估值的总价值 / n_target
        target_value_per = value_open * BUFFER_RATIO / n_target

        for sym in target_symbols:
            try:
                data = self.getdatabyname(sym)
            except KeyError:
                continue
            if len(data) < 1:
                continue
            try:
                op = float(data.open[0])
            except (IndexError, KeyError, TypeError, ValueError):
                continue
            if np.isnan(op) or op <= 0:
                continue
            # 整手取整（A 股 100 股一手）
            target_shares = int(target_value_per / op / 100) * 100
            self.order_target_size(data=data, target=target_shares)
            self.n_order += 1

    def stop(self):
        print(f"  [debug] 下单数 {self.n_order} / 成交数 {self.n_filled}")
        print(f"  [debug] 记录期数 {len(self.period_values)}")
        if self.cash_ratios:
            print(
                f"  [debug] 调仓后现金比例 均值 {np.mean(self.cash_ratios):.4f} / "
                f"最小 {np.min(self.cash_ratios):.4f} / 最大 {np.max(self.cash_ratios):.4f}"
            )


def main():
    print("[M7-c] Backtrader 对账 v2（open-to-open + 手动成本）...")

    holdings = pd.read_csv(HOLDINGS_FILE, parse_dates=["trade_date", "signal_date"])
    holdings["symbol"] = holdings["symbol"].astype(str).str.zfill(6)
    holdings_by_date = (
        holdings.groupby(holdings["trade_date"].dt.date)["symbol"].apply(list).to_dict()
    )
    unique_symbols = sorted(set(holdings["symbol"].unique()))
    print(f"  持仓期数: {len(holdings_by_date)}，唯一股票: {len(unique_symbols)}")

    panel = pd.read_parquet(PRICE_FILE)
    if "date" in panel.columns and "trade_date" not in panel.columns:
        panel = panel.rename(columns={"date": "trade_date"})
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    panel["symbol"] = panel["symbol"].astype(str).str.zfill(6)
    panel = panel[panel["symbol"].isin(set(unique_symbols))].copy()
    panel_groups = {sym: g for sym, g in panel.groupby("symbol", sort=False)}

    bench = pd.read_parquet(BENCH_FILE)
    if "date" in bench.columns and "trade_date" not in bench.columns:
        bench = bench.rename(columns={"date": "trade_date"})
    bench["trade_date"] = pd.to_datetime(bench["trade_date"])
    full_idx = pd.DatetimeIndex(np.sort(bench["trade_date"].unique()))
    print(f"  交易日历长度: {len(full_idx)}")

    cerebro = bt.Cerebro(cheat_on_open=True)
    cerebro.broker.setcash(INIT_CASH)
    cerebro.broker.setcommission(commission=0.0)  # 零成本，手动扣

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

    need = {"open", "high", "low", "close", "volume"}
    n_added = 0
    for sym in unique_symbols:
        sub = panel_groups.get(sym)
        if sub is None or sub.empty or not need.issubset(sub.columns):
            continue
        sub = sub.sort_values("trade_date").set_index("trade_date")
        feed_df = sub[["open", "high", "low", "close", "volume"]].astype(float)
        feed_df = feed_df.reindex(full_idx).ffill().bfill()
        cerebro.adddata(bt.feeds.PandasData(dataname=feed_df), name=sym)
        n_added += 1
    print(f"  股票 feeds: {n_added}")

    cerebro.addstrategy(
        MultiFactorStrategy,
        holdings_by_date=holdings_by_date,
        calendar_name="CALENDAR",
    )
    strat = cerebro.run()[0]

    pv = pd.DataFrame(strat.period_values, columns=["trade_date", "value"]).set_index(
        "trade_date"
    )
    turn = pd.DataFrame(
        strat.period_turnovers, columns=["trade_date", "turnover"]
    ).set_index("trade_date")
    pv = pv.join(turn)
    pv["gross_ret_bt"] = pv["value"].pct_change()
    pv["cost"] = pv["turnover"] * 2.0 * (COST_PER_SIDE + SLIPPAGE_PER_SIDE)
    pv["net_ret_bt"] = pv["gross_ret_bt"] - pv["cost"]
    pv = pv.dropna(subset=["gross_ret_bt"]).reset_index()
    pv["trade_date"] = pd.to_datetime(pv["trade_date"])
    pv = pv.rename(columns={"turnover": "turnover_bt"})

    self_df = (
        pd.read_csv(
            SELF_FILE, parse_dates=["signal_date", "trade_date", "next_trade_date"]
        )
        .sort_values("trade_date")
        .reset_index(drop=True)
    )
    self_df["align_date"] = pd.to_datetime(self_df["next_trade_date"])

    merged = pd.merge(
        self_df[["align_date", "gross_ret", "net_ret", "turnover"]],
        pv[["trade_date", "gross_ret_bt", "net_ret_bt", "turnover_bt"]],
        left_on="align_date",
        right_on="trade_date",
        how="inner",
    )
    merged["gross_diff"] = merged["gross_ret"] - merged["gross_ret_bt"]
    merged["net_diff"] = merged["net_ret"] - merged["net_ret_bt"]

    n = len(merged)
    span = (merged["trade_date"].iloc[-1] - merged["trade_date"].iloc[0]).days
    years = max(span / 365.25, 1e-6)

    def ann(nav):
        return nav ** (1 / years) - 1

    nav_sg = (1 + merged["gross_ret"]).cumprod().iloc[-1]
    nav_bg = (1 + merged["gross_ret_bt"]).cumprod().iloc[-1]
    nav_sn = (1 + merged["net_ret"]).cumprod().iloc[-1]
    nav_bn = (1 + merged["net_ret_bt"]).cumprod().iloc[-1]

    print("\n  === 对账 v2 ===")
    print(f"  有效期数:       {n}")
    print(
        f"  gross 累计:     自研 {nav_sg:.4f} / BT {nav_bg:.4f} "
        f"/ 差 {nav_bg - nav_sg:+.4f}"
    )
    print(
        f"  net   累计:     自研 {nav_sn:.4f} / BT {nav_bn:.4f} "
        f"/ 差 {nav_bn - nav_sn:+.4f}"
    )
    print(
        f"  gross 年化:     自研 {ann(nav_sg):+.2%} / BT {ann(nav_bg):+.2%} "
        f"/ 差 {ann(nav_bg) - ann(nav_sg):+.2%}"
    )
    print(
        f"  net   年化:     自研 {ann(nav_sn):+.2%} / BT {ann(nav_bn):+.2%} "
        f"/ 差 {ann(nav_bn) - ann(nav_sn):+.2%}"
    )
    print(
        f"  gross 单期差:   平均 {merged['gross_diff'].mean():+.4%} "
        f"/ 标准差 {merged['gross_diff'].std():.4%}"
    )
    print(
        f"  net   单期差:   平均 {merged['net_diff'].mean():+.4%} "
        f"/ 标准差 {merged['net_diff'].std():.4%}"
    )
    nav_self_n = (1 + merged["net_ret"]).cumprod()
    nav_bt_n = (1 + merged["net_ret_bt"]).cumprod()
    print(f"  net 净值相关系数: {nav_self_n.corr(nav_bt_n):.4f}")
    print(
        f"  turnover:       自研 {merged['turnover'].mean():.4f} "
        f"/ BT {merged['turnover_bt'].mean():.4f}"
    )

    merged.to_csv(OUT_FILE, index=False)
    print(f"\n  对账表保存: {OUT_FILE}")


if __name__ == "__main__":
    main()
