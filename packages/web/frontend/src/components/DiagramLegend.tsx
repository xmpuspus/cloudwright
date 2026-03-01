import React, { useState, useMemo } from "react";
import { CATEGORY_COLORS, getCategoryIconPath, getServiceCategory } from "../lib/icons";

interface LegendProps {
  components?: { service: string }[];
}

export default function DiagramLegend({ components }: LegendProps) {
  const [collapsed, setCollapsed] = useState(false);

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
      style={{
        position: "absolute",
        bottom: 16,
        left: 16,
        zIndex: 10,
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        padding: "8px 12px",
        fontSize: 11,
        color: "#64748b",
        boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
        maxHeight: collapsed ? "auto" : 260,
        overflowY: collapsed ? "visible" : "auto",
      }}
    >
      <div
        onClick={() => setCollapsed((v) => !v)}
        style={{
          fontWeight: 600,
          marginBottom: collapsed ? 0 : 4,
          color: "#0f172a",
          cursor: "pointer",
          userSelect: "none",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        Legend
        <span style={{ fontSize: 10, color: "#94a3b8" }}>{collapsed ? "+" : "-"}</span>
      </div>
      {!collapsed &&
        categoryCounts.map(({ category, count }) => {
          const color = CATEGORY_COLORS[category] || "#94a3b8";
          const iconPath = getCategoryIconPath(category);
          return (
            <div
              key={category}
              style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}
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
                style={{ flexShrink: 0 }}
              >
                <path d={iconPath} />
              </svg>
              <span style={{ textTransform: "capitalize" }}>{category}</span>
              {count > 0 && (
                <span style={{ color: "#94a3b8", fontSize: 10 }}>({count})</span>
              )}
            </div>
          );
        })}
    </div>
  );
}
