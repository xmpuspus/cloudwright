"""Self-contained HTML architecture report.

Generates a single HTML file with embedded styles and a Mermaid diagram
that can be shared via email, Slack, or GitHub Gist.
"""

from __future__ import annotations

import html as html_mod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec


def render(spec: "ArchSpec") -> str:
    """Render a self-contained HTML report for the given ArchSpec."""
    from cloudwright.exporter.mermaid import render as mermaid_render

    mermaid_source = mermaid_render(spec)
    # Remove the Cloudwright attribution from the embedded mermaid
    # (it's already in the HTML footer)
    mermaid_source = mermaid_source.replace(
        "%% Designed with Cloudwright (https://github.com/xmpuspus/cloudwright)\n", ""
    )

    # Build component inventory rows
    comp_rows = ""
    for c in spec.components:
        comp_rows += f"<tr><td>{html_mod.escape(c.label)}</td><td><code>{html_mod.escape(c.service)}</code></td><td>{html_mod.escape(c.provider.upper())}</td><td>{c.tier}</td><td>{html_mod.escape(c.description or '')}</td></tr>\n"

    # Build cost rows
    cost_rows = ""
    cost_total = 0.0
    if spec.cost_estimate:
        for item in spec.cost_estimate.breakdown:
            cost_rows += f"<tr><td>{html_mod.escape(item.component_id)}</td><td>{html_mod.escape(item.service)}</td><td class='cost'>${item.monthly:,.2f}</td><td>{html_mod.escape(item.notes or '')}</td></tr>\n"
            cost_total = spec.cost_estimate.monthly_total

    # Build connections rows
    conn_rows = ""
    for conn in spec.connections:
        protocol = f"{conn.protocol or ''}"
        if conn.port:
            protocol += f":{conn.port}"
        conn_rows += f"<tr><td>{html_mod.escape(conn.source)}</td><td>&rarr;</td><td>{html_mod.escape(conn.target)}</td><td><code>{html_mod.escape(protocol)}</code></td></tr>\n"

    cost_section = ""
    if spec.cost_estimate:
        cost_section = f"""
        <section>
            <h2>Cost Estimate</h2>
            <div class="stat-bar">
                <div class="stat">Monthly Total: <strong>${cost_total:,.2f}</strong></div>
                <div class="stat">Components: <strong>{len(spec.components)}</strong></div>
                <div class="stat">Provider: <strong>{spec.provider.upper()}</strong></div>
            </div>
            <table>
                <thead><tr><th>Component</th><th>Service</th><th>Monthly</th><th>Notes</th></tr></thead>
                <tbody>{cost_rows}</tbody>
                <tfoot><tr><td colspan="2"><strong>Total</strong></td><td class="cost"><strong>${cost_total:,.2f}</strong></td><td></td></tr></tfoot>
            </table>
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_mod.escape(spec.name)} - Architecture Report</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; background: #0f172a; color: #e2e8f0; line-height: 1.6; }}
.container {{ max-width: 1100px; margin: 0 auto; padding: 2rem; }}
h1 {{ font-size: 1.75rem; color: #f8fafc; margin-bottom: 0.25rem; }}
h2 {{ font-size: 1.25rem; color: #f8fafc; margin: 2rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #334155; }}
.subtitle {{ color: #94a3b8; font-size: 0.875rem; margin-bottom: 1.5rem; }}
.stat-bar {{ display: flex; gap: 1.5rem; margin-bottom: 1rem; flex-wrap: wrap; }}
.stat {{ background: #1e293b; padding: 0.5rem 1rem; border-radius: 0.5rem; font-size: 0.875rem; color: #94a3b8; }}
.stat strong {{ color: #60a5fa; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 1rem; font-size: 0.875rem; }}
th {{ text-align: left; padding: 0.75rem; background: #1e293b; color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
td {{ padding: 0.75rem; border-bottom: 1px solid #1e293b; color: #cbd5e1; }}
td code {{ background: #1e293b; padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-size: 0.8125rem; color: #93c5fd; }}
td.cost {{ font-family: 'SF Mono', Menlo, monospace; color: #60a5fa; text-align: right; }}
th:nth-child(3) {{ text-align: right; }}
tfoot td {{ border-top: 2px solid #334155; }}
.mermaid {{ background: #1e293b; border-radius: 0.75rem; padding: 1.5rem; margin: 1rem 0; text-align: center; }}
.footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #334155; color: #64748b; font-size: 0.75rem; text-align: center; }}
.footer a {{ color: #60a5fa; text-decoration: none; }}
section {{ margin-bottom: 2rem; }}
</style>
</head>
<body>
<div class="container">
    <h1>{html_mod.escape(spec.name)}</h1>
    <div class="subtitle">{html_mod.escape(spec.provider.upper())} / {html_mod.escape(spec.region)} - {len(spec.components)} components, {len(spec.connections)} connections</div>

    <section>
        <h2>Architecture Diagram</h2>
        <div class="mermaid">
{html_mod.escape(mermaid_source)}
        </div>
    </section>

    {cost_section}

    <section>
        <h2>Components</h2>
        <table>
            <thead><tr><th>Label</th><th>Service</th><th>Provider</th><th>Tier</th><th>Description</th></tr></thead>
            <tbody>{comp_rows}</tbody>
        </table>
    </section>

    <section>
        <h2>Connections</h2>
        <table>
            <thead><tr><th>Source</th><th></th><th>Target</th><th>Protocol</th></tr></thead>
            <tbody>{conn_rows}</tbody>
        </table>
    </section>

    <div class="footer">
        Designed with <a href="https://github.com/xmpuspus/cloudwright">Cloudwright</a> - Architecture Intelligence for Cloud Engineers
    </div>
</div>
<script>mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});</script>
</body>
</html>"""
