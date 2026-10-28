# 数据基建（data/）

把行情数据从第三方接口拉取并落库到本地 DuckDB，供回测与研究中直接 SQL 查询。

## 设计

- `fetch.py`：行情拉取层。封装 AkShare，统一规范化列，带退避重试。
- `store.py`：DuckDB 存储层。表 `daily(code, date, open, high, low, close, volume, amount, adj_close)`，
  按 `(code, date)` 主键 `INSERT OR REPLACE`，天然支持增量更新去重。
- `cli.py`：命令行入口，支持 `demo` / `fetch` / `query`。

## 快速开始

```bash
pip install -r requirements.txt

# 1) 无网络自测存储层（生成合成数据写入并回查）
python -m data.cli demo

# 2) 拉取真实日线并入库（需网络 + akshare）
python -m data.cli fetch --code 600519.SH --start 2024-01-01 --end 2024-12-31

# 3) 查询
python -m data.cli query --code 600519.SH
```

## 测试

```bash
pytest tests/test_store.py
```

## 注意

- 本 PR 仅覆盖**日线**行情基建。分钟/tick 不在范围内。
- 真实环境建议改用 Parquet 分区 + DuckDB 外表以承载全市场历史，避免单文件过大。
- `fetch_index_universe()` 目前返回常用指数占位，真实成分用 `ak.index_stock_cons` 接入。
