import React, { useState, useCallback, useRef, useMemo, useEffect } from "react";
import Icon from "./Icon";

interface Component {
  id: string;
  service: string;
  provider: string;
  label: string;
  description: string;
  tier: number;
  config?: Record<string, unknown>;
}

interface Connection {
  source: string;
  target: string;
  label: string;
  protocol?: string;
  port?: number;
}

interface Boundary {
  id: string;
  kind: string;
  label?: string;
  component_ids: string[];
}

interface CostEstimate {
  monthly_total: number;
  currency: string;
}

interface ArchSpec {
  name: string;
  provider?: string;
  region?: string;
  components: Component[];
  connections: Connection[];
  boundaries?: Boundary[];
  cost_estimate?: CostEstimate;
}

type TabKey = "overview" | "yaml";

interface SpecPanelProps {
  spec: ArchSpec;
  yaml: string;
  apiBase: string;
}

const TIER_LABELS: Record<number, string> = {
  0: "Edge / CDN",
  1: "Load Balancing",
  2: "Compute",
  3: "Data",
  4: "Supporting",
};

/** YAML needs a quote around anything that would otherwise parse as another type.
 *  Without this, `region: no` reads back as the boolean false. */
const PLAIN_SAFE = /^[A-Za-z0-9_./:@-]+$/;
const LOOKS_TYPED = /^(true|false|yes|no|on|off|null|~|-?\d+(\.\d+)?([eE][+-]?\d+)?)$/i;

function scalarToYaml(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  const text = String(value);
  if (text === "") return '""';
  if (text.includes("\n")) return JSON.stringify(text);
  if (PLAIN_SAFE.test(text) && !LOOKS_TYPED.test(text) && !text.includes(": ")) return text;
  return JSON.stringify(text);
}

function toYaml(value: unknown, indent = 0): string {
  const pad = " ".repeat(indent);
  if (Array.isArray(value)) {
    if (value.length === 0) return "[]";
    return value
      .map((item) => {
        if (item && typeof item === "object") {
          const nested = toYaml(item, indent + 2);
          return `${pad}- ${nested.trimStart()}`;
        }
        return `${pad}- ${scalarToYaml(item)}`;
      })
      .join("\n");
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).filter(
      ([, item]) => item !== undefined,
    );
    if (entries.length === 0) return "{}";
    return entries
      .map(([key, item]) => {
        if (item && typeof item === "object") {
          const nested = toYaml(item, indent + 2);
          return `${pad}${key}:\n${nested}`;
        }
        return `${pad}${key}: ${scalarToYaml(item)}`;
      })
      .join("\n");
  }
  return scalarToYaml(value);
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="stat">
      <div className="stat__value">{value}</div>
      <div className="stat__label">{label}</div>
      {sub && <div className="stat__sub">{sub}</div>}
    </div>
  );
}

export default function SpecPanel({ spec, yaml, apiBase }: SpecPanelProps) {
  const [tab, setTab] = useState<TabKey>("overview");
  const [copied, setCopied] = useState(false);
  const [serverYaml, setServerYaml] = useState<string | null>(null);
  const [yamlLoading, setYamlLoading] = useState(false);
  const preRef = useRef<HTMLPreElement>(null);

  const fallback = useMemo(() => yaml?.trim() || toYaml(spec), [spec, yaml]);
  const source = serverYaml ?? fallback;

  // The server is the authority on this format. Asking it keeps the tab identical
  // to what `cloudwright export` writes, including after a canvas edit.
  useEffect(() => {
    if (tab !== "yaml") return;
    let cancelled = false;
    setYamlLoading(true);
    fetch(`${apiBase}/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec, format: "yaml" }),
    })
      .then((res) => (res.ok ? res.text() : null))
      .then((text) => {
        if (!cancelled && text) setServerYaml(text);
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setYamlLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tab, spec, apiBase]);

  const providers = useMemo(
    () => Array.from(new Set(spec.components.map((c) => c.provider))),
    [spec.components],
  );
  const services = useMemo(
    () => Array.from(new Set(spec.components.map((c) => c.service))),
    [spec.components],
  );

  const tierGroups = useMemo(() => {
    const groups: Record<number, Component[]> = {};
    for (const c of spec.components) {
      const t = c.tier ?? 2;
      if (!groups[t]) groups[t] = [];
      groups[t].push(c);
    }
    return groups;
  }, [spec.components]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(source);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const el = preRef.current;
      if (el) {
        const range = document.createRange();
        range.selectNodeContents(el);
        window.getSelection()?.removeAllRanges();
        window.getSelection()?.addRange(range);
      }
    }
  }, [source]);

  const handleDownload = useCallback(() => {
    const blob = new Blob([source], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${spec.name?.replace(/\s+/g, "-").toLowerCase() || "architecture"}.yaml`;
    a.click();
    URL.revokeObjectURL(url);
  }, [source, spec.name]);

  return (
    <div className="panel__body panel__body--wide">
      <div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-3)", flexWrap: "wrap", marginBottom: "var(--space-4)" }}>
        <h2 className="panel__title">{spec.name || "Architecture Spec"}</h2>
        {spec.provider && <span className="badge badge--neutral">{spec.provider}</span>}
        {spec.region && <code className="inline">{spec.region}</code>}
      </div>

      <div className="tabs" role="tablist" aria-label="Spec views" style={{ borderBottom: "1px solid var(--border)", marginBottom: "var(--space-5)", padding: 0 }}>
        {(["overview", "yaml"] as const).map((t) => (
          <button
            key={t}
            className="tab"
            role="tab"
            aria-selected={tab === t}
            tabIndex={tab === t ? 0 : -1}
            onClick={() => setTab(t)}
            style={{ minHeight: 38, textTransform: "none" }}
          >
            {t === "overview" ? "Overview" : "YAML Source"}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
          <div className="stat-grid">
            <StatCard label="Components" value={spec.components.length} />
            <StatCard label="Connections" value={spec.connections.length} />
            <StatCard label="Distinct services" value={services.length} sub={providers.join(", ")} />
            {spec.cost_estimate && (
              <StatCard
                label="Monthly cost"
                value={`$${spec.cost_estimate.monthly_total.toLocaleString()}`}
                sub={spec.cost_estimate.currency}
              />
            )}
          </div>

          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">Component</th>
                  <th scope="col">Service</th>
                  <th scope="col">Provider</th>
                  <th scope="col">Tier</th>
                  <th scope="col">Description</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(tierGroups)
                  .map(Number)
                  .sort()
                  .flatMap((tier) =>
                    tierGroups[tier].map((comp) => (
                      <tr key={comp.id}>
                        <td>
                          <span style={{ fontWeight: 600 }}>{comp.label}</span>
                          <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>{comp.id}</div>
                        </td>
                        <td><code className="inline">{comp.service}</code></td>
                        <td style={{ color: "var(--text-muted)" }}>{comp.provider}</td>
                        <td><span className="badge badge--neutral">{TIER_LABELS[tier] || `Tier ${tier}`}</span></td>
                        <td style={{ color: "var(--text-muted)", maxWidth: 280 }}>{comp.description}</td>
                      </tr>
                    )),
                  )}
              </tbody>
            </table>
          </div>

          {spec.connections.length > 0 && (
            <div className="card">
              <div className="card__header">Connections ({spec.connections.length})</div>
              <table className="data">
                <thead>
                  <tr>
                    <th scope="col">Source</th>
                    <th scope="col">Target</th>
                    <th scope="col">Protocol</th>
                    <th scope="col">Label</th>
                  </tr>
                </thead>
                <tbody>
                  {spec.connections.map((conn, i) => {
                    const srcComp = spec.components.find((c) => c.id === conn.source);
                    const tgtComp = spec.components.find((c) => c.id === conn.target);
                    return (
                      <tr key={i}>
                        <td style={{ fontWeight: 550 }}>{srcComp?.label || conn.source}</td>
                        <td style={{ fontWeight: 550 }}>{tgtComp?.label || conn.target}</td>
                        <td>
                          {conn.protocol && (
                            <code className="inline">
                              {conn.protocol}
                              {conn.port ? `:${conn.port}` : ""}
                            </code>
                          )}
                        </td>
                        <td style={{ color: "var(--text-muted)" }}>{conn.label}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {spec.boundaries && spec.boundaries.length > 0 && (
            <div className="card">
              <div className="card__header">Boundaries ({spec.boundaries.length})</div>
              <div className="card__body" style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
                {spec.boundaries.map((b) => (
                  <div
                    key={b.id}
                    style={{
                      padding: "8px 14px",
                      border: "1px dashed var(--border-strong)",
                      borderRadius: "var(--radius)",
                      background: "var(--bg-subtle)",
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: "var(--text-base)" }}>{b.label || b.id}</div>
                    <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>
                      {b.kind}, {b.component_ids.length} components
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "yaml" && (
        <div className="card">
          <div className="card__header">
            <span style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", minWidth: 0 }}>
              <code className="inline">
                {spec.name?.replace(/\s+/g, "-").toLowerCase() || "architecture"}.yaml
              </code>
              <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>
                {source.split("\n").length} lines
                {yamlLoading ? ", refreshing" : serverYaml ? ", from the server" : ""}
              </span>
            </span>
            <span style={{ display: "flex", gap: "var(--space-2)" }}>
              <button className="btn btn--sm" onClick={handleCopy}>
                <Icon name={copied ? "check" : "copy"} size={13} />
                {copied ? "Copied" : "Copy"}
              </button>
              <button className="btn btn--sm" onClick={handleDownload}>
                <Icon name="download" size={13} />
                Download
              </button>
            </span>
          </div>
          <div style={{ maxHeight: "62vh", overflow: "auto" }}>
            <pre ref={preRef} className="code-block">
              {source || "No YAML available"}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
