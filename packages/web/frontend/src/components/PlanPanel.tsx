import React, { useState, useCallback } from "react";
import { parseApiError } from "../lib/apiError";
import EmptyState from "./EmptyState";

interface PlanResult {
  tool: string;
  available: boolean;
  validated: boolean;
  plan_ran: boolean;
  ok: boolean;
  summary: { add: number; change: number; destroy: number } | null;
  messages: string[];
  output_tail: string;
}

interface PlanPanelProps {
  spec: Record<string, unknown>;
  apiBase: string;
}

const TARGETS = [
  { key: "terraform", label: "Terraform" },
  { key: "pulumi-python", label: "Pulumi (Python)" },
  { key: "pulumi-ts", label: "Pulumi (TS)" },
];

export default function PlanPanel({ spec, apiBase }: PlanPanelProps) {
  const [target, setTarget] = useState("terraform");
  const [result, setResult] = useState<PlanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${apiBase}/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spec, target, run_plan: true }),
      });
      if (!res.ok) throw new Error(await parseApiError(res));
      setResult((await res.json()) as PlanResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Plan failed");
    } finally {
      setLoading(false);
    }
  }, [spec, apiBase, target]);

  return (
    <div className="panel__body">
      <h2 className="panel__title">Deployability Check</h2>
      <p className="panel__lede">
        Runs <code className="inline">terraform validate</code> and{" "}
        <code className="inline">plan</code>, or <code className="inline">pulumi preview</code>,
        against the exported artifact. Nothing is ever applied. Validation needs no credentials,
        so it works offline.
      </p>

      <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap", marginBottom: "var(--space-4)" }}>
        {TARGETS.map((t) => (
          <button
            key={t.key}
            className="chip"
            aria-pressed={target === t.key}
            onClick={() => setTarget(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <button className="btn btn--primary" onClick={run} disabled={loading}>
        {loading && <span className="spinner" />}
        {loading ? "Running plan..." : "Run plan"}
      </button>

      {error && (
        <div className="callout callout--danger" style={{ marginTop: "var(--space-4)" }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{ marginTop: "var(--space-6)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <div>
            <span
              className={`badge ${result.ok ? "badge--success" : "badge--danger"}`}
              style={{ fontSize: "var(--text-base)", padding: "6px 14px" }}
            >
              {result.ok ? "Deployable" : "Not deployable"}
            </span>
            {result.ok && !result.plan_ran && (
              <span style={{ marginLeft: "var(--space-2)", fontSize: "var(--text-sm)", color: "var(--text-subtle)" }}>
                validate only, no credentials found
              </span>
            )}
          </div>

          {result.summary && (
            <div className="stat-grid">
              <div className="stat">
                <div className="stat__value" style={{ color: "var(--success)" }}>+{result.summary.add}</div>
                <div className="stat__label">Resources to add</div>
              </div>
              <div className="stat">
                <div className="stat__value" style={{ color: "var(--warn)" }}>~{result.summary.change}</div>
                <div className="stat__label">Resources to change</div>
              </div>
              <div className="stat">
                <div className="stat__value" style={{ color: "var(--danger)" }}>-{result.summary.destroy}</div>
                <div className="stat__label">Resources to destroy</div>
              </div>
            </div>
          )}

          {result.messages.length > 0 && (
            <ul style={{ paddingLeft: "var(--space-5)", fontSize: "var(--text-base)", color: "var(--text-muted)" }}>
              {result.messages.map((m, i) => (
                <li key={i} style={{ marginBottom: 4 }}>{m}</li>
              ))}
            </ul>
          )}

          {result.output_tail && (
            <div className="card">
              <div className="card__header">
                <span>{result.tool} output</span>
              </div>
              <pre className="code-block code-block--inverted" style={{ borderRadius: 0 }}>
                {result.output_tail}
              </pre>
            </div>
          )}
        </div>
      )}

      {!result && !loading && !error && (
        <EmptyState
          icon="refresh"
          title="No plan has run yet."
          hint="Pick a target above and run the plan. The check is read-only, so it never touches a live account."
        />
      )}
    </div>
  );
}
