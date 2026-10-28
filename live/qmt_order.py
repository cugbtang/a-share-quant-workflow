"""实盘下单骨架：迅投 miniQMT（XtTrader）。

这是一个**骨架/模板**，需要你本地具备：
  1. 安装并登录 迅投 QMT 极速交易客户端（miniQMT 模式，保持运行）。
  2. `pip install xtquant`（随 QMT 客户端附带，或从券商提供的包安装）。
  3. 在支持 QMT 的券商开户，拿到资金账号。

本文件演示：连接、订阅、报单、查询持仓/委托。生产环境还需接入：
  - 风控（单票仓位上限、当日亏损熔断、黑名单）
  - 信号源（来自 backtest/ 产出的选股结果或实时策略）
  - 监控上报（Prometheus，见 monitor/）

⚠️ 未填写真实账号与通过模拟盘验证前，请勿直接实盘运行。
"""
from __future__ import annotations

import time
from typing import Optional

try:
    from xtquant.xttrader import XtTrader
    from xtquant.xttype import StockAccount
    from xtquant import xtconstant
except ImportError:  # pragma: no cover - 运行环境才装 xtquant
    XtTrader = StockAccount = xtconstant = None


class QmtOrderClient:
    def __init__(self, account_id: str, client_path: str, session_id: int = 123456):
        if XtTrader is None:
            raise RuntimeError("未安装 xtquant，请先安装 QMT 客户端自带的 xtquant 包")
        self.account_id = account_id
        self.client_path = client_path
        self.session_id = session_id
        self.xt_trader = XtTrader()
        self.account = StockAccount(account_id, "STOCK")

    def connect(self) -> bool:
        # 1) 建立交易连接
        if not self.xt_trader.connect(self.client_path, self.session_id, 10):
            print("[qmt] 连接失败，请检查 QMT 客户端是否以 miniQMT 模式运行")
            return False
        # 2) 绑定资金账号
        if not self.xt_trader.subscribe(self.account):
            print("[qmt] 订阅账号失败")
            return False
        print(f"[qmt] 已连接账号 {self.account_id}")
        return True

    def buy(self, code: str, volume: int, price: float, remark: str = "") -> int:
        """限价买入。volume 为股数（100 的整数倍）。返回委托号，<=0 表示失败。"""
        return self.xt_trader.trade(self.account, code, price, volume, xtconstant.STOCK_BUY)

    def sell(self, code: str, volume: int, price: float, remark: str = "") -> int:
        """限价卖出。"""
        return self.xt_trader.trade(self.account, code, price, volume, xtconstant.STOCK_SELL)

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
        # TODO: 接入真实信号与风控后再报单
        # client.buy("600519.SH", 100, 0.0)  # 已注释，避免误下单
        print("持仓:", client.query_position())
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
