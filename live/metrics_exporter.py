"""实盘 Prometheus 指标导出器（供 K8s 中 Prometheus 抓取）。

读取由 k8s/run_pipeline.sh 在每次跑批后写入的 state JSON：
  { "last_run_ts": <unix秒>, "equity_return_pct": <float>,
    "order_fail_total": <int>, "signal_latency_ms": <float> }

导出 monitor/alerts.yml 约定的四个指标：
  marketdata_freshness_seconds / signal_latency_ms /
  order_fail_total / strategy_equity_return_pct

指标口径（生产请替换为真实值）：
  - marketdata_freshness_seconds：now - last_run_ts（管道多久没成功跑过）
  - signal_latency_ms：单次信号计算耗时
  - order_fail_total：累计下单失败次数
  - strategy_equity_return_pct：实盘累计收益率
"""
from __future__ import annotations

import json
import os
import time

from prometheus_client import Gauge, start_http_server

STATE_FILE = os.environ.get("METRICS_STATE_FILE", "/data/quant_state.json")
PORT = int(os.environ.get("METRICS_PORT", "8000"))

_freshness = Gauge("marketdata_freshness_seconds", "行情/管道新鲜度（秒）")
_signal_latency = Gauge("signal_latency_ms", "信号计算延迟（毫秒）")
_order_fail = Gauge("order_fail_total", "下单失败累计次数")
_equity_return = Gauge("strategy_equity_return_pct", "实盘累计收益率（%）")


def _update() -> None:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            s = json.load(f)
    except Exception:
        # 无 state 文件时只让 freshness 持续上涨，由 alert 兜底告警
        return
    ts = float(s.get("last_run_ts", 0.0))
    _freshness.set(max(0.0, time.time() - ts))
    _signal_latency.set(float(s.get("signal_latency_ms", 0.0)))
    _order_fail.set(float(s.get("order_fail_total", 0.0)))
    _equity_return.set(float(s.get("equity_return_pct", 0.0)))


def main() -> None:
    start_http_server(PORT)
    print(f"[metrics] serving /metrics on :{PORT}, state={STATE_FILE}")
    while True:
        _update()
        time.sleep(5)


if __name__ == "__main__":
    main()
