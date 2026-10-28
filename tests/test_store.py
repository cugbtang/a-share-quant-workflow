import pandas as pd

from data import store


def _frame(code: str, dates):
    return pd.DataFrame(
        {
            "code": [code] * len(dates),
            "date": pd.to_datetime(dates).date,
            "open": list(range(1, len(dates) + 1)),
            "high": list(range(2, len(dates) + 2)),
            "low": list(range(0, len(dates))),
            "close": list(range(1, len(dates) + 1)),
            "volume": list(range(1, len(dates) + 1)),
            "amount": list(range(1, len(dates) + 1)),
            "adj_close": list(range(1, len(dates) + 1)),
        }
    )


def test_upsert_dedup(tmp_path):
    con = store.connect(tmp_path / "t.duckdb")
    df = _frame("A.SH", ["2024-01-01", "2024-01-02", "2024-01-03"])
    store.upsert_daily(con, df)
    store.upsert_daily(con, df)  # 重复写入应被主键去重
    out = store.query_daily(con, "A.SH")
    assert len(out) == 3, len(out)
    assert store.list_codes(con) == ["A.SH"]
    assert str(store.latest_date(con, "A.SH")) == "2024-01-03"
    con.close()


def test_query_range(tmp_path):
    con = store.connect(tmp_path / "t2.duckdb")
    df = _frame("B.SH", ["2024-01-01", "2024-01-02", "2024-01-03"])
    store.upsert_daily(con, df)
    out = store.query_daily(con, "B.SH", start="2024-01-02")
    assert len(out) == 2
    con.close()
