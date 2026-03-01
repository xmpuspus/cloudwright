import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { getCategoryColor, getServiceCategory, getCategoryIconPath } from "../lib/icons";

interface CloudServiceData {
  label: string;
  service: string;
  provider: string;
  description?: string;
  tier: number;
  config?: Record<string, unknown>;
  monthlyCost?: number;
}

function CloudServiceNode({ data }: NodeProps) {
  const d = data as unknown as CloudServiceData;
  const category = getServiceCategory(d.service);
  const color = getCategoryColor(category);
  const iconPath = getCategoryIconPath(category);

  return (
    <div
      style={{
        background: "#ffffff",
        border: `2px solid ${color}`,
        borderRadius: 10,
        padding: "8px 12px",
        color: "#0f172a",
        minWidth: 160,
        position: "relative",
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: color }} />

      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
        <svg
          width={16}
          height={16}
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            display: "block",
            width: 28,
            height: 28,
            padding: 5,
            borderRadius: 6,
            background: `${color}22`,
          }}
        >
          <path d={iconPath} />
        </svg>
        <span
          style={{
            fontSize: 9,
            color: "#64748b",
            textTransform: "uppercase",
            letterSpacing: 1,
          }}
        >
          {category}
        </span>
      </div>

      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2, color: "#0f172a" }}>{d.label}</div>

      <div style={{ fontSize: 11, color: "#64748b" }}>
        {d.service}
        <span
          style={{
            marginLeft: 6,
            padding: "1px 4px",
            borderRadius: 3,
            background: "#e2e8f0",
            color: "#475569",
            fontSize: 9,
            textTransform: "uppercase",
          }}
        >
          {d.provider}
        </span>
      </div>

      {d.monthlyCost != null && d.monthlyCost > 0 && (
        <div style={{ fontSize: 10, color: "#2563eb", marginTop: 4 }}>
          ${d.monthlyCost.toFixed(0)}/mo
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: color }} />
    </div>
  );
}

export default memo(CloudServiceNode);
