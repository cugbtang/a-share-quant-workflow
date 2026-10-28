"""示例策略：央行降息后持有沪深300ETF(510300) 20 个交易日的事件研究。

事件定义（政策利率 7天逆回购 / MLF 下调，或 LPR 单独下调；降准不计入；
同一轮逆回购/MLF/LPR 连续下调合并为一次，以政策利率公告日为锚点）：
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime

from . import engine

ETF_CODE = "sh510300"
HOLD_DAYS = 20

EVENTS = [
    ("2022-01-17", "政策利率(逆回购/MLF)下调", "policy"),
    ("2022-05-20", "5年期LPR单独下调", "lpr"),
    ("2022-08-15", "政策利率(MLF)下调", "policy"),
    ("2023-06-13", "政策利率(逆回购)下调", "policy"),
    ("2023-08-15", "政策利率(MLF)下调", "policy"),
    ("2024-02-20", "5年期LPR单独下调", "lpr"),
    ("2024-07-22", "政策利率(逆回购/MLF)下调", "policy"),
    ("2024-09-24", "924一揽子刺激(降息+降准+资本市场支持)", "policy"),
    ("2025-05-08", "政策利率(逆回购/MLF)下调", "policy"),
]


def run(out_dir: str = ".") -> dict:
    os.makedirs(out_dir, exist_ok=True)
    print(f"[event_study] 拉取 {ETF_CODE} 日线 ...")
    df = engine.fetch_kline(ETF_CODE, limit=2200)
    print(f"[event_study] 共 {len(df)} 个交易日 ({df['date'].iloc[0]} ~ {df['date'].iloc[-1]})")

    trades = []
    for date, label, etype in EVENTS:
        r = engine.event_return(df, date, hold_days=HOLD_DAYS)
        if r is None:
            print(f"  ! {date} 数据不足，跳过")
            continue
        r["label"] = label
        r["type"] = etype
        trades.append(r)
        print(f"  {date} {label}: {r['pnl_pct']:+.2f}%  ({r['buy_date']}->{r['sell_date']})")

    pnls = [t["pnl_pct"] for t in trades]
    stats = engine.compute_stats(pnls)
    stats["hold_days"] = HOLD_DAYS
    stats["symbol"] = ETF_CODE
    stats["buy_rule"] = "事件后下一交易日开盘买入"
    stats["sell_rule"] = f"持有 {HOLD_DAYS} 交易日后收盘卖出（无费用）"

    # 写出标准三件套
    trades_path = os.path.join(out_dir, "pbc_cut_csi300_trades.csv")
    with open(trades_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["event_date", "label", "type", "buy_date", "sell_date", "buy_open", "sell_close", "pnl_pct"])
        w.writeheader()
        w.writerows(trades)

    summary_path = os.path.join(out_dir, "pbc_cut_csi300_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"stats": stats, "trades": trades}, f, ensure_ascii=False, indent=2)

    print(f"[event_study] 平均 {stats['mean_pct']:+.2f}% | 中位 {stats['median_pct']:+.2f}% | 胜率 {stats['win_rate']}%")
    return {"stats": stats, "trades": trades, "trades_path": trades_path, "summary_path": summary_path}


def main() -> None:
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backtest", "output")
    run(out)


if __name__ == "__main__":
    main()
