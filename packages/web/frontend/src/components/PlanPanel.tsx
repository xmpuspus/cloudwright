import React, { useState, useCallback } from "react";

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
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `Request failed (${res.status})`);
      }
      setResult((await res.json()) as PlanResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Plan failed");
    } finally {
      setLoading(false);
    }
  }, [spec, apiBase, target]);

  return (
    <div style={{ padding: 24, maxWidth: 920 }}>
      <h2 style={{ fontSize: 18, marginBottom: 6, color: "#0f172a" }}>
        Plan / Preview — prove it deploys
      </h2>
      <p style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>
        Runs <code>terraform validate/plan</code> or <code>pulumi preview</code> against the
        exported artifact. Read-only — nothing is applied. Validation needs no credentials and is
        the offline proof of deployability.
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {TARGETS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTarget(t.key)}
            style={{
              padding: "6px 14px",
              borderRadius: 8,
              border: `1px solid ${target === t.key ? "#2563eb" : "#cbd5e1"}`,
              background: target === t.key ? "#2563eb" : "#ffffff",
              color: target === t.key ? "#ffffff" : "#475569",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

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
        {loading ? "Running plan…" : "Run plan"}
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

      {result && (
        <div style={{ marginTop: 24 }}>
          <div
            style={{
              display: "inline-block",
              padding: "8px 18px",
              borderRadius: 8,
              fontSize: 15,
              fontWeight: 700,
              background: result.ok ? "#dcfce7" : "#fee2e2",
              color: result.ok ? "#166534" : "#991b1b",
              marginBottom: 16,
            }}
          >
            {result.ok ? "DEPLOYABLE" : "NOT DEPLOYABLE"}
            {result.ok && !result.plan_ran ? "  (validate only — no credentials)" : ""}
          </div>

          {result.summary && (
            <div style={{ fontSize: 14, marginBottom: 16 }}>
              Resource diff:{" "}
              <span style={{ color: "#166534" }}>+{result.summary.add}</span>{" "}
              <span style={{ color: "#92400e" }}>~{result.summary.change}</span>{" "}
              <span style={{ color: "#991b1b" }}>-{result.summary.destroy}</span>
            </div>
          )}

          <ul style={{ fontSize: 13, color: "#334155", marginBottom: 16, paddingLeft: 18 }}>
            {result.messages.map((m, i) => (
              <li key={i} style={{ marginBottom: 4 }}>
                {m}
              </li>
            ))}
          </ul>

          {result.output_tail && (
            <pre
              style={{
                background: "#0f172a",
                color: "#e2e8f0",
                padding: 14,
                borderRadius: 8,
                fontSize: 12,
                overflowX: "auto",
                maxHeight: 280,
              }}
            >
              {result.output_tail}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
