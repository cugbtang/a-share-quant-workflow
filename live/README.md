# 实盘工程骨架（live/）

把"跑通的策略"接成可 7×24 运行的实盘 + 监控闭环。

## 1. 下单：`qmt_order.py`

基于**迅投 miniQMT（XtTrader）**的程序化下单骨架。

前置条件：
- 安装并登录 QMT 极速交易客户端（miniQMT 模式，保持运行）。
- 安装 `xtquant`（随 QMT 客户端附带）。
- 在支持 QMT 的券商开户，拿到资金账号。

运行：
```bash
export QMT_ACCOUNT="你的资金账号"
export QMT_CLIENT_PATH="C:/国金QMT/userdata_mini"   # 按实际路径
python live/qmt_order.py
```
> 默认 `main()` 不会实际下单（已注释 `buy/sell`）。接入真实信号与风控后再打开。

生产环境还需补齐（本骨架未含，需自行实现）：
- 风控：单票仓位上限、当日亏损熔断、黑名单。
- 信号接入：来自 `backtest/` 的选股结果或实时策略输出。
- 报单状态跟踪与撤单逻辑。

## 2. 监控：`monitor/` + `docker-compose.yml`

复用 DevOps 长板，用 Prometheus + Grafana 盯实盘最该关心的 4 件事：
- 行情心跳是否中断（`marketdata_freshness_seconds`）
- 信号计算延迟（`signal_latency_ms`）
- 下单失败次数（`order_fail_total`）
- 实盘回撤（`strategy_equity_return_pct`）

启动：
```bash
cd live && docker compose up -d
# Grafana: http://localhost:3000  (admin/admin)
# Prometheus: http://localhost:9090
```

策略服务需通过 `/metrics` 暴露上述指标（指标名见 `monitor/alerts.yml`）。示例（Python）：
```python
from prometheus_client import start_http_server, Gauge
fresh = Gauge("marketdata_freshness_seconds", "行情新鲜度")
# 定时更新 fresh.set(...)
start_http_server(8000)
```

## 注意

- 本目录为**骨架/模板**，未含真实账号、券商配置与完整风控；直接实盘前务必先在模拟盘跑通。
- 不同券商的 QMT 客户端路径、`xtquant` 包版本可能不同，按券商文档调整。
- 监控栈中的密码仅为示例，生产请改用密钥管理。

> ⚠️ 本代码仅供参考，不构成投资建议或开户/交易建议。
