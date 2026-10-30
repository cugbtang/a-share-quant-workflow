## 内容
为在 WSL2 / Docker 中一键跑通 demo 做健壮性增强（不改变离线 demo 行为）：

- `requirements.txt`：拆分为「核心依赖」最小集（pandas/numpy/duckdb/pyarrow/pytest），**不再默认装 akshare**。离线 demo（`data.cli demo` + 低波回测）完全用不到 akshare，去掉后镜像构建更快、免去 slim 镜像下 akshare 依赖树编译失败风险。
- `requirements-full.txt`：`-r requirements.txt` + `akshare`，仅当你要用 `python -m data.cli fetch` 拉真实日线时才安装。
- `Dockerfile`：`pip install` 前先 `pip install --upgrade pip`，并只装核心依赖。
- `.dockerignore`：移除误把 `Dockerfile`/`docker-compose.yml` 自身排除的规则，改为忽略 `.env`/`.env.example`（避免密钥模板进入镜像）。
- `.env.example`：给出 `WESTOCK_BIN` 的填写示例（真实数据事件研究用）。
- `README.md`：快速开始章节补充「真实数据需 `requirements-full.txt`」说明。

## 验证
- `data/fetch.py` 中 akshare 为懒加载（`try/except ImportError → ak=None`），因此 `data.cli demo` 在**未安装 akshare** 时也不会 ImportError（已确认）。
- 本沙箱无 Docker，未实跑 `docker build`；改动仅涉及依赖分层与忽略规则，逻辑未变。
- 离线 demo 路径（`data.cli demo` + `backtest.strategy_lowvol`）在本仓库前期会话已实跑成功。

## 范围
- 仅优化 Docker 构建与依赖分层；策略/数据逻辑未改。
- 真实数据拉取（`fetch` + akshare）需自行 `pip install -r requirements-full.txt`。

> ⚠️ 本代码仅供参考，不构成投资建议。
