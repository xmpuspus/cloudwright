import React from "react";

interface FindingCardProps {
  severity: string;
  title: string;
  source?: string;
  detail?: string;
  component?: string | null;
  children?: React.ReactNode;
}

const KNOWN = new Set(["critical", "high", "medium", "low"]);

/** One severity-coloured finding row. Shared by the review and compliance panels,
 *  so a severity always looks the same wherever it appears. */
export default function FindingCard({
  severity,
  title,
  source,
  detail,
  component,
  children,
}: FindingCardProps) {
  const key = KNOWN.has(severity) ? severity : "low";
  return (
    <div
      className="card"
      style={{
        marginBottom: "var(--space-2)",
        borderLeft: `3px solid var(--${key === "critical" ? "danger" : key === "high" ? "high-text" : key === "medium" ? "warn" : "success"})`,
      }}
    >
      <div className="card__body" style={{ padding: "var(--space-3) var(--space-4)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
          <span className={`badge badge--${key}`}>{severity}</span>
          <span style={{ fontSize: "var(--text-md)", fontWeight: 550 }}>{title}</span>
          {component && <code className="inline">{component}</code>}
          {source && (
            <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginLeft: "auto" }}>
              {source}
            </span>
          )}
        </div>
        {detail && (
          <p style={{ fontSize: "var(--text-base)", color: "var(--text-muted)", marginTop: "var(--space-2)" }}>
            {detail}
          </p>
        )}
        {children}
      </div>
    </div>
  );
}
