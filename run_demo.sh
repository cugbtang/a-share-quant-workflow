#!/usr/bin/env bash
# 一键本地演示（Linux / macOS / Git Bash / WSL）。
# 作用：创建 .venv → 安装依赖 → 运行 scripts/run_demo.py。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"

if [ ! -d ".venv" ]; then
  echo "[run_demo] 创建虚拟环境 .venv ..."
  "$PYTHON" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[run_demo] 安装依赖 ..."
pip install -q -r requirements.txt

echo "[run_demo] 运行演示 ..."
python scripts/run_demo.py "$@"
