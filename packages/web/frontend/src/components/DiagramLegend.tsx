import React, { useState, useMemo } from "react";
import { CATEGORY_COLORS, getCategoryIconPath, getServiceCategory } from "../lib/icons";
import Icon from "./Icon";

interface LegendProps {
  components?: { service: string }[];
}

export default function DiagramLegend({ components }: LegendProps) {
  const [open, setOpen] = useState(true);

  const categoryCounts = useMemo(() => {
    if (!components || components.length === 0) {
      return Object.keys(CATEGORY_COLORS).map((cat) => ({ category: cat, count: 0 }));
    }
    const counts: Record<string, number> = {};
    for (const comp of components) {
      const cat = getServiceCategory(comp.service);
      counts[cat] = (counts[cat] || 0) + 1;
    }
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .map(([category, count]) => ({ category, count }));
  }, [components]);

  return (
    <div
      className="float-panel"
      style={{
        bottom: "var(--space-4)",
        right: "var(--space-4)",
        padding: "var(--space-2) var(--space-3)",
        maxHeight: 280,
        overflowY: "auto",
        fontSize: "var(--text-xs)",
      }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "var(--space-3)",
          width: "100%",
          border: "none",
          background: "transparent",
          cursor: "pointer",
          padding: 0,
          marginBottom: open ? 6 : 0,
          fontSize: "var(--text-sm)",
          fontWeight: 650,
          color: "var(--text)",
        }}
      >
        Legend
        <span style={{ transform: open ? "none" : "rotate(-90deg)", transition: "transform 160ms" }}>
          <Icon name="chevron" size={13} strokeWidth={2} />
        </span>
      </button>
      {open &&
        categoryCounts.map(({ category, count }) => {
          const color = CATEGORY_COLORS[category] || "currentColor";
          return (
            <div
              key={category}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                marginBottom: 3,
                color: "var(--text-muted)",
              }}
            >
              <svg
                width={12}
                height={12}
                viewBox="0 0 24 24"
                fill="none"
                stroke={color}
                strokeWidth={2.5}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                style={{ flexShrink: 0 }}
              >
                <path d={getCategoryIconPath(category)} />
              </svg>
              <span style={{ textTransform: "capitalize" }}>{category}</span>
              {count > 0 && <span style={{ color: "var(--text-subtle)" }}>({count})</span>}
            </div>
          );
        })}
    </div>
  );
}
