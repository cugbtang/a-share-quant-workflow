"""回测模块：通用事件/规则回测引擎 + 示例策略。

子模块：
    engine.py        # 通用工具：拉数、解析、事件收益、统计
    event_study.py   # 示例：央行降息后持有沪深300ETF 20日收益
    strategy_lowvol.py # 示例：月度低波选股（合成数据可跑版）
    dashboard.py     # 自包含 HTML 看板生成
"""
from . import engine, event_study, strategy_lowvol, dashboard  # noqa: F401
