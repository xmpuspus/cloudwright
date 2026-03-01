import React, { useState, useCallback, useRef, useMemo } from "react";

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
}

const TIER_LABELS: Record<number, string> = {
  0: "Edge / CDN",
  1: "Load Balancing",
  2: "Compute",
  3: "Data",
  4: "Supporting",
};

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div
      style={{
        padding: "14px 16px",
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        flex: 1,
        minWidth: 120,
      }}
    >
      <div style={{ fontSize: 22, fontWeight: 700, color: "#0f172a", lineHeight: 1.2 }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{label}</div>
      {sub && (
        <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>{sub}</div>
      )}
    </div>
  );
}

export default function SpecPanel({ spec, yaml }: SpecPanelProps) {
  const [tab, setTab] = useState<TabKey>("overview");
  const [copied, setCopied] = useState(false);
  const preRef = useRef<HTMLPreElement>(null);

  const providers = useMemo(() => {
    const s = new Set(spec.components.map((c) => c.provider));
    return Array.from(s);
  }, [spec.components]);

  const services = useMemo(() => {
    const s = new Set(spec.components.map((c) => c.service));
    return Array.from(s);
  }, [spec.components]);

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
      await navigator.clipboard.writeText(yaml);
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
  }, [yaml]);

  const handleDownload = useCallback(() => {
    const blob = new Blob([yaml], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${spec.name?.replace(/\s+/g, "-").toLowerCase() || "architecture"}.yaml`;
    a.click();
    URL.revokeObjectURL(url);
  }, [yaml, spec.name]);

  return (
    <div style={{ padding: 32, maxWidth: 960 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, color: "#0f172a", fontWeight: 700, margin: 0 }}>
          {spec.name || "Architecture Spec"}
        </h2>
        {spec.provider && (
          <span
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "#475569",
              background: "#f1f5f9",
              padding: "2px 8px",
              borderRadius: 4,
            }}
          >
            {spec.provider.toUpperCase()}
          </span>
        )}
        {spec.region && (
          <span style={{ fontSize: 12, color: "#94a3b8" }}>{spec.region}</span>
        )}
      </div>

      {/* Tab switcher */}
      <div
        style={{
          display: "flex",
          gap: 0,
          marginBottom: 20,
          borderBottom: "1px solid #e2e8f0",
        }}
      >
        {(["overview", "yaml"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "8px 18px",
              background: "none",
              border: "none",
              borderBottom: tab === t ? "2px solid #2563eb" : "2px solid transparent",
              color: tab === t ? "#1d4ed8" : "#64748b",
              fontWeight: tab === t ? 600 : 500,
              fontSize: 13,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            {t === "overview" ? "Overview" : "YAML Source"}
          </button>
        ))}
      </div>

      {/* Overview tab */}
      {tab === "overview" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Stats row */}
          <div style={{ display: "flex", gap: 12 }}>
            <StatCard label="Components" value={spec.components.length} />
            <StatCard label="Connections" value={spec.connections.length} />
            <StatCard
              label="Services"
              value={services.length}
              sub={providers.join(", ")}
            />
            {spec.cost_estimate && (
              <StatCard
                label="Monthly Cost"
                value={`$${spec.cost_estimate.monthly_total.toLocaleString()}`}
                sub={spec.cost_estimate.currency}
              />
            )}
          </div>

          {/* Component table by tier */}
          <div
            style={{
              border: "1px solid #e2e8f0",
              borderRadius: 10,
              overflow: "hidden",
            }}
          >
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f8fafc" }}>
                  <th style={thStyle}>Component</th>
                  <th style={thStyle}>Service</th>
                  <th style={thStyle}>Provider</th>
                  <th style={thStyle}>Tier</th>
                  <th style={thStyle}>Description</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(tierGroups)
                  .map(Number)
                  .sort()
                  .flatMap((tier) =>
                    tierGroups[tier].map((comp) => (
                      <tr
                        key={comp.id}
                        style={{ borderBottom: "1px solid #f1f5f9" }}
                      >
                        <td style={tdStyle}>
                          <span style={{ fontWeight: 600, color: "#0f172a" }}>{comp.label}</span>
                          <div style={{ fontSize: 11, color: "#94a3b8" }}>{comp.id}</div>
                        </td>
                        <td style={tdStyle}>
                          <code
                            style={{
                              fontSize: 12,
                              background: "#f1f5f9",
                              padding: "1px 6px",
                              borderRadius: 3,
                              color: "#334155",
                            }}
                          >
                            {comp.service}
                          </code>
                        </td>
                        <td style={tdStyle}>
                          <span style={{ fontSize: 12, color: "#475569" }}>{comp.provider}</span>
                        </td>
                        <td style={tdStyle}>
                          <span
                            style={{
                              fontSize: 11,
                              fontWeight: 600,
                              color: "#64748b",
                              background: "#f1f5f9",
                              padding: "2px 8px",
                              borderRadius: 4,
                            }}
                          >
                            {TIER_LABELS[tier] || `Tier ${tier}`}
                          </span>
                        </td>
                        <td style={{ ...tdStyle, color: "#64748b", maxWidth: 240 }}>
                          {comp.description}
                        </td>
                      </tr>
                    ))
                  )}
              </tbody>
            </table>
          </div>

          {/* Connections table */}
          {spec.connections.length > 0 && (
            <div
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: 10,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  padding: "10px 16px",
                  background: "#f8fafc",
                  borderBottom: "1px solid #e2e8f0",
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#0f172a",
                }}
              >
                Connections ({spec.connections.length})
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#fafafa" }}>
                    <th style={thStyle}>Source</th>
                    <th style={thStyle}></th>
                    <th style={thStyle}>Target</th>
                    <th style={thStyle}>Protocol</th>
                    <th style={thStyle}>Label</th>
                  </tr>
                </thead>
                <tbody>
                  {spec.connections.map((conn, i) => {
                    const srcComp = spec.components.find((c) => c.id === conn.source);
                    const tgtComp = spec.components.find((c) => c.id === conn.target);
                    return (
                      <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={tdStyle}>
                          <span style={{ fontWeight: 500, color: "#0f172a" }}>
                            {srcComp?.label || conn.source}
                          </span>
                        </td>
                        <td
                          style={{
                            ...tdStyle,
                            textAlign: "center",
                            color: "#94a3b8",
                            fontSize: 14,
                          }}
                        >
                          &#8594;
                        </td>
                        <td style={tdStyle}>
                          <span style={{ fontWeight: 500, color: "#0f172a" }}>
                            {tgtComp?.label || conn.target}
                          </span>
                        </td>
                        <td style={tdStyle}>
                          {conn.protocol && (
                            <code
                              style={{
                                fontSize: 11,
                                background: "#f1f5f9",
                                padding: "1px 6px",
                                borderRadius: 3,
                                color: "#334155",
                              }}
                            >
                              {conn.protocol}
                              {conn.port ? `:${conn.port}` : ""}
                            </code>
                          )}
                        </td>
                        <td style={{ ...tdStyle, color: "#64748b" }}>{conn.label}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Boundaries */}
          {spec.boundaries && spec.boundaries.length > 0 && (
            <div
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: 10,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  padding: "10px 16px",
                  background: "#f8fafc",
                  borderBottom: "1px solid #e2e8f0",
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#0f172a",
                }}
              >
                Boundaries ({spec.boundaries.length})
              </div>
              <div style={{ padding: 16, display: "flex", flexWrap: "wrap", gap: 10 }}>
                {spec.boundaries.map((b) => (
                  <div
                    key={b.id}
                    style={{
                      padding: "8px 14px",
                      border: "1px dashed #cbd5e1",
                      borderRadius: 8,
                      background: "#fafafa",
                      fontSize: 13,
                    }}
                  >
                    <div style={{ fontWeight: 600, color: "#0f172a" }}>
                      {b.label || b.id}
                    </div>
                    <div style={{ fontSize: 11, color: "#94a3b8" }}>
                      {b.kind} &middot; {b.component_ids.length} components
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* YAML tab */}
      {tab === "yaml" && (
        <div
          style={{
            border: "1px solid #e2e8f0",
            borderRadius: 10,
            overflow: "hidden",
          }}
        >
          {/* Toolbar */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "8px 14px",
              background: "#f8fafc",
              borderBottom: "1px solid #e2e8f0",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: "#7c3aed",
                  background: "#7c3aed14",
                  padding: "2px 8px",
                  borderRadius: 4,
                }}
              >
                YAML
              </span>
              <span style={{ fontSize: 12, color: "#64748b" }}>
                {spec.name?.replace(/\s+/g, "-").toLowerCase() || "architecture"}.yaml
              </span>
              <span style={{ fontSize: 11, color: "#cbd5e1" }}>
                {yaml.split("\n").length} lines
              </span>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <button
                onClick={handleCopy}
                style={{
                  padding: "4px 12px",
                  borderRadius: 4,
                  border: "1px solid #e2e8f0",
                  background: copied ? "#dcfce7" : "#ffffff",
                  color: copied ? "#166534" : "#475569",
                  cursor: "pointer",
                  fontSize: 12,
                  fontWeight: 500,
                  transition: "all 0.15s ease",
                }}
              >
                {copied ? "Copied" : "Copy"}
              </button>
              <button
                onClick={handleDownload}
                style={{
                  padding: "4px 12px",
                  borderRadius: 4,
                  border: "1px solid #e2e8f0",
                  background: "#ffffff",
                  color: "#475569",
                  cursor: "pointer",
                  fontSize: 12,
                  fontWeight: 500,
                }}
              >
                Download
              </button>
            </div>
          </div>

          {/* Code */}
          <div style={{ maxHeight: 600, overflow: "auto" }}>
            <pre
              ref={preRef}
              style={{
                margin: 0,
                padding: 16,
                fontSize: 13,
                lineHeight: 1.7,
                color: "#334155",
                background: "#ffffff",
                fontFamily: "'SF Mono', 'Cascadia Code', 'Fira Code', Menlo, monospace",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {yaml || "No YAML available"}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: "10px 14px",
  textAlign: "left",
  fontSize: 11,
  fontWeight: 600,
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const tdStyle: React.CSSProperties = {
  padding: "10px 14px",
  color: "#0f172a",
};
