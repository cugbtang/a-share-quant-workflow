"""示例策略：月度低波选股（合成数据可跑版）。

用合成日收益演示"低波动因子"回测框架，无需网络：
- 生成 N 只股票、T 天的日收益（部分股票人为低波动）。
- 每月末按过去 1 个月波动率排序，选最低的 K 只等权持有 1 个月。
- 输出 equity.csv 与 summary.json，含年化、夏普、最大回撤等组合指标。

真实接入：把 `generate_synthetic` 换成从 data.store 读取真实日线，
用 `adj_close` 计算收益率即可复用同一套组合逻辑。
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def generate_synthetic(n_stocks: int = 50, n_days: int = 756, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-01", periods=n_days)
    # 基础市场收益
    market = rng.normal(0.0003, 0.011, n_days)
    # 每只股票：不同的个体波动 + 与市场的 beta
    base_vol = rng.uniform(0.008, 0.025, n_stocks)
    beta = rng.uniform(0.6, 1.4, n_stocks)
    # 让前 10 只人为低波动（低波因子存在）
    base_vol[:10] = rng.uniform(0.006, 0.009, 10)
    cols = {}
    for i in range(n_stocks):
        noise = rng.normal(0, base_vol[i], n_days)
        cols[f"S{i:02d}"] = market * beta[i] + noise
    return pd.DataFrame(cols, index=dates)


def monthly_lowvol_portfolio(returns: pd.DataFrame, k: int = 10, lookback: int = 21) -> pd.DataFrame:
    """每月末按过去 lookback 日波动率选最低 k 只，等权持有到下月末。"""
    dates = returns.index
    # 组合日收益序列
    port_ret = pd.Series(0.0, index=dates)
    # 月末标记
    month_end = dates.to_series().dt.to_period("M").drop_duplicates().index
    for m_end in month_end:
        pos = dates.get_loc(m_end)
        start = max(0, pos - lookback + 1)
        window = returns.iloc[start : pos + 1]
        if window.shape[0] < 5:
            continue
        vol = window.std()
        chosen = vol.nsmallest(k).index.tolist()
        # 持有区间：下月末之前
        nxt = pos + 1
        if nxt >= len(dates):
            break
        # 持有至下一个月末（或期末）
        nxt_month = dates[nxt:].to_series().dt.to_period("M").drop_duplicates().index
        end_pos = len(dates) - 1
        if len(nxt_month) > 1:
            end_pos = dates.get_loc(nxt_month[1]) - 1
        hold = returns.loc[dates[nxt : end_pos + 1], chosen].mean(axis=1)
        port_ret.loc[hold.index] = hold
    return port_ret


def perf(port_ret: pd.Series) -> dict:
    ret = port_ret[port_ret != 0]
    if ret.empty:
        return {}
    cum = (1 + ret).cumprod()
    n_years = len(ret) / 252
    cagr = cum.iloc[-1] ** (1 / n_years) - 1 if n_years > 0 else 0
    sharpe = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else 0
    peak = cum.cummax()
    mdd = ((cum - peak) / peak).min()
    return {
        "n_days": int(len(ret)),
        "total_return_pct": round(float(cum.iloc[-1] - 1) * 100, 2),
        "cagr_pct": round(float(cagr) * 100, 2),
        "sharpe": round(float(sharpe), 2),
        "max_drawdown_pct": round(float(mdd) * 100, 2),
    }


def run(out_dir: str = ".") -> dict:
    os.makedirs(out_dir, exist_ok=True)
    print("[lowvol] 生成合成数据 ...")
    px = generate_synthetic()
    ret = px.pct_change().dropna()
    print(f"[lowvol] {px.shape[1]} 只股票 / {len(ret)} 交易日")
    port = monthly_lowvol_portfolio(ret, k=10)
    stats = perf(port)
    equity = (1 + port[port != 0]).cumprod()
    eq_path = os.path.join(out_dir, "lowvol_equity.csv")
    equity.to_csv(eq_path, header=["equity"])
    summ_path = os.path.join(out_dir, "lowvol_summary.json")
    with open(summ_path, "w", encoding="utf-8") as f:
        json.dump({"strategy": "monthly_lowvol", "params": {"k": 10, "lookback": 21}, "stats": stats}, f, indent=2)
    print(f"[lowvol] 年化 {stats['cagr_pct']}% | 夏普 {stats['sharpe']} | 最大回撤 {stats['max_drawdown_pct']}%")
    return {"stats": stats, "equity_path": eq_path, "summary_path": summ_path}


def main() -> None:
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backtest", "output")
    run(out)


if __name__ == "__main__":
    main()
