import React, { useState, useCallback } from "react";
import { parseApiError } from "../lib/apiError";
import EmptyState from "./EmptyState";
import FindingCard from "./FindingCard";
import Icon from "./Icon";

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
    const blob = new Blob([JSON.stringify(report.oscal, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "compliance.oscal.json";
    a.click();
    URL.revokeObjectURL(url);
  }, [report]);

  return (
    <div className="panel__body">
      <h2 className="panel__title">Compliance Control Mapping</h2>
      <p className="panel__lede">
        Every design-stage finding carries the framework control it violates, before any
        infrastructure exists. A Checkov deep scan folds in when Checkov is on the PATH.
      </p>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", marginBottom: "var(--space-4)" }}>
        {FRAMEWORKS.map((f) => (
          <button
            key={f.key}
            className="chip"
            aria-pressed={selected.includes(f.key)}
            onClick={() => toggle(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <label className="checkbox" style={{ marginBottom: "var(--space-4)" }}>
        <input
          type="checkbox"
          checked={includeOscal}
          onChange={(e) => setIncludeOscal(e.target.checked)}
        />
        Include OSCAL 1.1.2 component-definition export
      </label>

      <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
        <button className="btn btn--primary" onClick={run} disabled={loading || selected.length === 0}>
          {loading && <span className="spinner" />}
          {loading ? "Scanning..." : "Run compliance scan"}
        </button>

        {report?.oscal && (
          <button className="btn" onClick={downloadOscal}>
            <Icon name="download" size={14} />
            Download OSCAL JSON
          </button>
        )}
      </div>

      {error && (
        <div className="callout callout--danger" style={{ marginTop: "var(--space-4)" }}>
          {error}
        </div>
      )}

      {report && (
        <div style={{ marginTop: "var(--space-6)" }}>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--text-subtle)", marginBottom: "var(--space-2)" }}>
            Scanner: <strong>{report.scanner}</strong>
            {report.checkov_used ? ", with the Checkov deep scan included" : ""}
          </p>

          <div className="table-wrap" style={{ marginBottom: "var(--space-6)" }}>
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">Framework</th>
                  <th scope="col">Controls satisfied</th>
                  <th scope="col">Violated</th>
                  <th scope="col">Findings</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {report.frameworks.map((s) => (
                  <tr key={s.framework}>
                    <td><strong>{s.framework}</strong></td>
                    <td className="num" style={{ textAlign: "left" }}>
                      {s.controls_satisfied}/{s.controls_total}
                    </td>
                    <td style={{ color: "var(--danger-text)", fontSize: "var(--text-sm)" }}>
                      {s.controls_violated.length ? s.controls_violated.join(", ") : "none"}
                    </td>
                    <td className="num" style={{ textAlign: "left" }}>{s.findings}</td>
                    <td>
                      <span className={`badge ${s.status === "pass" ? "badge--success" : "badge--danger"}`}>
                        {s.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-3)" }}>
            Findings ({report.findings.length})
          </h3>
          {report.findings.length === 0 ? (
            <div className="callout callout--success">
              No findings. Every selected control is satisfied by this design.
            </div>
          ) : (
            report.findings.map((f, i) => (
              <FindingCard
                key={i}
                severity={f.severity}
                title={f.message}
                source={f.source}
                detail={f.remediation}
                component={f.component_id}
              >
                {f.controls.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: "var(--space-2)" }}>
                    {f.controls.map((ctrl, j) => (
                      <span
                        key={j}
                        title={ctrl.title}
                        className="badge badge--neutral"
                        style={{ fontFamily: "var(--font-mono)", textTransform: "none" }}
                      >
                        {ctrl.framework} {ctrl.control_id}
                      </span>
                    ))}
                  </div>
                )}
              </FindingCard>
            ))
          )}
        </div>
      )}

      {!report && !loading && !error && (
        <EmptyState
          icon="check"
          title="No scan has run yet."
          hint="Pick the frameworks that apply, then run the scan. Every finding comes back with its control ID."
        />
      )}
    </div>
  );
}
