import React, { useState, useCallback } from "react";
import { parseApiError } from "../lib/apiError";

interface CritiqueFinding {
  severity: string;
  source: string;
  code: string;
  message: string;
  recommendation: string;
  component: string | null;
}

interface CritiqueReport {
  score: number;
  grade: string;
  findings: CritiqueFinding[];
  blocking_count: number;
  summary: string;
}

interface ReviewPanelProps {
  spec: Record<string, unknown>;
  apiBase: string;
}

const SEV_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  critical: { bg: "#fef2f2", text: "#991b1b", border: "#fca5a5" },
  high: { bg: "#fff7ed", text: "#9a3412", border: "#fdba74" },
  medium: { bg: "#fffbeb", text: "#92400e", border: "#fcd34d" },
  low: { bg: "#f0fdf4", text: "#166534", border: "#86efac" },
};

export default function ReviewPanel({ spec, apiBase }: ReviewPanelProps) {
  const [wellArchitected, setWellArchitected] = useState(false);
  const [report, setReport] = useState<CritiqueReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spec, well_architected: wellArchitected }),
      });
      if (!res.ok) throw new Error(await parseApiError(res));
      setReport((await res.json()) as CritiqueReport);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setLoading(false);
    }
  }, [spec, apiBase, wellArchitected]);

  return (
    <div style={{ padding: 24, maxWidth: 920 }}>
      <h2 style={{ fontSize: 18, marginBottom: 6, color: "#0f172a" }}>Architecture Review</h2>
      <p style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>
        Deterministic critique — scorer, linter, and validator merged into one severity-ranked
        report. Runs offline, no LLM call.
      </p>

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
          checked={wellArchitected}
          onChange={(e) => setWellArchitected(e.target.checked)}
        />
        Include Well-Architected checks
      </label>

      <button
        onClick={run}
        disabled={loading}
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
        {loading ? "Reviewing…" : "Run review"}
      </button>

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
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 12,
              padding: "8px 18px",
              borderRadius: 8,
              fontSize: 15,
              fontWeight: 700,
              background: report.blocking_count === 0 ? "#dcfce7" : "#fee2e2",
              color: report.blocking_count === 0 ? "#166534" : "#991b1b",
              marginBottom: 16,
            }}
          >
            {report.score.toFixed(0)}/100 (grade {report.grade})
            <span style={{ fontWeight: 500, fontSize: 12, marginLeft: 8 }}>
              {report.blocking_count === 0
                ? "no blocking findings"
                : `${report.blocking_count} blocking finding(s)`}
            </span>
          </div>

          <h3 style={{ fontSize: 15, color: "#0f172a", marginBottom: 12 }}>
            Findings ({report.findings.length})
          </h3>

          {report.findings.length === 0 ? (
            <div style={{ fontSize: 14, color: "#166534" }}>
              No findings. This architecture passes every critic.
            </div>
          ) : (
            report.findings.map((f, i) => {
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
                  {f.recommendation && (
                    <div style={{ fontSize: 12, color: "#475569", marginTop: 8 }}>
                      {f.recommendation}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
