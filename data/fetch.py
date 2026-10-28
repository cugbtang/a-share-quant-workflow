"""行情拉取层。

优先使用 AkShare（免费、覆盖全）。网络/接口异常时做有限重试。
所有输出统一规范化为列：
    code, date, open, high, low, close, volume, amount, adj_close
其中 date 为 python date 类型（无时分），便于与 DuckDB DATE 对齐。
"""
from __future__ import annotations

import time
from typing import Optional

import pandas as pd

try:
    import akshare as ak
except ImportError:  # pragma: no cover - 运行时缺失由调用方抛错提示
    ak = None


def _norm_ak(df: pd.DataFrame, code: str) -> pd.DataFrame:
    df = df.rename(
        columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "amount",
        }
    )
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["adj_close"] = df["close"]
    df["code"] = code
    cols = ["code", "date", "open", "high", "low", "close", "volume", "amount", "adj_close"]
    return df[cols]


def _to_ak_symbol(code: str) -> str:
    """'600519.SH' / 'sh600519' -> akshare 的 '600519'。"""
    sym = code.lower().replace(".sh", "").replace(".sz", "").replace("sh", "").replace("sz", "")
    return sym.lstrip("0") if False else sym  # 保留前导 0


def fetch_daily(
    code: str,
    start: str,
    end: str,
    adjust: str = "qfq",
    retries: int = 3,
) -> pd.DataFrame:
    """拉取单标的日线。code 形如 '600519.SH' 或 'sh600519'。

    返回规范化的 DataFrame（见模块 docstring 列定义）。
    """
    if ak is None:
        raise RuntimeError("akshare 未安装，请先 `pip install akshare`")
    sym = _to_ak_symbol(code)
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            df = ak.stock_zh_a_hist(
                symbol=sym,
                period="daily",
                start_date=start.replace("-", ""),
                end_date=end.replace("-", ""),
                adjust=adjust,
            )
            if df is None or df.empty:
                raise ValueError("接口返回空数据")
            return _norm_ak(df, code)
        except Exception as e:  # 网络抖动/限流，退避重试
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch_daily {code} 失败（已重试 {retries} 次）: {last}")


def fetch_index_universe() -> list[str]:
    """常用指数代码占位。真实成分用 ak.index_stock_cons 拉取后替换。"""
    return ["000300.SH", "000905.SH", "000852.SH"]
