.PHONY: help install demo test docker-build docker-run monitor clean

help:
	@echo "可用目标:"
	@echo "  install       创建 .venv 并安装 requirements.txt"
	@echo "  demo          运行 scripts/run_demo.py 一键演示"
	@echo "  test          运行 pytest 单测"
	@echo "  docker-build  构建演示镜像"
	@echo "  docker-run    启动演示容器 (docker compose up app)"
	@echo "  monitor       启动监控栈 (Prometheus/Grafana/node-exporter)"
	@echo "  clean         清理 .venv / 生成物"

install:
	python -m venv .venv && .venv/bin/pip install -r requirements.txt

demo:
	python scripts/run_demo.py

test:
	python -m pytest tests/ -q

docker-build:
	docker compose build

docker-run:
	docker compose up app

monitor:
	docker compose up prometheus grafana node-exporter

clean:
	rm -rf .venv backtest/output *.duckdb output
