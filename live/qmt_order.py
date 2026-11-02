"""实盘下单骨架 + 风控模块：迅投 miniQMT（XtTrader）。

本文件在原有"连接/报单/查询/撤单"骨架之上，补齐生产必需的风控：
  - RiskLimits / RiskController：单票仓位上限（金额 + 占比）、单笔委托上限、
    当日亏损熔断（circuit breaker）、黑名单。
  - QmtOrderClient 在每次 buy/sell 前调用 RiskController.pre_trade，
    不通过则不下单，并打印拒绝原因。

设计取舍：
  - RiskController 为纯逻辑、不依赖 xtquant，便于单测（见 tests/test_risk_controller.py）。
  - 熔断以"日初净值为基准的当日回撤"判定；命中后当天停止一切报单。
  - 真实成交的盈亏通过 register_fill 回灌，供更精细的当日盈亏统计。

⚠️ 未填写真实账号与通过模拟盘验证前，请勿直接实盘运行。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple

try:
    from xtquant.xttrader import XtTrader
    from xtquant.xttype import StockAccount
    from xtquant import xtconstant
except ImportError:  # pragma: no cover - 运行环境才装 xtquant
    XtTrader = StockAccount = xtconstant = None


@dataclass
class RiskLimits:
    """风控阈值（默认偏保守，按账户规模自行调整）。"""
    max_single_position_value: float = 200_000.0   # 单票市值上限（元）
    max_single_position_pct: float = 0.10          # 单票占账户净值上限（0~1）
    max_order_value: float = 200_000.0             # 单笔委托金额上限（元）
    max_daily_loss_pct: float = 2.0                # 当日净值回撤熔断阈值（%）
    blacklist: tuple = field(default_factory=tuple)  # 禁止交易代码，如 ("600519.SH",)


class RiskController:
    """纯逻辑风控，不依赖 xtquant，便于单测。

    equity_fn()       -> 账户当前总资产（元）
    position_fn(code) -> 该代码当前持仓市值（元）
    """

    def __init__(self, limits: RiskLimits,
                 equity_fn: Callable[[], float] = lambda: 0.0,
                 position_fn: Callable[[str], float] = lambda _: 0.0):
        self.limits = limits
        self._equity_fn = equity_fn
        self._position_fn = position_fn
        self.halted = False
        self.day_start_equity: Optional[float] = None
        self.realized_pnl: float = 0.0  # 当日已实现盈亏（元）

    # ---- 日初 / 日终 ----
    def on_new_day(self, equity: float) -> None:
        self.day_start_equity = equity
        self.realized_pnl = 0.0
        self.halted = False

    def register_fill(self, pnl: float) -> None:
        """成交后回灌当日已实现盈亏（元，可正可负）。"""
        self.realized_pnl += pnl

    # ---- 熔断检查 ----
    def _check_circuit_breaker(self, equity: float) -> Optional[str]:
        if self.day_start_equity and self.day_start_equity > 0:
            drawdown_pct = (self.day_start_equity - equity) / self.day_start_equity * 100.0
            if drawdown_pct > self.limits.max_daily_loss_pct:
                self.halted = True
                return (f"当日净值回撤 {drawdown_pct:.2f}% 超过熔断阈值 "
                        f"{self.limits.max_daily_loss_pct:.2f}%，已停止交易")
        return None

    def pre_trade(self, code: str, price: float, volume: int, side: str
                  ) -> Tuple[bool, str]:
        """返回 (是否放行, 原因)。side ∈ {'BUY','SELL'}。"""
        if self.halted:
            return False, "circuit-breaker 已触发，全天停止交易"
        if code in self.limits.blacklist:
            return False, f"{code} 在黑名单中"
        if volume <= 0 or price <= 0:
            return False, "价格或数量非法"

        equity = self._equity_fn()
        notional = price * volume

        if notional > self.limits.max_order_value:
            return False, f"单笔委托 {notional:.0f} 超过上限 {self.limits.max_order_value:.0f}"

        # 单票仓位上限（仅买入需要占用新仓位）
        if side.upper() == "BUY":
            pos = self._position_fn(code)
            if pos + notional > self.limits.max_single_position_value:
                return False, (f"买入后 {code} 市值 {pos + notional:.0f} 超过单票上限 "
                               f"{self.limits.max_single_position_value:.0f}")
            if equity > 0 and (pos + notional) / equity > self.limits.max_single_position_pct:
                return False, (f"买入后 {code} 占净值 {(pos + notional) / equity * 100:.1f}% "
                               f"超过 {self.limits.max_single_position_pct * 100:.1f}%")

        # 当日亏损熔断
        cb = self._check_circuit_breaker(equity)
        if cb:
            return False, cb

        return True, "ok"


class QmtOrderClient:
    def __init__(self, account_id: str, client_path: str, session_id: int = 123456,
                 limits: Optional[RiskLimits] = None, connect: bool = True):
        if XtTrader is None:
            raise RuntimeError("未安装 xtquant，请先安装 QMT 客户端自带的 xtquant 包")
        self.account_id = account_id
        self.client_path = client_path
        self.session_id = session_id
        self.xt_trader = XtTrader()
        self.account = StockAccount(account_id, "STOCK")
        self.risk = RiskController(
            limits or RiskLimits(),
            equity_fn=self._query_equity,
            position_fn=self._query_position_value,
        )
        if connect:
            self.connect()

    # ---- 账户查询（供风控回调）----
    def _query_equity(self) -> float:
        try:
            asset = self.xt_trader.query_asset(self.account)
            return float(getattr(asset, "cash", 0.0) + getattr(asset, "market_value", 0.0))
        except Exception:
            return 0.0

    def _query_position_value(self, code: str) -> float:
        try:
            positions = self.xt_trader.query_stock_positions(self.account)
            for p in positions or []:
                if getattr(p, "stock_code", None) == code:
                    return float(getattr(p, "market_value", 0.0) or 0.0)
        except Exception:
            return 0.0
        return 0.0

    def connect(self) -> bool:
        if not self.xt_trader.connect(self.client_path, self.session_id, 10):
            print("[qmt] 连接失败，请检查 QMT 客户端是否以 miniQMT 模式运行")
            return False
        if not self.xt_trader.subscribe(self.account):
            print("[qmt] 订阅账号失败")
            return False
        # 日初记录净值，作为熔断基准
        self.risk.on_new_day(self._query_equity())
        print(f"[qmt] 已连接账号 {self.account_id}，日初净值 {self._query_equity():.2f}")
        return True

    def buy(self, code: str, volume: int, price: float, remark: str = "") -> int:
        ok, reason = self.risk.pre_trade(code, price, volume, "BUY")
        if not ok:
            print(f"[risk] 拒绝买入 {code} {volume}@{price}: {reason}")
            return 0
        return self.xt_trader.trade(self.account, code, price, volume, xtconstant.STOCK_BUY)

    def sell(self, code: str, volume: int, price: float, remark: str = "") -> int:
        ok, reason = self.risk.pre_trade(code, price, volume, "SELL")
        if not ok:
            print(f"[risk] 拒绝卖出 {code} {volume}@{price}: {reason}")
            return 0
        return self.xt_trader.trade(self.account, code, price, volume, xtconstant.STOCK_SELL)

    def cancel_order(self, order_id: int) -> bool:
        """撤单（兼容不同 xtquant 版本的取消接口）。"""
        try:
            if hasattr(self.xt_trader, "cancel_order_stock"):
                return bool(self.xt_trader.cancel_order_stock(self.account, order_id))
            return bool(self.xt_trader.cancel_order(order_id))
        except Exception as e:
            print(f"[qmt] 撤单失败 {order_id}: {e}")
            return False

    def query_position(self):
        return self.xt_trader.query_stock_positions(self.account)

    def query_orders(self):
        return self.xt_trader.query_stock_orders(self.account)

    def disconnect(self):
        self.xt_trader.disconnect()


def main() -> None:
    import os

    account_id = os.environ.get("QMT_ACCOUNT", "")
    client_path = os.environ.get("QMT_CLIENT_PATH", r"C:/国金QMT/userdata_mini")
    if not account_id:
        print("请设置环境变量 QMT_ACCOUNT 后运行（示例骨架，不实际下单）")
        return
    client = QmtOrderClient(account_id, client_path)
    if not client.connect():
        return
    try:
        # 风控演示：黑名单 / 单票上限等可在 RiskLimits 中配置
        # client.buy("600519.SH", 100, 0.0)  # 已注释，避免误下单
        print("持仓:", client.query_position())
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
