"""M5a: 自研事件驱动回测引擎（核心函数库）。

设计原则：
    - 严格无未来函数：
        signal_date T 日盘后生成信号（因子值 T 日可见）
        trade_date T+1 开盘成交
        IC 窗口右端点 ≤ signal_date
    - 涨跌停过滤：调仓日 is_limit_up=True 或 is_suspended=True 的标的跳过
    - 交易成本：单边 0.3% 手续费 + 0.1% 滑点 = 0.4%
        一次完整换手（卖旧 + 买新）成本 = 0.8%
    - 等权持仓 top_n 只

用法：由 run_*.py 调用，不直接运行本文件。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# 交易成本（按带教验收口径的字面理解）
COST_PER_SIDE = 0.003  # 手续费单边 0.3%
SLIPPAGE_PER_SIDE = 0.001  # 滑点单边 0.1%


def run_backtest(
    scores: pd.DataFrame,
    calendar: pd.DataFrame,
    prices: pd.DataFrame,
    top_n: int = 480,
    buffer_n: int = 0,
    cost_per_side: float = COST_PER_SIDE,
    slippage_per_side: float = SLIPPAGE_PER_SIDE,
    position_series: pd.Series | None = None,
) -> dict:
    """事件驱动回测。

    参数
    ----
    scores : pd.DataFrame
        index=signal_date, columns=symbol, values=score（越大越好）
    calendar : pd.DataFrame
        两列 signal_date, trade_date（datetime）
    prices : pd.DataFrame
        列含 symbol, date, open, is_limit_up, is_suspended
    top_n : int
        每期持仓数
    position_series : pd.Series | None
        期初目标仓位序列。index=trade_date（datetime），value∈[0,1]。
        None=满仓（基线，向后兼容）；缺失期沿用上一期，首期之前缺失默认 1.0。

    返回
    ----
    dict:
        periods : pd.DataFrame
            每期一行，列含 signal_date/trade_date/next_trade_date/
            gross_ret/turnover/cost/net_ret/n_holding/pos
        nav : pd.Series
            期频净值（index=trade_date）
        holdings : dict[trade_date -> list[symbol]]
    """
    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"])
    prices_by_date = {d: g.set_index("symbol") for d, g in prices.groupby("date")}

    # ---- 新增：期初仓位序列预处理 ----
    if position_series is not None:
        if not isinstance(position_series, pd.Series):
            position_series = pd.Series(position_series)
        position_series = position_series.copy()
        position_series.index = pd.to_datetime(position_series.index)
        position_series = position_series.reindex(
            pd.to_datetime(calendar["trade_date"])
        )
        # 缺失沿用上一期；首期之前缺失默认满仓 1.0
        position_series = position_series.ffill().fillna(1.0)

    records = []
    holdings = {}
    prev_holdings: set[str] = set()
    prev_pos: float | None = None  # 新增：上一实际执行期的仓位；None=尚未执行过

    n_periods = len(calendar)
    for i in range(n_periods - 1):  # 最后一期没有下一期可卖
        row = calendar.iloc[i]
        next_row = calendar.iloc[i + 1]
        sig = row["signal_date"]
        trade = row["trade_date"]
        next_trade = next_row["trade_date"]

        if sig not in scores.index:
            continue
        score_t = scores.loc[sig].dropna()
        if len(score_t) < top_n:
            continue

        # 候选池：top_n + buffer_n 的 2 倍冗余
        pool_size = top_n + buffer_n
        candidates = score_t.nlargest(pool_size * 2).index.tolist()

        trade_prices = prices_by_date.get(trade)
        if trade_prices is None:
            continue

        # 过滤：涨停/停牌/无数据
        valid_pool = []
        for s in candidates:
            if s not in trade_prices.index:
                continue
            p = trade_prices.loc[s]
            if p.get("is_limit_up", False) or p.get("is_suspended", False):
                continue
            valid_pool.append(s)

        # 持仓缓冲：旧持仓里仍在前 pool_size 的优先保留
        pool_top = valid_pool[:pool_size]
        kept = [s for s in pool_top if s in prev_holdings]
        fill = [s for s in valid_pool if s not in prev_holdings]
        valid = (kept + fill)[:top_n]

        if len(valid) < top_n // 2:
            continue

        open_t = trade_prices.loc[valid, "open"]

        next_prices = prices_by_date.get(next_trade)
        if next_prices is None:
            continue
        open_next = next_prices.reindex(valid)["open"]

        # 停牌/缺价股：用该股在 next_trade 之前最后一个可用 open 填充
        missing = open_next[open_next.isna()].index
        if len(missing) > 0:
            last_avail = (
                prices[prices["symbol"].isin(missing) & (prices["date"] <= next_trade)]
                .sort_values("date")
                .groupby("symbol")["open"]
                .last()
            )
            open_next = open_next.fillna(last_avail)

        # 单只股票期间收益（满仓等权口径）
        rets = (open_next / open_t - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
        if len(rets) == 0:
            continue
        gross = float(rets.mean())

        # ---- 新增：期初目标仓位 ----
        if position_series is not None:
            pos = float(position_series.get(trade, 1.0))
            pos = float(np.clip(pos, 0.0, 1.0))
        else:
            pos = 1.0

        # 换手：新买入的占比（对称地卖出）
        cur_set = set(valid)
        turnover = len(cur_set - prev_holdings) / len(cur_set) if cur_set else 0.0

        # ---- 修改：成本拆成「股票换手」+「仓位调整」 ----
        # 股票换手成本按 pos 缩放：只有 pos 部分资金在股票里换手
        stock_cost = turnover * 2.0 * (cost_per_side + slippage_per_side) * pos
        # 仓位调整成本：单边；首期（prev_pos is None）不收费，避免与首期 turnover×2 重复
        if prev_pos is None:
            pos_cost = 0.0
        else:
            pos_cost = abs(pos - prev_pos) * (cost_per_side + slippage_per_side)
        cost = stock_cost + pos_cost

        # 组合净收益 = 股票部分收益（pos 缩放） - 总成本
        net = pos * gross - cost

        records.append(
            {
                "signal_date": sig,
                "trade_date": trade,
                "next_trade_date": next_trade,
                "gross_ret": gross,
                "turnover": turnover,
                "cost": cost,
                "net_ret": net,
                "n_holding": len(valid),
                "pos": pos,  # 新增列
            }
        )
        holdings[trade] = valid
        prev_holdings = cur_set
        prev_pos = pos  # 新增：更新上一实际仓位

    periods = pd.DataFrame(records)
    if periods.empty:
        return {"periods": periods, "nav": pd.Series(dtype=float), "holdings": holdings}

    periods = periods.sort_values("trade_date").reset_index(drop=True)
    nav = (1.0 + periods["net_ret"]).cumprod()
    nav.index = periods["trade_date"]
    nav.name = "nav"

    return {"periods": periods, "nav": nav, "holdings": holdings}


def nav_stats(nav: pd.Series, periods_per_year: float = 12.0) -> dict:
    """期频净值 → 年化/波动/Sharpe/最大回撤/胜率。"""
    if len(nav) < 2:
        return {}
    rets = nav.pct_change().dropna()
    n = len(rets)
    years = n / periods_per_year
    ann_ret = nav.iloc[-1] ** (1.0 / years) - 1.0
    ann_vol = rets.std() * np.sqrt(periods_per_year)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else np.nan
    running_max = nav.cummax()
    dd = nav / running_max - 1.0
    max_dd = dd.min()
    calmar = ann_ret / abs(max_dd) if max_dd < 0 else np.nan
    win = (rets > 0).mean()
    avg_win = rets[rets > 0].mean() if (rets > 0).any() else 0.0
    avg_loss = rets[rets < 0].mean() if (rets < 0).any() else 0.0
    pl_ratio = abs(avg_win / avg_loss) if avg_loss < 0 else np.nan
    return {
        "n_periods": n,
        "ann_return": ann_ret,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "win_rate": win,
        "pnl_ratio": pl_ratio,
    }
