import React, { useState, useCallback } from "react";
import { parseApiError } from "../lib/apiError";

interface ControlRef {
  framework: string;
  control_id: string;
  title: string;
}

interface Finding {
  severity: string;
  rule: string;
  component_id: string | null;
  message: string;
  remediation: string;
  source: string;
  category: string | null;
  controls: ControlRef[];
}

interface FrameworkSummary {
  framework: string;
  controls_total: number;
  controls_satisfied: number;
  controls_violated: string[];
  findings: number;
  status: string;
}

interface ComplianceReport {
  passed: boolean;
  scanner: string;
  checkov_used: boolean;
  findings: Finding[];
  frameworks: FrameworkSummary[];
  oscal?: Record<string, unknown>;
}

interface CompliancePanelProps {
  spec: Record<string, unknown>;
  apiBase: string;
}

const FRAMEWORKS = [
  { key: "hipaa", label: "HIPAA" },
  { key: "soc2", label: "SOC 2" },
  { key: "pci-dss", label: "PCI-DSS" },
  { key: "fedramp", label: "FedRAMP" },
  { key: "gdpr", label: "GDPR" },
  { key: "iso27001", label: "ISO 27001" },
  { key: "nist", label: "NIST 800-53" },
];

const SEV_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  critical: { bg: "#fef2f2", text: "#991b1b", border: "#fca5a5" },
  high: { bg: "#fff7ed", text: "#9a3412", border: "#fdba74" },
  medium: { bg: "#fffbeb", text: "#92400e", border: "#fcd34d" },
  low: { bg: "#f0fdf4", text: "#166534", border: "#86efac" },
};

export default function CompliancePanel({ spec, apiBase }: CompliancePanelProps) {
  const [selected, setSelected] = useState<string[]>(["hipaa", "soc2", "fedramp"]);
  const [includeOscal, setIncludeOscal] = useState(false);
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = (k: string) =>
    setSelected((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k]));

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/compliance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spec, frameworks: selected, oscal: includeOscal }),
      });
      if (!res.ok) throw new Error(await parseApiError(res));
      setReport((await res.json()) as ComplianceReport);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Compliance scan failed");
    } finally {
      setLoading(false);
    }
  }, [spec, apiBase, selected, includeOscal]);

  const downloadOscal = useCallback(() => {
    if (!report?.oscal) return;
    const blob = new Blob([JSON.stringify(report.oscal, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "compliance.oscal.json";
    a.click();
    URL.revokeObjectURL(url);
  }, [report]);

  return (
    <div style={{ padding: 24, maxWidth: 920 }}>
      <h2 style={{ fontSize: 18, marginBottom: 6, color: "#0f172a" }}>
        Compliance Control Mapping
      </h2>
      <p style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>
        Every design-stage finding mapped to the framework control it violates — before any
        infrastructure exists. Folds in a Checkov deep scan when available.
      </p>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        {FRAMEWORKS.map((f) => (
          <button
            key={f.key}
            onClick={() => toggle(f.key)}
            style={{
              padding: "6px 14px",
              borderRadius: 999,
              border: `1px solid ${selected.includes(f.key) ? "#2563eb" : "#cbd5e1"}`,
              background: selected.includes(f.key) ? "#2563eb" : "#ffffff",
              color: selected.includes(f.key) ? "#ffffff" : "#475569",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      <label
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 13,
          color: "#334155",
          marginBottom: 16,
        }}
      >
        <input
          type="checkbox"
          checked={includeOscal}
          onChange={(e) => setIncludeOscal(e.target.checked)}
        />
        Include OSCAL 1.1.2 component-definition export
      </label>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={run}
          disabled={loading || selected.length === 0}
          style={{
            padding: "10px 22px",
            borderRadius: 8,
            border: "none",
            background: loading ? "#94a3b8" : "#0f172a",
            color: "#ffffff",
            fontSize: 14,
            fontWeight: 600,
            cursor: loading ? "default" : "pointer",
          }}
        >
          {loading ? "Scanning…" : "Run compliance scan"}
        </button>

        {report?.oscal && (
          <button
            onClick={downloadOscal}
            style={{
              padding: "10px 22px",
              borderRadius: 8,
              border: "1px solid #2563eb",
              background: "#ffffff",
              color: "#2563eb",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Download OSCAL JSON
          </button>
        )}
      </div>

      {error && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            background: "#fef2f2",
            border: "1px solid #fca5a5",
            borderRadius: 8,
            color: "#991b1b",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      {report && (
        <div style={{ marginTop: 24 }}>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>
            Scanner: <strong>{report.scanner}</strong>
            {report.checkov_used ? " (Checkov deep scan included)" : ""}
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 24 }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={th}>Framework</th>
                <th style={th}>Controls satisfied</th>
                <th style={th}>Violated</th>
                <th style={th}>Findings</th>
                <th style={th}>Status</th>
              </tr>
            </thead>
            <tbody>
              {report.frameworks.map((s) => (
                <tr key={s.framework} style={{ borderTop: "1px solid #e2e8f0" }}>
                  <td style={td}>
                    <strong>{s.framework}</strong>
                  </td>
                  <td style={td}>
                    {s.controls_satisfied}/{s.controls_total}
                  </td>
                  <td style={{ ...td, color: "#991b1b" }}>
                    {s.controls_violated.length ? s.controls_violated.join(", ") : "—"}
                  </td>
                  <td style={td}>{s.findings}</td>
                  <td style={td}>
                    <span
                      style={{
                        padding: "2px 10px",
                        borderRadius: 999,
                        fontSize: 12,
                        fontWeight: 600,
                        background: s.status === "pass" ? "#dcfce7" : "#fee2e2",
                        color: s.status === "pass" ? "#166534" : "#991b1b",
                      }}
                    >
                      {s.status.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3 style={{ fontSize: 15, color: "#0f172a", marginBottom: 12 }}>
            Findings ({report.findings.length})
          </h3>
          {report.findings.map((f, i) => {
            const c = SEV_COLORS[f.severity] || SEV_COLORS.low;
            return (
              <div
                key={i}
                style={{
                  border: `1px solid ${c.border}`,
                  background: c.bg,
                  borderRadius: 8,
                  padding: 14,
                  marginBottom: 10,
                }}
              >
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: c.text,
                      textTransform: "uppercase",
                    }}
                  >
                    [{f.severity}]
                  </span>
                  <span style={{ fontSize: 14, color: "#0f172a" }}>{f.message}</span>
                  <span style={{ fontSize: 11, color: "#64748b" }}>({f.source})</span>
                </div>
                {f.controls.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                    {f.controls.map((ctrl, j) => (
                      <span
                        key={j}
                        title={ctrl.title}
                        style={{
                          fontSize: 11,
                          padding: "2px 8px",
                          borderRadius: 4,
                          background: "#e0e7ff",
                          color: "#3730a3",
                          fontFamily: "monospace",
                        }}
                      >
                        {ctrl.framework} {ctrl.control_id}
                      </span>
                    ))}
                  </div>
                )}
                <div style={{ fontSize: 12, color: "#475569", marginTop: 8 }}>
                  {f.remediation}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const th: React.CSSProperties = {
  padding: "10px 12px",
  fontSize: 12,
  color: "#475569",
  fontWeight: 600,
};
const td: React.CSSProperties = { padding: "10px 12px", fontSize: 13, color: "#0f172a" };
