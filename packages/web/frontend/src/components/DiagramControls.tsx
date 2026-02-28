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
    border: "1px solid #334155",
    background: "#1e293b",
    color: "#94a3b8",
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
        background: "#0f172a",
        padding: 4,
        border: "1px solid #1e293b",
        borderRadius: 8,
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
        style={{ ...btnStyle, background: showBoundaries ? "#334155" : "#1e293b" }}
        onClick={onToggleBoundaries}
      >
        {showBoundaries ? "Hide" : "Show"} Boundaries
      </button>
    </div>
  );
}
