#!/usr/bin/env python3
"""一键演示编排脚本：本地 / Docker / Makefile 统一入口。

跑通两件「离线即可运行」的事（合成数据，无需网络）：
  1. data.cli demo            —— DuckDB 落库自测
  2. backtest.strategy_lowvol —— 合成低波选股回测（输出 equity/summary）

若环境变量 WESTOCK_BIN 指向 westock-data 的 Node 入口，
则额外运行 backtest.event_study（真实行情，需联网）。

退出码：全部成功 0，任一失败 1。
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_module(module: str, *args: str) -> bool:
    cmd = [sys.executable, "-m", module, *args]
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode == 0


def main() -> int:
    print("=" * 64)
    print(" a-share-quant-workflow — 一键演示")
    print("=" * 64)

    ok = True
    ok &= _run_module("data.cli", "demo")
    ok &= _run_module("backtest.strategy_lowvol")

    westock = os.environ.get("WESTOCK_BIN")
    if westock:
        os.environ["WESTOCK_BIN"] = westock  # 透传给子进程
        print(f"\n[info] 检测到 WESTOCK_BIN，额外运行降息事件研究（真实数据）")
        ok &= _run_module("backtest.event_study")
    else:
        print("\n[info] 未设置 WESTOCK_BIN，跳过降息事件研究。")
        print("       设置后重跑: WESTOCK_BIN=\"node /path/westock-data/scripts/index.js\" \\")
        print("                   python scripts/run_demo.py")

    print("\n" + ("✅ 演示完成（详见上方各模块输出）" if ok else "⚠️ 部分步骤失败，请查看上方日志"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
