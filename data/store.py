"""DuckDB 行情存储层。

表结构（按 code+date 主键，支持 upsert 去重）：
    daily(code, date, open, high, low, close, volume, amount, adj_close)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import duckdb

_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily (
    code      VARCHAR,
    date      DATE,
    open      DOUBLE,
    high      DOUBLE,
    low       DOUBLE,
    close     DOUBLE,
    volume    DOUBLE,
    amount    DOUBLE,
    adj_close DOUBLE,
    PRIMARY KEY (code, date)
);
"""


def connect(db_path: str | Path = "quant.duckdb") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(db_path))
    con.execute(_SCHEMA)
    return con


def upsert_daily(con: duckdb.DuckDBPyConnection, df) -> int:
    """将规范化 DataFrame 写入 daily 表（按主键去重）。返回写入行数。"""
    required = ["code", "date", "open", "high", "low", "close", "volume", "amount", "adj_close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"upsert_daily 缺少列: {missing}")
    con.register("src", df)
    try:
        con.execute(
            """
            INSERT OR REPLACE INTO daily
            (code, date, open, high, low, close, volume, amount, adj_close)
            SELECT code, date, open, high, low, close, volume, amount, adj_close
            FROM src
            """
        )
    finally:
        con.unregister("src")
    return len(df)


def query_daily(
    con: duckdb.DuckDBPyConnection,
    code: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> "pd.DataFrame":
    sql = "SELECT * FROM daily WHERE code = ?"
    params: list = [code]
    if start:
        sql += " AND date >= ?"
        params.append(start)
    if end:
        sql += " AND date <= ?"
        params.append(end)
    sql += " ORDER BY date"
    return con.execute(sql, params).df()


def list_codes(con: duckdb.DuckDBPyConnection) -> list[str]:
    return [r[0] for r in con.execute("SELECT DISTINCT code FROM daily ORDER BY code").fetchall()]


def latest_date(con: duckdb.DuckDBPyConnection, code: str):
    return con.execute("SELECT MAX(date) FROM daily WHERE code = ?", [code]).fetchone()[0]
