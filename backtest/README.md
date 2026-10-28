# 回测模块（backtest/）

通用事件/规则回测引擎与两个示例策略。

## 结构

- `engine.py`：行情获取（`westock-data`）、Markdown 解析、事件收益计算、统计。已规避前视偏差（买点用事件后首交易日开盘）。
- `event_study.py`：示例——央行降息后持有沪深300ETF(510300) 20 个交易日的事件研究。
- `strategy_lowvol.py`：示例——月度低波选股（**合成数据可跑版**），演示组合层指标（年化/夏普/最大回撤）。
- `dashboard.py`：自包含 HTML 看板（无外部 CDN）。

## 运行

```bash
# 事件研究（需 westock-data；本机可用 WESTOCK_BIN 指定）
export WESTOCK_BIN="node /path/to/westock-data/scripts/index.js"
python -m backtest.event_study

# 低波选股（纯合成数据，无需网络）
python -m backtest.strategy_lowvol
```

## 输出

- `backtest/output/pbc_cut_csi300_trades.csv` / `_summary.json`
- `backtest/output/lowvol_equity.csv` / `_summary.json`

## 验证状态

- `event_study.py` 已用 westock-data 实跑，9 个事件全部出数。
- `strategy_lowvol.py` 纯 numpy/pandas，可离线运行。
- 本环境无 PyPI 网络，未安装 pandas/numpy 时无法在此重跑；代码已通过 `py_compile` 语法校验。

## 范围与偏差提示

- 单标的、单事件独立统计，不构造组合，避免幸存者偏差。
- 默认不计交易成本（事件研究惯例）；实盘应计入印花税/佣金/滑点。
- 样本仅 9 次，均值对极端事件（如 "924"）高度敏感，须看中位数与分布。

> ⚠️ 回测结果由模型驱动，仅供研究参考，不构成投资建议。
