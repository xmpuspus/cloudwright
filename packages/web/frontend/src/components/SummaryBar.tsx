import React from "react";
import Icon from "./Icon";

interface UsageInfo {
  model?: string;
  input_tokens?: number;
  output_tokens?: number;
  cost_usd?: number;
  latency_ms?: number;
}

interface SpecSummary {
  components?: unknown[];
  provider?: string;
  region?: string;
  cost_estimate?: { monthly_total?: number };
}

interface SummaryBarProps {
  spec: SpecSummary | null;
  onDownloadTerraform?: () => void;
  onDownloadYaml?: () => void;
  validationSummary?: { passed: number; total: number } | null;
  usage?: UsageInfo | null;
}

export default function SummaryBar({
  spec,
  onDownloadTerraform,
  onDownloadYaml,
  validationSummary,
  usage,
}: SummaryBarProps) {
  if (!spec) return null;

  const usageParts: string[] = [];
  if (usage?.model) usageParts.push(usage.model.replace("claude-", "").replace("anthropic.", ""));
  if (usage?.input_tokens != null && usage?.output_tokens != null)
    usageParts.push(`${((usage.input_tokens + usage.output_tokens) / 1000).toFixed(1)}k tokens`);
  if (usage?.cost_usd != null) usageParts.push(`$${usage.cost_usd.toFixed(4)}`);
  if (usage?.latency_ms != null) usageParts.push(`${(usage.latency_ms / 1000).toFixed(1)}s`);

  const allPassed = validationSummary ? validationSummary.passed === validationSummary.total : false;

  return (
    <div className="summary">
      <span className="summary__stat">
        Components: <strong>{spec.components?.length || 0}</strong>
      </span>
      {spec.cost_estimate && (
        <span className="summary__stat summary__stat--accent">
          Est. <strong>${spec.cost_estimate.monthly_total?.toFixed(0)}/mo</strong>
        </span>
      )}
      <span className="summary__stat">
        <strong>{(spec.provider || "aws").toUpperCase()}</strong> {spec.region || "us-east-1"}
      </span>
      {validationSummary && (
        <span
          className={`badge ${allPassed ? "badge--success" : "badge--danger"}`}
          title="Well-Architected checks passed out of total"
        >
          WA: {validationSummary.passed}/{validationSummary.total}
        </span>
      )}
      {usageParts.length > 0 && (
        <span className="summary__stat" style={{ fontSize: "var(--text-sm)" }}>
          {usageParts.join(" / ")}
        </span>
      )}
      <div className="summary__actions">
        {onDownloadTerraform && (
          <button className="btn btn--primary btn--sm" onClick={onDownloadTerraform}>
            <Icon name="download" size={13} />
            Download Terraform
          </button>
        )}
        {onDownloadYaml && (
          <button className="btn btn--sm" onClick={onDownloadYaml}>
            Download YAML
          </button>
        )}
      </div>
    </div>
  );
}
