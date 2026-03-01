import React from "react";

interface DiagramControlsProps {
  onExportSvg?: () => void;
  onExportPng?: () => void;
  showBoundaries: boolean;
  onToggleBoundaries: () => void;
}

export default function DiagramControls({
  onExportSvg,
  onExportPng,
  showBoundaries,
  onToggleBoundaries,
}: DiagramControlsProps) {
  const btnStyle: React.CSSProperties = {
    padding: "4px 10px",
    borderRadius: 4,
    border: "1px solid #e2e8f0",
    background: "#ffffff",
    color: "#475569",
    cursor: "pointer",
    fontSize: 11,
  };
  return (
    <div
      style={{
        position: "absolute",
        top: 16,
        right: 16,
        zIndex: 10,
        display: "flex",
        gap: 4,
        background: "#ffffff",
        padding: 4,
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
      }}
    >
      {onExportSvg && (
        <button style={btnStyle} onClick={onExportSvg}>
          Export SVG
        </button>
      )}
      {onExportPng && (
        <button style={btnStyle} onClick={onExportPng}>
          Export PNG
        </button>
      )}
      <button
        style={{ ...btnStyle, background: showBoundaries ? "#f1f5f9" : "#ffffff" }}
        onClick={onToggleBoundaries}
      >
        {showBoundaries ? "Hide" : "Show"} Boundaries
      </button>
    </div>
  );
}
