#!/usr/bin/env bash
# K8s CronJob 入口：跑一遍回测/事件研究管道，并把运行结果写入 state 文件，
# 供 live/metrics_exporter.py 读取、Prometheus 抓取。
#
# 依赖：镜像内已含本仓库（/app），且挂载了 PVC 到 /data（与 exporter 共享）。
set -euo pipefail

cd "$(dirname "$0")/.."

export STATE_FILE="${METRICS_STATE_FILE:-/data/quant_state.json}"
export PIPE_START_TS="$(date -u +%s)"

echo "[pipeline] start ts=${PIPE_START_TS}"

# 1) 数据基建自测（离线可用，验证 DuckDB 落库链路）
python -m data.cli demo

# 2) 一键演示：低波策略回测 + （若设置 WESTOCK_BIN）降息事件研究
#    失败不阻断后续；用 DEMO_RC 记录是否异常，写入 order_fail_total
set +e
WESTOCK_BIN="${WESTOCK_BIN:-}" python scripts/run_demo.py
export DEMO_RC=$?
set -e
echo "[pipeline] run_demo rc=${DEMO_RC}"

# 3) 写出 state 供 exporter（真实场景这里填实际 equity / order_fail / 延迟）
python - <<'PY'
import json, os, time
start = float(os.environ.get("PIPE_START_TS", time.time()))
rc = int(os.environ.get("DEMO_RC", "0"))
state = {
    "last_run_ts": start,
    "equity_return_pct": 0.0,
    "order_fail_total": rc,
    "signal_latency_ms": 0.0,
}
path = os.environ.get("METRICS_STATE_FILE", "/data/quant_state.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(state, f)
print("[pipeline] wrote state ->", path)
PY

echo "[pipeline] done"
exit 0
