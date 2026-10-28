## 内容
补齐开源项目常见的「一键跑通 demo」能力，让仓库无需手动装依赖、无需逐个模块敲命令即可本地 / 容器演示。

- `scripts/run_demo.py`：统一编排入口。默认离线跑 `data.cli demo`（DuckDB 落库）+ `backtest.strategy_lowvol`（合成低波选股回测）；设置 `WESTOCK_BIN` 后自动追加 `backtest.event_study`（真实行情，需联网）。
- `run_demo.sh` / `run_demo.ps1`：本地虚拟环境一键（Linux/macOS/Windows）。
- `Makefile`：`make demo / test / docker-build / docker-run / monitor / clean`。
- `Dockerfile`：`python:3.11-slim` 镜像，离线跑通演示。
- `docker-compose.yml`：演示容器 + 监控栈（Prometheus/Grafana/node-exporter，复用 `live/monitor/` 配置）。
- `.dockerignore`、`scripts/README.md`、README 新增「快速开始 / 一键部署」章节与目录树更新。

## 三种运行方式
1. 本地：`make demo`（或 `bash run_demo.sh` / PowerShell 运行 `run_demo.ps1`）
2. 容器：`docker compose up app` 仅演示；`docker compose up` 演示 + 监控栈
3. 直接：`python scripts/run_demo.py`

## 验证
- `python -m py_compile scripts/run_demo.py` 通过。
- `bash -n run_demo.sh` 通过。
- `Makefile` recipe 行使用 tab（GNU make 要求，正确）。
- `docker-compose.yml` 无 tab、2 空格缩进（标准 compose 格式）；本环境无 PyYAML / Docker，未做解析与构建。
- 离线演示路径（`data.cli demo` + 低波回测）在本仓库前期会话已实跑成功。

## 范围
- 演示 / 部署脚手架，不含真实策略逻辑改动（逻辑复用 PR1/PR2）。
- 监控栈为「待接入」状态：策略服务需自行暴露 `/metrics` 后才能在 Grafana 看到净值 / 延迟 / 失败。

> ⚠️ 本代码仅供参考，不构成投资建议。
