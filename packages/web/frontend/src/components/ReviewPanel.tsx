import React, { useState, useCallback } from "react";
import { parseApiError } from "../lib/apiError";
import EmptyState from "./EmptyState";
import FindingCard from "./FindingCard";

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
    <div className="panel__body">
      <h2 className="panel__title">Architecture Review</h2>
      <p className="panel__lede">
        The scorer, the linter and the validator merged into one severity-ranked report. Runs
        offline, with no LLM call, so the result is the same every time.
      </p>

      <label className="checkbox" style={{ marginBottom: "var(--space-4)" }}>
        <input
          type="checkbox"
          checked={wellArchitected}
          onChange={(e) => setWellArchitected(e.target.checked)}
        />
        Include Well-Architected checks
      </label>

      <div>
        <button className="btn btn--primary" onClick={run} disabled={loading}>
          {loading && <span className="spinner" />}
          {loading ? "Reviewing..." : "Run review"}
        </button>
      </div>

      {error && (
        <div className="callout callout--danger" style={{ marginTop: "var(--space-4)" }}>
          {error}
        </div>
      )}

      {report && (
        <div style={{ marginTop: "var(--space-6)" }}>
          <div className="stat-grid" style={{ marginBottom: "var(--space-5)" }}>
            <div className="stat">
              <div className="stat__value">
                {report.score.toFixed(0)}
                <span style={{ fontSize: "var(--text-md)", color: "var(--text-subtle)" }}>/100</span>
              </div>
              <div className="stat__label">Score, grade {report.grade}</div>
            </div>
            <div className="stat">
              <div
                className="stat__value"
                style={{ color: report.blocking_count === 0 ? "var(--success)" : "var(--danger)" }}
              >
                {report.blocking_count}
              </div>
              <div className="stat__label">Blocking findings</div>
            </div>
            <div className="stat">
              <div className="stat__value">{report.findings.length}</div>
              <div className="stat__label">Findings in total</div>
            </div>
          </div>

          <h3 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-3)" }}>
            Findings ({report.findings.length})
          </h3>

          {report.findings.length === 0 ? (
            <div className="callout callout--success">
              No findings. This architecture passes every critic.
            </div>
          ) : (
            report.findings.map((f, i) => (
              <FindingCard
                key={i}
                severity={f.severity}
                title={f.message}
                source={f.source}
                detail={f.recommendation}
                component={f.component}
              />
            ))
          )}
        </div>
      )}

      {!report && !loading && !error && (
        <EmptyState
          icon="alert"
          title="No review has run yet."
          hint="The review reads the current spec and ranks what it finds, from critical down to low."
        />
      )}
    </div>
  );
}
