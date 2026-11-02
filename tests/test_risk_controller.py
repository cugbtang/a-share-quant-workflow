"""RiskController 纯逻辑单测（无需 xtquant / 网络）。"""
from __future__ import annotations

from live.qmt_order import RiskController, RiskLimits


def test_blacklist_rejected():
    rc = RiskController(RiskLimits(blacklist=("600519.SH",)))
    ok, reason = rc.pre_trade("600519.SH", 100.0, 100, "BUY")
    assert not ok and "黑名单" in reason


def test_single_position_value_limit():
    # 当前持仓 150000，买入 100*1000=100000 -> 250000 超过 200000 上限
    rc = RiskController(
        RiskLimits(max_single_position_value=200_000.0),
        equity_fn=lambda: 1_000_000.0,
        position_fn=lambda code: 150_000.0,
    )
    ok, reason = rc.pre_trade("600519.SH", 1000.0, 100, "BUY")
    assert not ok and "单票上限" in reason


def test_single_position_pct_limit():
    # 市值占比 (100*1000)/1_000_000 = 10% 恰好等于上限，通过；略微超出则拒绝
    rc = RiskController(
        RiskLimits(max_single_position_value=999_999_999.0,
                   max_single_position_pct=0.10),
        equity_fn=lambda: 1_000_000.0,
        position_fn=lambda code: 0.0,
    )
    assert rc.pre_trade("600519.SH", 1000.0, 100, "BUY")[0] is True
    ok, _ = rc.pre_trade("600519.SH", 1000.0, 101, "BUY")
    assert ok is False


def test_order_value_limit():
    rc = RiskController(RiskLimits(max_order_value=200_000.0),
                        equity_fn=lambda: 1_000_000.0,
                        position_fn=lambda code: 0.0)
    ok, reason = rc.pre_trade("600519.SH", 3000.0, 100, "BUY")
    assert not ok and "单笔委托" in reason


def test_circuit_breaker_halts():
    rc = RiskController(RiskLimits(max_daily_loss_pct=2.0),
                        equity_fn=lambda: 1_000_000.0,
                        position_fn=lambda code: 0.0)
    rc.on_new_day(1_000_000.0)
    # 模拟净值跌到 970000（回撤 3% > 2%）-> 触发熔断
    rc._query_equity = lambda: 970_000.0  # 直接替换回调
    rc._equity_fn = lambda: 970_000.0
    ok, reason = rc.pre_trade("600519.SH", 10.0, 100, "BUY")
    assert not ok and rc.halted is True
    # 熔断后任何订单都被拒
    assert rc.pre_trade("000001.SZ", 10.0, 100, "BUY")[0] is False


def test_sell_not_blocked_by_position_limit():
    rc = RiskController(
        RiskLimits(max_single_position_value=200_000.0),
        equity_fn=lambda: 1_000_000.0,
        position_fn=lambda code: 150_000.0,
    )
    # 卖出不受"买入后市值"限制约束
    ok, reason = rc.pre_trade("600519.SH", 1000.0, 100, "SELL")
    assert ok is True
