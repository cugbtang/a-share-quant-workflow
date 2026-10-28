"""数据基建模块：行情拉取 + DuckDB 落库 + CLI。

用法：
    python -m data.cli demo                      # 合成数据自测（无需网络）
    python -m data.cli fetch --code 600519.SH    # 拉取并入库（需 akshare + 网络）
    python -m data.cli query --code 600519.SH     # 查询
"""
from . import fetch, store, cli  # noqa: F401
