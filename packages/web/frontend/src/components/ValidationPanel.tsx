import React, { useState, useCallback } from "react";
import { parseApiError } from "../lib/apiError";
import EmptyState from "./EmptyState";
import Icon from "./Icon";

interface ValidationCheck {
  name: string;
  category: string;
  passed: boolean;
  severity: string;
  detail: string;
  recommendation: string;
}

interface ValidationResult {
  framework: string;
  passed: boolean;
  score: number;
  checks: ValidationCheck[];
}

interface ValidationPanelProps {
  spec: Record<string, unknown>;
  apiBase: string;
}

const FRAMEWORKS = [
  { key: "hipaa", label: "HIPAA" },
  { key: "pci-dss", label: "PCI-DSS" },
  { key: "soc2", label: "SOC 2" },
  { key: "fedramp", label: "FedRAMP" },
  { key: "gdpr", label: "GDPR" },
  { key: "well-architected", label: "Well-Architected" },
];

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const CATEGORY_LABELS: Record<string, string> = {
  data_protection: "Data Protection",
  monitoring: "Monitoring and Logging",
  identity: "Identity and Access",
  network_security: "Network Security",
  reliability: "Reliability",
  compliance: "Compliance",
  operations: "Operations",
  security: "Security",
  cost: "Cost Optimization",
};

function ScoreArc({ score, passed }: { score: number; passed: boolean }) {
  const pct = Math.round(score * 100);
  const radius = 48;
  const stroke = 8;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.max(0, Math.min(1, score)));
  const color = passed ? "var(--success)" : pct >= 70 ? "var(--warn)" : "var(--danger)";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-2)" }}>
      <svg width={120} height={120} viewBox="0 0 120 120" role="img" aria-label={`Score ${pct} percent`}>
        <circle cx={60} cy={60} r={radius} fill="none" stroke="var(--bg-inset)" strokeWidth={stroke} />
        <circle
          cx={60}
          cy={60}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 60 60)"
          style={{ transition: "stroke-dashoffset 0.6s var(--ease)" }}
        />
        <text x={60} y={56} textAnchor="middle" fontSize={26} fontWeight={700} fill="var(--text)">
          {pct}%
        </text>
        <text x={60} y={75} textAnchor="middle" fontSize={11} fill="var(--text-subtle)">
          checks passed
        </text>
      </svg>
      <span className={`badge ${passed ? "badge--success" : "badge--danger"}`}>
        {passed ? "Passed" : "Failed"}
      </span>
    </div>
  );
}

function CheckRow({
  check,
  expanded,
  onToggle,
}: {
  check: ValidationCheck;
  expanded: boolean;
  onToggle: () => void;
}) {
  const sev = SEVERITY_ORDER[check.severity] !== undefined ? check.severity : "medium";
  const accent = check.passed
    ? "var(--success)"
    : sev === "critical"
      ? "var(--danger)"
      : sev === "high"
        ? "var(--high-text)"
        : sev === "medium"
          ? "var(--warn)"
          : "var(--success)";

  return (
    <div
      style={{
        borderLeft: `3px solid ${accent}`,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderLeftWidth: 3,
        borderLeftColor: accent,
        borderRadius: "var(--radius)",
        marginBottom: 6,
        overflow: "hidden",
      }}
    >
      <button
        onClick={onToggle}
        aria-expanded={expanded}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-2)",
          width: "100%",
          padding: "9px 14px",
          border: "none",
          background: "transparent",
          textAlign: "left",
          cursor: "pointer",
        }}
      >
        <span style={{ color: check.passed ? "var(--success)" : "var(--danger)", display: "flex" }}>
          <Icon name={check.passed ? "check" : "cross"} size={15} strokeWidth={2.4} />
        </span>
        <span style={{ flex: 1, fontSize: "var(--text-base)", fontWeight: 550, minWidth: 0 }}>
          {check.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        </span>
        <span className={`badge badge--${sev}`}>{check.severity}</span>
        <span
          style={{
            display: "flex",
            color: "var(--text-subtle)",
            transform: expanded ? "rotate(180deg)" : "none",
            transition: "transform var(--duration) var(--ease)",
          }}
        >
          <Icon name="chevron" size={13} />
        </span>
      </button>
      {expanded && (
        <div style={{ padding: "0 14px 12px 40px", fontSize: "var(--text-sm)", lineHeight: 1.6 }}>
          <p style={{ color: "var(--text-muted)" }}>{check.detail}</p>
          {check.recommendation && (
            <div className="callout" style={{ marginTop: "var(--space-2)", fontSize: "var(--text-sm)" }}>
              <strong style={{ color: "var(--text)" }}>Recommendation: </strong>
              {check.recommendation}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ValidationPanel({ spec, apiBase }: ValidationPanelProps) {
  const [results, setResults] = useState<ValidationResult[] | null>(null);
  const [activeFramework, setActiveFramework] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedChecks, setExpandedChecks] = useState<Set<string>>(new Set());
  const [showPassed, setShowPassed] = useState(false);

  const runValidation = useCallback(
    async (fw: string) => {
      setActiveFramework(fw);
      setLoading(true);
      setError(null);
      setExpandedChecks(new Set());
      setShowPassed(false);
      try {
        const isWA = fw === "well-architected";
        const res = await fetch(`${apiBase}/validate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ spec, compliance: isWA ? [] : [fw], well_architected: isWA }),
        });
        if (!res.ok) throw new Error(await parseApiError(res));
        const data = await res.json();
        setResults(data.results);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Validation failed");
        setResults(null);
      } finally {
        setLoading(false);
      }
    },
    [spec, apiBase],
  );

  const toggleCheck = useCallback((key: string) => {
    setExpandedChecks((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  // The API returns an array, but this panel requests one framework at a time.
  const result = results?.[0] ?? null;

  const failedChecks = result
    ? result.checks
        .filter((c) => !c.passed)
        .sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9))
    : [];

  const passedChecks = result
    ? result.checks
        .filter((c) => c.passed)
        .sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9))
    : [];

  const failedByCategory: Record<string, ValidationCheck[]> = {};
  for (const c of failedChecks) {
    if (!failedByCategory[c.category]) failedByCategory[c.category] = [];
    failedByCategory[c.category].push(c);
  }

  const severityCounts = result
    ? result.checks.reduce(
        (acc, c) => {
          if (!c.passed) acc[c.severity] = (acc[c.severity] || 0) + 1;
          return acc;
        },
        {} as Record<string, number>,
      )
    : {};

  return (
    <div className="panel__body">
      <h2 className="panel__title">Validate Architecture</h2>
      <p className="panel__lede">
        One framework at a time. A framework fails when any critical check fails, whatever the
        overall score says.
      </p>

      <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap", marginBottom: "var(--space-5)" }}>
        {FRAMEWORKS.map((fw) => (
          <button
            key={fw.key}
            className="chip"
            aria-pressed={activeFramework === fw.key}
            onClick={() => runValidation(fw.key)}
            disabled={loading}
          >
            {fw.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="status-row">
          <span className="spinner" />
          Running {activeFramework?.toUpperCase()} validation...
        </div>
      )}

      {error && <div className="callout callout--danger">{error}</div>}

      {result && !loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
          <div
            className="card"
            style={{ display: "flex", gap: "var(--space-6)", alignItems: "flex-start", padding: "var(--space-5)", flexWrap: "wrap" }}
          >
            <ScoreArc score={result.score} passed={result.passed} />

            <div style={{ flex: 1, minWidth: 240 }}>
              <h3 style={{ fontSize: "var(--text-lg)", marginBottom: 4 }}>{result.framework}</h3>
              <p style={{ fontSize: "var(--text-base)", color: "var(--text-muted)", marginBottom: "var(--space-4)" }}>
                {result.checks.length} checks evaluated, {passedChecks.length} passed,{" "}
                {failedChecks.length} failed.
              </p>

              <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
                {(["critical", "high", "medium", "low"] as const).map((sev) => {
                  const count = severityCounts[sev] || 0;
                  return (
                    <div
                      key={sev}
                      className={count > 0 ? `badge badge--${sev}` : "badge badge--neutral"}
                      style={{ padding: "6px 12px", gap: 8 }}
                    >
                      <span style={{ fontSize: "var(--text-lg)", fontWeight: 700, lineHeight: 1 }}>{count}</span>
                      {sev}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {failedChecks.length > 0 && (
            <div>
              <h3 style={{ fontSize: "var(--text-md)", marginBottom: "var(--space-3)", display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ color: "var(--danger)", display: "flex" }}>
                  <Icon name="cross" size={15} strokeWidth={2.4} />
                </span>
                Failed Checks ({failedChecks.length})
              </h3>
              {Object.entries(failedByCategory).map(([category, checks]) => (
                <div key={category} style={{ marginBottom: "var(--space-4)" }}>
                  <p className="section-label" style={{ marginBottom: 6 }}>
                    {CATEGORY_LABELS[category] || category.replace(/_/g, " ")}
                  </p>
                  {checks.map((check) => {
                    const key = `${category}-${check.name}`;
                    return (
                      <CheckRow
                        key={key}
                        check={check}
                        expanded={expandedChecks.has(key)}
                        onToggle={() => toggleCheck(key)}
                      />
                    );
                  })}
                </div>
              ))}
            </div>
          )}

          {passedChecks.length > 0 && (
            <div>
              <button
                onClick={() => setShowPassed((v) => !v)}
                aria-expanded={showPassed}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: "4px 0",
                  fontSize: "var(--text-md)",
                  fontWeight: 650,
                  color: "var(--text)",
                }}
              >
                <span style={{ color: "var(--success)", display: "flex" }}>
                  <Icon name="check" size={15} strokeWidth={2.4} />
                </span>
                Passed Checks ({passedChecks.length})
                <span
                  style={{
                    display: "flex",
                    color: "var(--text-subtle)",
                    transform: showPassed ? "rotate(180deg)" : "none",
                    transition: "transform var(--duration) var(--ease)",
                  }}
                >
                  <Icon name="chevron" size={13} />
                </span>
              </button>
              {showPassed && (
                <div style={{ marginTop: "var(--space-2)" }}>
                  {passedChecks.map((check) => {
                    const key = `passed-${check.category}-${check.name}`;
                    return (
                      <CheckRow
                        key={key}
                        check={check}
                        expanded={expandedChecks.has(key)}
                        onToggle={() => toggleCheck(key)}
                      />
                    );
                  })}
                </div>
              )}
            </div>
          )}

          <p style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", borderTop: "1px solid var(--border)", paddingTop: "var(--space-3)", lineHeight: 1.6 }}>
            Score is the percentage of checks passed. A framework is marked failed if any
            critical-severity check fails, whatever the score. The Cloudwright validator defines
            these checks from the {result.framework} control requirements.
          </p>
        </div>
      )}

      {!result && !loading && !error && (
        <EmptyState
          icon="check"
          title="No framework selected yet."
          hint="Pick a framework above. Every failed check comes back with the reason and a fix."
        />
      )}
    </div>
  );
}
