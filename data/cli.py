"""命令行入口：拉数 / 入库 / 查询 / demo 自测。

示例：
    python -m data.cli demo                       # 合成数据写入并回查（无需网络）
    python -m data.cli fetch --code 600519.SH \\
        --start 2024-01-01 --end 2024-12-31       # 拉取并入库
    python -m data.cli query --code 600519.SH
"""
from __future__ import annotations

import argparse

import pandas as pd

from . import fetch, store


def _demo_frame(n: int = 60) -> pd.DataFrame:
    """生成合成日线，用于在无网络环境下验证存储层。"""
    import numpy as np

    dates = pd.date_range("2024-01-01", periods=n, freq="B").date
    rng = np.random.default_rng(0)
    base = 100.0 + rng.normal(0, 1, n).cumsum()
    return pd.DataFrame(
        {
            "code": "DEMO.SH",
            "date": dates,
            "open": base,
            "high": base + 1.0,
            "low": base - 1.0,
            "close": base + rng.normal(0, 0.5, n),
            "volume": rng.integers(1_000_000, 10_000_000, n).astype(float),
            "amount": rng.integers(100_000_000, 1_000_000_000, n).astype(float),
            "adj_close": base,
        }
    )


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m data.cli", description="数据基建 CLI")
    ap.add_argument("action", choices=["fetch", "query", "demo"])
    ap.add_argument("--code", default="600519.SH")
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2024-12-31")
    ap.add_argument("--db", default="quant.duckdb")
    args = ap.parse_args()

    con = store.connect(args.db)
    try:
        if args.action == "demo":
            df = _demo_frame()
            n = store.upsert_daily(con, df)
            print(f"[demo] 写入 {n} 行 -> {args.db}")
            print(store.query_daily(con, "DEMO.SH").head())
        elif args.action == "fetch":
            df = fetch.fetch_daily(args.code, args.start, args.end)
            n = store.upsert_daily(con, df)
            print(f"[fetch] {args.code} 入库 {n} 行")
        elif args.action == "query":
            out = store.query_daily(con, args.code)
            print(out.head(10))
            print(f"[query] 共 {len(out)} 行")
    finally:
        con.close()


if __name__ == "__main__":
    main()
