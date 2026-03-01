import React, { useState, useCallback } from "react";

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
  { key: "well-architected", label: "Well-Architected" },
];

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const SEVERITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  critical: { bg: "#fef2f2", text: "#991b1b", border: "#fca5a5" },
  high: { bg: "#fff7ed", text: "#9a3412", border: "#fdba74" },
  medium: { bg: "#fffbeb", text: "#92400e", border: "#fcd34d" },
  low: { bg: "#f0fdf4", text: "#166534", border: "#86efac" },
};

const CATEGORY_LABELS: Record<string, string> = {
  data_protection: "Data Protection",
  monitoring: "Monitoring & Logging",
  identity: "Identity & Access",
  network_security: "Network Security",
  reliability: "Reliability",
  compliance: "Compliance",
  operations: "Operations",
  security: "Security",
  cost: "Cost Optimization",
};

function ScoreArc({ score, passed }: { score: number; passed: boolean }) {
  const pct = Math.round(score * 100);
  const radius = 54;
  const stroke = 8;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score);
  const color = passed ? "#16a34a" : pct >= 70 ? "#f59e0b" : "#dc2626";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <svg width={136} height={136} viewBox="0 0 136 136">
        <circle
          cx={68} cy={68} r={radius}
          fill="none" stroke="#f1f5f9" strokeWidth={stroke}
        />
        <circle
          cx={68} cy={68} r={radius}
          fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 68 68)"
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
        <text x={68} y={62} textAnchor="middle" fontSize={28} fontWeight={700} fill="#0f172a">
          {pct}%
        </text>
        <text x={68} y={82} textAnchor="middle" fontSize={11} fill="#64748b">
          compliance
        </text>
      </svg>
      <span
        style={{
          display: "inline-block",
          padding: "3px 12px",
          borderRadius: 4,
          fontSize: 12,
          fontWeight: 600,
          background: passed ? "#dcfce7" : "#fee2e2",
          color: passed ? "#166534" : "#991b1b",
        }}
      >
        {passed ? "PASSED" : "FAILED"}
      </span>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors = SEVERITY_COLORS[severity] || SEVERITY_COLORS.medium;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "1px 8px",
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        background: colors.bg,
        color: colors.text,
        border: `1px solid ${colors.border}`,
        textTransform: "uppercase",
        letterSpacing: "0.02em",
      }}
    >
      {severity}
    </span>
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
  const colors = SEVERITY_COLORS[check.severity] || SEVERITY_COLORS.medium;

  return (
    <div
      style={{
        borderLeft: `3px solid ${check.passed ? "#86efac" : colors.border}`,
        background: "#ffffff",
        borderRadius: "0 6px 6px 0",
        marginBottom: 6,
        cursor: "pointer",
        transition: "box-shadow 0.15s ease",
      }}
      onClick={onToggle}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow = "0 1px 4px rgba(0,0,0,0.06)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow = "none";
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 14px",
        }}
      >
        <span style={{ fontSize: 14, flexShrink: 0, width: 18, textAlign: "center" }}>
          {check.passed ? (
            <span style={{ color: "#16a34a" }}>&#10003;</span>
          ) : (
            <span style={{ color: "#dc2626", fontWeight: 700 }}>&#10005;</span>
          )}
        </span>
        <span
          style={{
            flex: 1,
            fontSize: 13,
            color: "#0f172a",
            fontWeight: 500,
          }}
        >
          {check.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        </span>
        <SeverityBadge severity={check.severity} />
        <span
          style={{
            fontSize: 11,
            color: "#94a3b8",
            transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.15s ease",
            flexShrink: 0,
          }}
        >
          &#9660;
        </span>
      </div>
      {expanded && (
        <div style={{ padding: "0 14px 12px 42px", fontSize: 12, lineHeight: 1.6 }}>
          <div style={{ color: "#475569", marginBottom: 4 }}>{check.detail}</div>
          {check.recommendation && (
            <div
              style={{
                marginTop: 6,
                padding: "8px 12px",
                background: "#f8fafc",
                borderRadius: 4,
                border: "1px solid #e2e8f0",
                color: "#334155",
              }}
            >
              <span style={{ fontWeight: 600, color: "#475569", fontSize: 11 }}>Recommendation: </span>
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
          body: JSON.stringify({
            spec,
            compliance: isWA ? [] : [fw],
            well_architected: isWA,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Validation failed");
        setResults(data.results);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Validation failed");
        setResults(null);
      } finally {
        setLoading(false);
      }
    },
    [spec, apiBase]
  );

  const toggleCheck = useCallback((key: string) => {
    setExpandedChecks((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  // Derive display data from first result (API returns array, but we request one framework at a time)
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

  // Group failed checks by category
  const failedByCategory: Record<string, ValidationCheck[]> = {};
  for (const c of failedChecks) {
    const cat = c.category;
    if (!failedByCategory[cat]) failedByCategory[cat] = [];
    failedByCategory[cat].push(c);
  }

  // Severity summary counts
  const severityCounts = result
    ? result.checks.reduce(
        (acc, c) => {
          if (!c.passed) acc[c.severity] = (acc[c.severity] || 0) + 1;
          return acc;
        },
        {} as Record<string, number>
      )
    : {};

  return (
    <div style={{ padding: 32, maxWidth: 900 }}>
      <h2 style={{ fontSize: 18, marginBottom: 16, color: "#0f172a", fontWeight: 700 }}>
        Validate Architecture
      </h2>

      {/* Framework selector */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {FRAMEWORKS.map((fw) => {
          const isActive = activeFramework === fw.key;
          return (
            <button
              key={fw.key}
              onClick={() => runValidation(fw.key)}
              disabled={loading}
              style={{
                padding: "8px 18px",
                borderRadius: 6,
                border: isActive ? "1.5px solid #2563eb" : "1px solid #e2e8f0",
                background: isActive ? "#eff6ff" : "#ffffff",
                color: isActive ? "#1d4ed8" : "#475569",
                cursor: loading ? "wait" : "pointer",
                fontSize: 13,
                fontWeight: isActive ? 600 : 500,
                transition: "all 0.15s ease",
                opacity: loading && !isActive ? 0.6 : 1,
              }}
            >
              {fw.label}
            </button>
          );
        })}
      </div>

      {/* Loading state */}
      {loading && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: 24,
            color: "#64748b",
            fontSize: 14,
          }}
        >
          <span
            style={{
              display: "inline-block",
              width: 16,
              height: 16,
              border: "2px solid #e2e8f0",
              borderTopColor: "#2563eb",
              borderRadius: "50%",
              animation: "spin 0.6s linear infinite",
            }}
          />
          Running {activeFramework?.toUpperCase()} validation...
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div
          style={{
            padding: "12px 16px",
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

      {/* Results */}
      {result && !loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Top summary row */}
          <div
            style={{
              display: "flex",
              gap: 24,
              alignItems: "flex-start",
              padding: 20,
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: 10,
            }}
          >
            <ScoreArc score={result.score} passed={result.passed} />

            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", marginBottom: 4 }}>
                {result.framework}
              </div>
              <div style={{ fontSize: 13, color: "#64748b", marginBottom: 14 }}>
                {result.checks.length} checks evaluated &middot;{" "}
                {passedChecks.length} passed &middot;{" "}
                {failedChecks.length} failed
              </div>

              {/* Severity summary cards */}
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {(["critical", "high", "medium", "low"] as const).map((sev) => {
                  const count = severityCounts[sev] || 0;
                  const colors = SEVERITY_COLORS[sev];
                  return (
                    <div
                      key={sev}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        borderRadius: 6,
                        background: count > 0 ? colors.bg : "#f8fafc",
                        border: `1px solid ${count > 0 ? colors.border : "#e2e8f0"}`,
                        minWidth: 100,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 18,
                          fontWeight: 700,
                          color: count > 0 ? colors.text : "#cbd5e1",
                          lineHeight: 1,
                        }}
                      >
                        {count}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 600,
                          color: count > 0 ? colors.text : "#94a3b8",
                          textTransform: "uppercase",
                          letterSpacing: "0.03em",
                        }}
                      >
                        {sev}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Failed checks grouped by category */}
          {failedChecks.length > 0 && (
            <div>
              <h3
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: "#0f172a",
                  marginBottom: 12,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span style={{ color: "#dc2626" }}>&#10005;</span>
                Failed Checks ({failedChecks.length})
              </h3>
              {Object.entries(failedByCategory).map(([category, checks]) => (
                <div key={category} style={{ marginBottom: 16 }}>
                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: "#64748b",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      marginBottom: 6,
                      paddingLeft: 4,
                    }}
                  >
                    {CATEGORY_LABELS[category] || category.replace(/_/g, " ")}
                  </div>
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

          {/* Passed checks — collapsible */}
          {passedChecks.length > 0 && (
            <div>
              <button
                onClick={() => setShowPassed((v) => !v)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: "4px 0",
                  fontSize: 14,
                  fontWeight: 600,
                  color: "#0f172a",
                }}
              >
                <span style={{ color: "#16a34a" }}>&#10003;</span>
                Passed Checks ({passedChecks.length})
                <span
                  style={{
                    fontSize: 11,
                    color: "#94a3b8",
                    transform: showPassed ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 0.15s ease",
                  }}
                >
                  &#9660;
                </span>
              </button>
              {showPassed && (
                <div style={{ marginTop: 8 }}>
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

          {/* Methodology footnote */}
          <div
            style={{
              fontSize: 11,
              color: "#94a3b8",
              borderTop: "1px solid #f1f5f9",
              paddingTop: 12,
              lineHeight: 1.5,
            }}
          >
            Score = percentage of checks passed. A framework is marked FAILED if any critical-severity
            check fails, regardless of overall score. Checks are defined in the Cloudwright Validator
            based on {result.framework} control requirements.
          </div>
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && !error && (
        <div
          style={{
            padding: 40,
            textAlign: "center",
            color: "#94a3b8",
            fontSize: 14,
            background: "#f8fafc",
            borderRadius: 8,
            border: "1px dashed #e2e8f0",
          }}
        >
          Select a compliance framework above to validate your architecture.
        </div>
      )}
    </div>
  );
}
