"""自包含 HTML 看板生成（无外部 CDN，离线可用）。"""
from __future__ import annotations

import html
import os


def build_event_dashboard(summary: dict, out_path: str) -> str:
    stats = summary.get("stats", {})
    trades = summary.get("trades", [])
    cards = [
        ("事件数", stats.get("n", "-")),
        ("平均收益", f"{stats.get('mean_pct', 0):+.2f}%"),
        ("中位数", f"{stats.get('median_pct', 0):+.2f}%"),
        ("胜率", f"{stats.get('win_rate', 0)}%"),
        ("最佳", f"{stats.get('best_pct', 0):+.2f}%"),
        ("最差", f"{stats.get('worst_pct', 0):+.2f}%"),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="k">{html.escape(str(k))}</div><div class="v">{html.escape(str(v))}</div></div>'
        for k, v in cards
    )
    rows = "".join(
        f"<tr><td>{html.escape(str(t.get('event_date','')))}</td>"
        f"<td>{html.escape(str(t.get('label','')))}</td>"
        f"<td>{html.escape(str(t.get('buy_date','')))}→{html.escape(str(t.get('sell_date','')))}</td>"
        f"<td class=\"{'pos' if t.get('pnl_pct',0)>=0 else 'neg'}\">{t.get('pnl_pct',0):+.2f}%</td></tr>"
        for t in trades
    )
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>事件研究看板</title></head>
<body>
<h1>央行降息事件研究看板</h1>
<div class="kpis">{cards_html}</div>
<table><thead><tr><th>事件日</th><th>说明</th><th>买卖区间</th><th>20日收益</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="note">买入：事件后下一交易日开盘；卖出：持有20交易日后收盘。无费用。仅模型结果，非投资建议。</p>
</body></html>
<style>
body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:24px;color:#0f172a;background:#f8fafc}}
h1{{font-size:18px}}
.kpis{{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 18px;min-width:110px}}
.card .k{{font-size:12px;color:#64748b}}
.card .v{{font-size:20px;font-weight:600;margin-top:4px}}
table{{width:100%;border-collapse:collapse;margin-top:8px;background:#fff}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #e2e8f0;font-size:14px}}
th{{color:#64748b;font-weight:500}}
.pos{{color:#dc2626}}
.neg{{color:#16a34a}}
.note{{font-size:12px;color:#94a3b8;margin-top:16px}}
</style>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path
