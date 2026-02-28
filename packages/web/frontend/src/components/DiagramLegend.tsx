import React from "react";
import { CATEGORY_COLORS } from "../lib/icons";

export default function DiagramLegend() {
  const categories = Object.entries(CATEGORY_COLORS);
  return (
    <div
      style={{
        position: "absolute",
        bottom: 16,
        left: 16,
        zIndex: 10,
        background: "#0f172a",
        border: "1px solid #1e293b",
        borderRadius: 8,
        padding: "8px 12px",
        fontSize: 11,
        color: "#94a3b8",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4, color: "#f8fafc" }}>Legend</div>
      {categories.map(([cat, color]) => (
        <div
          key={cat}
          style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: 2,
              background: color,
              display: "inline-block",
              flexShrink: 0,
            }}
          />
          <span style={{ textTransform: "capitalize" }}>{cat}</span>
        </div>
      ))}
    </div>
  );
}
