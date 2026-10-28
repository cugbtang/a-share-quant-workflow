# 一键本地演示（Windows PowerShell / pwsh）。
# 作用：创建 .venv → 安装依赖 → 运行 scripts/run_demo.py。
$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

if (-not (Test-Path ".venv")) {
    Write-Host "[run_demo] 创建虚拟环境 .venv ..."
    python -m venv .venv
}

& ".venv/Scripts/Activate.ps1"

Write-Host "[run_demo] 安装依赖 ..."
pip install -q -r requirements.txt

Write-Host "[run_demo] 运行演示 ..."
python scripts/run_demo.py @args
