"""示例策略：央行降息后持有沪深300ETF(510300) 20 个交易日的事件研究。

事件定义（政策利率 7天逆回购 / MLF 下调，或 LPR 单独下调；降准不计入；
同一轮逆回购/MLF/LPR 连续下调合并为一次，以政策利率公告日为锚点）：

数据管道（完整链路，优先走 data/ 层）：
  1. 优先从 data/store（DuckDB 本地库）读取已落库的日线；
  2. 本地无数据则通过 data/fetch（AkShare）拉取并 upsert 落库；
  3. 仍失败（无 AkShare / 无网络）则回退 engine.fetch_kline（westock-data）。
这样事件研究与数据基建（data/）共用同一份落地数据，避免重复拉取与口径分歧。
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime

# 允许以脚本方式直接运行：把仓库根加入 path，使 `data` 可被 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import fetch as data_fetch, store as data_store
from . import engine

ETF_CODE = "sh510300"
DB_PATH = os.environ.get("QUANT_DB", "quant.duckdb")
HOLD_DAYS = 20
# 拉取区间起点：覆盖最早事件前约 60 个交易日，保证事件后有足够样本
FETCH_START = "2021-11-01"

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


def _load_kline() -> "pd.DataFrame":
    """完整数据管道：DuckDB 优先 -> AkShare 拉取落库 -> westock 回退。

    返回列：date, open, high, low, close, volume, amount（外加 code/adj_close）。
    """
    # 1) 本地 DuckDB 优先
    try:
        con = data_store.connect(DB_PATH)
        df = data_store.query_daily(con, ETF_CODE)
        if not df.empty:
            print(f"[event_study] 命中本地库 {DB_PATH}: {len(df)} 行")
            con.close()
            return df
        # 2) 本地为空，尝试 AkShare 拉取并落库
        print(f"[event_study] 本地库无 {ETF_CODE}，尝试 AkShare 拉取 ...")
        end = datetime.today().strftime("%Y-%m-%d")
        # 注：510300 为 ETF，AkShare 实际可用 fund_etf_hist_em；
        # 此处复用 data.fetch 的通用日线接口，若返回为空会在下方回退。
        fresh = data_fetch.fetch_daily(ETF_CODE, FETCH_START, end)
        if fresh is not None and not fresh.empty:
            data_store.upsert_daily(con, fresh)
            print(f"[event_study] 已落库 {len(fresh)} 行 -> {DB_PATH}")
            con.close()
            return fresh
        con.close()
    except Exception as e:  # 缺 akshare / DuckDB / 网络异常等
        print(f"[event_study] 数据层不可用（{e}），回退 westock-data")

    # 3) 回退：westock-data（需要 Node 环境与本机行情源）
    return engine.fetch_kline(ETF_CODE, limit=2200)


def run(out_dir: str = ".") -> dict:
    os.makedirs(out_dir, exist_ok=True)
    df = _load_kline()
    if df.empty:
        raise RuntimeError("无法获取行情数据（数据层与 westock 回退均失败）")
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
