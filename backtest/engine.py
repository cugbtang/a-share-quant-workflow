"""回测通用引擎：行情获取、Markdown 解析、事件收益、统计。

设计要点（规避回测常见偏差）：
- 买点用"事件后第一个交易日开盘价"，只用公告后才知道的价格，规避前视偏差。
- 卖点用持有 N 个交易日后的收盘价，满足 A 股 T+1（持有 >=1 日即可卖出）。
- 默认不计交易成本（事件研究惯例）；如需计入可在调用处扣减。
- 单一标的、单事件独立统计，不构造组合，避免幸存者偏差混入。
"""
from __future__ import annotations

import os
import subprocess
from typing import Optional

import pandas as pd


def _westock_cmd() -> list[str]:
    """定位 westock-data 可执行命令。

    优先读环境变量 WESTOCK_BIN（如 'node /path/index.js'）；
    否则回退到 PATH 中的 'westock-data'。
    """
    bin_ = os.environ.get("WESTOCK_BIN")
    if bin_:
        return bin_.split()
    return ["westock-data"]


def fetch_kline(code: str, limit: int = 2200, fq: str = "qfq") -> pd.DataFrame:
    """通过 westock-data 拉取日线，返回按日期升序的 DataFrame。

    列：date, open, high, low, close, volume, amount
    """
    cmd = _westock_cmd() + ["kline", code, "--period", "day", "--fq", fq, "--limit", str(limit)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return parse_kline_markdown(proc.stdout)


def parse_kline_markdown(text: str) -> pd.DataFrame:
    """解析 westock-data 的 Markdown 表格输出（最新在前）。

    westock 输出列：date | open | last | high | low | volume | amount | exchange
    其中 'last' 即当日收盘价。
    """
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if "---" in line:  # 分隔行
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and cells[0] == "date":  # 表头
            continue
        if len(cells) < 7:
            continue
        try:
            rows.append(
                {
                    "date": pd.to_datetime(cells[0]).date(),
                    "open": float(cells[1]),
                    "close": float(cells[2]),  # 'last' = 收盘价
                    "high": float(cells[3]),
                    "low": float(cells[4]),
                    "volume": float(cells[5]),
                    "amount": float(cells[6]),
                }
            )
        except ValueError:
            continue
    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "amount"])
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return df


def event_return(
    df: pd.DataFrame,
    event_date,
    hold_days: int = 20,
    cost_bps: float = 0.0,
) -> Optional[dict]:
    """计算单个事件收益。

    买：event_date 之后第一个交易日开盘价；
    卖：持有 hold_days 个交易日后收盘价（T+1 满足）。
    cost_bps：双边成本（基点），如 10 = 0.1%。
    返回 dict 或 None（数据不足时）。
    """
    if df.empty or len(df) <= hold_days + 1:
        return None
    ev = pd.to_datetime(event_date).date()
    future = df[df["date"] > ev]
    if future.empty:
        return None
    buy_idx = future.index[0]
    sell_idx = buy_idx + hold_days
    if sell_idx >= len(df):
        return None
    buy_open = float(df.at[buy_idx, "open"])
    sell_close = float(df.at[sell_idx, "close"])
    pnl = (sell_close - buy_open) / buy_open * 100.0
    pnl -= cost_bps / 100.0 * 2  # 双边成本
    return {
        "event_date": str(ev),
        "buy_date": str(df.at[buy_idx, "date"]),
        "sell_date": str(df.at[sell_idx, "date"]),
        "buy_open": round(buy_open, 4),
        "sell_close": round(sell_close, 4),
        "pnl_pct": round(pnl, 3),
    }


def compute_stats(pnls: list[float]) -> dict:
    """事件级统计：均值/中位数/胜率/最佳/最差/样本数。"""
    if not pnls:
        return {"n": 0}
    s = pd.Series(pnls)
    return {
        "n": int(s.shape[0]),
        "mean_pct": round(float(s.mean()), 3),
        "median_pct": round(float(s.median()), 3),
        "win_rate": round(float((s > 0).mean() * 100), 1),
        "best_pct": round(float(s.max()), 3),
        "worst_pct": round(float(s.min()), 3),
    }
