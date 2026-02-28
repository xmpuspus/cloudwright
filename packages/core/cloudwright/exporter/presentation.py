"""Architecture presentation/deck exporter.

Generates a multi-page HTML document (convertible to PDF via WeasyPrint)
with overview diagram, component inventory, cost breakdown, compliance
summary, and network topology.
"""

from __future__ import annotations

import html
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_TIER_NAMES = {
    0: "Edge / CDN",
    1: "Ingress",
    2: "Compute",
    3: "Data",
    4: "AI / ML",
    5: "Observability",
}

_CSS = """
@page {
    size: A4 landscape;
    margin: 0;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: #0f172a;
    color: #f8fafc;
    font-size: 13px;
    line-height: 1.5;
}

.page {
    width: 297mm;
    min-height: 210mm;
    padding: 12mm 14mm;
    page-break-after: always;
    page-break-inside: avoid;
    background: #0f172a;
    display: flex;
    flex-direction: column;
}

.page:last-child {
    page-break-after: auto;
}

/* ---- Title page ---- */

.title-page {
    justify-content: center;
    gap: 8mm;
}

.title-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    border-bottom: 2px solid #10b981;
    padding-bottom: 6mm;
    margin-bottom: 6mm;
}

.arch-name {
    font-size: 28px;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: -0.5px;
}

.arch-subtitle {
    font-size: 13px;
    color: #94a3b8;
    margin-top: 4px;
}

.provider-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.badge-aws    { background: #f59e0b; color: #1c1917; }
.badge-gcp    { background: #3b82f6; color: #fff; }
.badge-azure  { background: #0078d4; color: #fff; }
.badge-other  { background: #64748b; color: #f8fafc; }

.title-meta {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
}

.meta-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.meta-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #64748b;
}

.meta-value {
    font-size: 14px;
    font-weight: 600;
    color: #e2e8f0;
}

.meta-value-accent {
    color: #10b981;
}

.diagram-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #1e293b;
    border-radius: 8px;
    padding: 8mm;
    min-height: 60mm;
    overflow: hidden;
}

.diagram-container svg {
    max-width: 100%;
    max-height: 100mm;
}

.no-diagram {
    color: #475569;
    font-size: 12px;
    text-align: center;
}

/* ---- Section pages ---- */

.page-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6mm;
    padding-bottom: 3mm;
    border-bottom: 1px solid #1e293b;
}

.section-tag {
    background: #10b981;
    color: #0f172a;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 2px 8px;
    border-radius: 3px;
}

.section-title {
    font-size: 18px;
    font-weight: 700;
    color: #f8fafc;
}

/* ---- Tables ---- */

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}

thead th {
    background: #1e293b;
    color: #94a3b8;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-weight: 600;
    padding: 6px 10px;
    text-align: left;
    border-bottom: 1px solid #334155;
}

tbody tr:nth-child(even) {
    background: #0f1d30;
}

tbody tr:nth-child(odd) {
    background: #0f172a;
}

tbody tr:hover {
    background: #1e293b;
}

td {
    padding: 6px 10px;
    border-bottom: 1px solid #1e293b;
    color: #e2e8f0;
    vertical-align: top;
}

.tier-group-header td {
    background: #1e293b;
    color: #10b981;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    padding: 4px 10px;
}

.tag {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
}

.tag-aws    { background: #78350f; color: #fde68a; }
.tag-gcp    { background: #1e3a5f; color: #93c5fd; }
.tag-azure  { background: #1e3a5f; color: #93c5fd; }
.tag-other  { background: #1e293b; color: #94a3b8; }

.config-cell {
    font-family: 'Menlo', 'Consolas', monospace;
    font-size: 11px;
    color: #94a3b8;
}

/* ---- Cost bar chart ---- */

.cost-bar-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
}

.cost-bar-bg {
    flex: 1;
    background: #1e293b;
    border-radius: 2px;
    height: 8px;
    overflow: hidden;
}

.cost-bar-fill {
    height: 100%;
    background: #10b981;
    border-radius: 2px;
}

.cost-total-row td {
    background: #1e293b;
    color: #10b981;
    font-weight: 700;
    border-top: 2px solid #10b981;
}

.cost-amount {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
}

/* ---- Config details ---- */

.config-block {
    background: #1e293b;
    border-radius: 6px;
    padding: 8px 12px;
    margin-bottom: 6px;
}

.config-block-title {
    font-size: 12px;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 4px;
}

.config-block-sub {
    font-size: 10px;
    color: #64748b;
    margin-bottom: 6px;
}

.config-kv-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 4px 12px;
}

.config-kv {
    display: flex;
    flex-direction: column;
    gap: 1px;
}

.config-key {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #64748b;
}

.config-val {
    font-size: 11px;
    font-family: 'Menlo', 'Consolas', monospace;
    color: #a5f3fc;
    word-break: break-all;
}

/* ---- Footer ---- */

.page-footer {
    margin-top: auto;
    padding-top: 4mm;
    border-top: 1px solid #1e293b;
    display: flex;
    justify-content: space-between;
    color: #475569;
    font-size: 10px;
}
"""


def _badge_class(provider: str) -> str:
    p = provider.lower()
    if p == "aws":
        return "badge-aws"
    if p == "gcp":
        return "badge-gcp"
    if p == "azure":
        return "badge-azure"
    return "badge-other"


def _tag_class(provider: str) -> str:
    p = provider.lower()
    if p == "aws":
        return "tag-aws"
    if p == "gcp":
        return "tag-gcp"
    if p == "azure":
        return "tag-azure"
    return "tag-other"


def _fmt_config(cfg: dict) -> str:
    if not cfg:
        return ""
    parts = []
    for k, v in cfg.items():
        parts.append(f"{html.escape(str(k))}: {html.escape(str(v))}")
    return ", ".join(parts)


def _title_page(spec: "ArchSpec", svg: str | None) -> str:
    today = date.today().isoformat()
    n_components = len(spec.components)
    provider = spec.provider.upper()
    badge_cls = _badge_class(spec.provider)

    cost_html = ""
    if spec.cost_estimate:
        total = spec.cost_estimate.monthly_total
        cost_html = f"""
        <div class="meta-item">
            <span class="meta-label">Monthly Cost</span>
            <span class="meta-value meta-value-accent">${total:,.2f}</span>
        </div>"""

    diagram_html = ""
    if svg:
        diagram_html = f'<div class="diagram-container">{svg}</div>'
    else:
        diagram_html = '<div class="diagram-container"><span class="no-diagram">No diagram provided</span></div>'

    return f"""
<div class="page title-page">
    <div class="title-header">
        <div>
            <div class="arch-name">{html.escape(spec.name)}</div>
            <div class="arch-subtitle">Architecture Specification &mdash; {html.escape(spec.region)}</div>
        </div>
        <span class="provider-badge {badge_cls}">{html.escape(provider)}</span>
    </div>
    <div class="title-meta">
        <div class="meta-item">
            <span class="meta-label">Provider</span>
            <span class="meta-value">{html.escape(spec.provider)}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Region</span>
            <span class="meta-value">{html.escape(spec.region)}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Components</span>
            <span class="meta-value">{n_components}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Connections</span>
            <span class="meta-value">{len(spec.connections)}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Generated</span>
            <span class="meta-value">{today}</span>
        </div>
        {cost_html}
    </div>
    {diagram_html}
    <div class="page-footer">
        <span>Cloudwright Architecture Intelligence</span>
        <span>{html.escape(spec.name)} &middot; {today}</span>
    </div>
</div>"""


def _component_inventory_page(spec: "ArchSpec") -> str:
    from itertools import groupby

    by_tier = sorted(spec.components, key=lambda c: c.tier)
    rows = []
    for tier, group in groupby(by_tier, key=lambda c: c.tier):
        tier_label = _TIER_NAMES.get(tier, f"Tier {tier}")
        rows.append(f'<tr class="tier-group-header"><td colspan="5">{html.escape(tier_label)}</td></tr>')
        for c in group:
            tag_cls = _tag_class(c.provider)
            cfg_str = _fmt_config(c.config)
            rows.append(f"""<tr>
                <td><strong>{html.escape(c.label)}</strong><br><span style="color:#64748b;font-size:10px">{html.escape(c.id)}</span></td>
                <td>{html.escape(c.service)}</td>
                <td><span class="tag {tag_cls}">{html.escape(c.provider)}</span></td>
                <td>{tier}</td>
                <td class="config-cell">{cfg_str}</td>
            </tr>""")

    rows_html = "\n".join(rows)
    return f"""
<div class="page">
    <div class="page-header">
        <span class="section-tag">02</span>
        <span class="section-title">Component Inventory</span>
    </div>
    <table>
        <thead>
            <tr>
                <th>Label / ID</th>
                <th>Service</th>
                <th>Provider</th>
                <th>Tier</th>
                <th>Config</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    <div class="page-footer">
        <span>Component Inventory</span>
        <span>{len(spec.components)} components</span>
    </div>
</div>"""


def _cost_breakdown_page(spec: "ArchSpec") -> str:
    ce = spec.cost_estimate
    if not ce or not ce.breakdown:
        return ""

    max_cost = max((item.monthly for item in ce.breakdown), default=1) or 1
    rows = []
    for item in ce.breakdown:
        pct = min(int(item.monthly / max_cost * 100), 100)
        bar_html = f"""<div class="cost-bar-wrap">
            <span class="cost-amount">${item.monthly:,.2f}</span>
            <div class="cost-bar-bg"><div class="cost-bar-fill" style="width:{pct}%"></div></div>
        </div>"""
        comp_id = html.escape(item.component_id)
        rows.append(f"""<tr>
            <td>{comp_id}</td>
            <td>{html.escape(item.service)}</td>
            <td>{bar_html}</td>
        </tr>""")

    # data transfer row if non-zero
    if ce.data_transfer_monthly:
        dt = ce.data_transfer_monthly
        pct = min(int(dt / max_cost * 100), 100)
        bar_html = f"""<div class="cost-bar-wrap">
            <span class="cost-amount">${dt:,.2f}</span>
            <div class="cost-bar-bg"><div class="cost-bar-fill" style="width:{pct}%"></div></div>
        </div>"""
        rows.append(f"""<tr>
            <td colspan="2" style="color:#64748b">Data Transfer</td>
            <td>{bar_html}</td>
        </tr>""")

    rows.append(f"""<tr class="cost-total-row">
        <td colspan="2">Total Monthly</td>
        <td><span class="cost-amount">${ce.monthly_total:,.2f} {html.escape(ce.currency)}</span></td>
    </tr>""")

    rows_html = "\n".join(rows)
    return f"""
<div class="page">
    <div class="page-header">
        <span class="section-tag">03</span>
        <span class="section-title">Cost Breakdown</span>
    </div>
    <table>
        <thead>
            <tr>
                <th>Component</th>
                <th>Service</th>
                <th>Monthly Cost</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    <div class="page-footer">
        <span>Cost Breakdown</span>
        <span>As of {html.escape(ce.as_of)} &middot; {html.escape(ce.currency)}</span>
    </div>
</div>"""


def _network_topology_page(spec: "ArchSpec") -> str:
    if not spec.connections:
        return ""

    comp_label = {c.id: c.label for c in spec.components}
    rows = []
    for conn in spec.connections:
        src_label = comp_label.get(conn.source, conn.source)
        tgt_label = comp_label.get(conn.target, conn.target)
        proto = html.escape(conn.protocol or "")
        port = str(conn.port) if conn.port else ""
        label = html.escape(conn.label or "")
        rows.append(f"""<tr>
            <td>{html.escape(src_label)}</td>
            <td style="color:#64748b;text-align:center">&rarr;</td>
            <td>{html.escape(tgt_label)}</td>
            <td>{proto}</td>
            <td>{port}</td>
            <td>{label}</td>
        </tr>""")

    rows_html = "\n".join(rows)
    return f"""
<div class="page">
    <div class="page-header">
        <span class="section-tag">04</span>
        <span class="section-title">Network Topology</span>
    </div>
    <table>
        <thead>
            <tr>
                <th>Source</th>
                <th></th>
                <th>Target</th>
                <th>Protocol</th>
                <th>Port</th>
                <th>Label</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    <div class="page-footer">
        <span>Network Topology</span>
        <span>{len(spec.connections)} connections</span>
    </div>
</div>"""


def _config_details_page(spec: "ArchSpec") -> str:
    if not spec.components:
        return ""

    blocks = []
    for c in spec.components:
        tier_label = _TIER_NAMES.get(c.tier, f"Tier {c.tier}")
        tag_cls = _tag_class(c.provider)
        kv_items = ""
        if c.config:
            kv_pairs = []
            for k, v in c.config.items():
                kv_pairs.append(f"""<div class="config-kv">
                    <span class="config-key">{html.escape(str(k))}</span>
                    <span class="config-val">{html.escape(str(v))}</span>
                </div>""")
            kv_items = f'<div class="config-kv-grid">{"".join(kv_pairs)}</div>'
        else:
            kv_items = '<span style="color:#475569;font-size:11px">No configuration</span>'

        desc_html = f'<div class="config-block-sub">{html.escape(c.description)}</div>' if c.description else ""
        blocks.append(f"""<div class="config-block">
            <div class="config-block-title">
                {html.escape(c.label)}
                <span style="font-weight:400;color:#64748b;font-size:11px;margin-left:8px">{html.escape(c.id)}</span>
                <span class="tag {tag_cls}" style="margin-left:8px">{html.escape(c.service)}</span>
                <span style="color:#64748b;font-size:10px;margin-left:8px">{html.escape(tier_label)}</span>
            </div>
            {desc_html}
            {kv_items}
        </div>""")

    return f"""
<div class="page">
    <div class="page-header">
        <span class="section-tag">05</span>
        <span class="section-title">Configuration Details</span>
    </div>
    {"".join(blocks)}
    <div class="page-footer">
        <span>Configuration Details</span>
        <span>{len(spec.components)} components</span>
    </div>
</div>"""


def render_html(spec: "ArchSpec", *, include_diagram_svg: str | None = None) -> str:
    """Render a multi-page HTML presentation for an ArchSpec.

    Pages:
    1. Title + overview diagram (SVG embedded if provided)
    2. Component inventory table
    3. Cost breakdown (if cost_estimate present)
    4. Network topology (connections table)
    5. Configuration details

    Args:
        spec: The architecture specification.
        include_diagram_svg: Optional SVG string to embed on title page.

    Returns:
        HTML string suitable for browser viewing or WeasyPrint PDF conversion.
    """
    pages = [
        _title_page(spec, include_diagram_svg),
        _component_inventory_page(spec),
        _cost_breakdown_page(spec),
        _network_topology_page(spec),
        _config_details_page(spec),
    ]
    body = "\n".join(p for p in pages if p)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(spec.name)} — Architecture Deck</title>
<style>
{_CSS}
</style>
</head>
<body>
{body}
</body>
</html>"""


def render_pdf(spec: "ArchSpec", *, include_diagram_svg: str | None = None) -> bytes:
    """Render the presentation as a PDF. Requires weasyprint.

    Raises:
        ImportError: If weasyprint is not installed.
    """
    try:
        from weasyprint import HTML
    except ImportError:
        raise ImportError("weasyprint is required for PDF export. Install: pip install 'cloudwright-ai[pdf]'")
    html_content = render_html(spec, include_diagram_svg=include_diagram_svg)
    doc = HTML(string=html_content)
    return doc.write_pdf()
