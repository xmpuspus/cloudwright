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

  // A source and a target handle on all four sides. buildEdges picks the pair
  // from the tier gap, so a same-tier connection goes across instead of looping
  // out of the bottom and back into the top.
  const sides = [
    { pos: Position.Top, key: "top" },
    { pos: Position.Bottom, key: "bottom" },
    { pos: Position.Left, key: "left" },
    { pos: Position.Right, key: "right" },
  ] as const;

  return (
    <div className="node" style={{ ["--node-accent" as string]: color }}>
      {sides.map(({ pos, key }) => (
        <React.Fragment key={key}>
          <Handle
            type="target"
            id={`t-${key}`}
            position={pos}
            style={{ background: color }}
          />
          <Handle
            type="source"
            id={`s-${key}`}
            position={pos}
            style={{ background: color }}
          />
        </React.Fragment>
      ))}

      <div className="node__head">
        <svg
          width={24}
          height={24}
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          style={{
            display: "block",
            padding: 4,
            borderRadius: "var(--radius-sm)",
            background: `${color}22`,
            flexShrink: 0,
          }}
        >
          <path d={iconPath} />
        </svg>
        <span className="node__cat">{category}</span>
      </div>

      <div className="node__label">{d.label}</div>

      <div className="node__meta">
        <span>{d.service}</span>
        <span className="badge badge--neutral">{d.provider}</span>
      </div>

      {d.monthlyCost != null && d.monthlyCost > 0 && (
        <div className="node__cost">${d.monthlyCost.toFixed(0)}/mo</div>
      )}
    </div>
  );
}

export default memo(CloudServiceNode);
