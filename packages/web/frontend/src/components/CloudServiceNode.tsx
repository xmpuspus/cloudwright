import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { getCategoryColor, getServiceCategory, getIconChar } from "../lib/icons";

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
  const iconChar = getIconChar(d.service);

  return (
    <div
      style={{
        background: "#1e293b",
        border: `2px solid ${color}`,
        borderRadius: 10,
        padding: "8px 12px",
        color: "#f8fafc",
        minWidth: 160,
        position: "relative",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: color }} />

      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 28,
            height: 28,
            borderRadius: 6,
            background: `${color}22`,
            color,
            fontWeight: 700,
            fontSize: 14,
          }}
        >
          {iconChar}
        </span>
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

      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{d.label}</div>

      <div style={{ fontSize: 11, color: "#94a3b8" }}>
        {d.service}
        <span
          style={{
            marginLeft: 6,
            padding: "1px 4px",
            borderRadius: 3,
            background: "#334155",
            fontSize: 9,
            textTransform: "uppercase",
          }}
        >
          {d.provider}
        </span>
      </div>

      {d.monthlyCost != null && d.monthlyCost > 0 && (
        <div style={{ fontSize: 10, color: "#10b981", marginTop: 4 }}>
          ${d.monthlyCost.toFixed(0)}/mo
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: color }} />
    </div>
  );
}

export default memo(CloudServiceNode);
