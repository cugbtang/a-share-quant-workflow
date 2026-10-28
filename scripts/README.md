# 一键部署 / 演示（PR5）

本目录让仓库具备「开源项目常见的一键跑通 demo」能力，无需手动装依赖、无需逐个模块敲命令。

## 三种运行方式

### 1. 本地虚拟环境（首次体验推荐）
```bash
make demo
# 等价于：
bash run_demo.sh          # Linux/macOS/Git Bash
pwsh run_demo.ps1         # Windows PowerShell
```
脚本会：建 `.venv` → `pip install -r requirements.txt` → 跑 `scripts/run_demo.py`。

### 2. Docker 一键
```bash
docker compose up app                 # 仅演示容器
docker compose up                     # 演示 + 监控栈（Prometheus/Grafana/node-exporter）
```

### 3. 直接调用编排脚本
```bash
pip install -r requirements.txt
python scripts/run_demo.py
```

## 演示内容
- `data.cli demo`：用合成日线写入 DuckDB 并回查，验证存储层（**离线**）。
- `backtest.strategy_lowvol`：合成多标的日收益，跑月度低波选股，输出 `backtest/output/lowvol_equity.csv` 与 `lowvol_summary.json`（**离线**）。

## 接入真实数据（可选）
设置 `WESTOCK_BIN` 指向 [westock-data](https://github.com/...) 的 Node 入口后重跑，
`run_demo.py` 会自动追加 `backtest.event_study`（央行降息后持有沪深300ETF 20 日事件研究，**需联网**）：
```bash
export WESTOCK_BIN="node /abs/path/westock-data/scripts/index.js"
python scripts/run_demo.py
# Docker：
WESTOCK_BIN="node /abs/path/westock-data/scripts/index.js" docker compose up app
```

## 监控栈
`docker compose up` 起的 Prometheus（:9090）/ Grafana（:3000，admin/admin）/ node-exporter（:9100）
复用 `live/monitor/` 下的配置与看板。策略服务暴露 `/metrics` 后即可在 Grafana 看到净值、信号延迟、下单失败等。
