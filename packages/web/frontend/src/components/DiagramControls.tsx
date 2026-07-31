import React from "react";
import Icon from "./Icon";

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
  return (
    <div
      className="float-panel"
      style={{
        top: "var(--space-4)",
        right: "var(--space-4)",
        display: "flex",
        gap: 4,
        padding: 4,
      }}
      role="group"
      aria-label="Diagram controls"
    >
      {onExportSvg && (
        <button className="btn btn--ghost btn--sm" onClick={onExportSvg} title="Download the diagram as SVG">
          <Icon name="download" size={13} />
          SVG
        </button>
      )}
      {onExportPng && (
        <button className="btn btn--ghost btn--sm" onClick={onExportPng} title="Download the diagram as PNG">
          <Icon name="download" size={13} />
          PNG
        </button>
      )}
      <button
        className="btn btn--ghost btn--sm"
        onClick={onToggleBoundaries}
        aria-pressed={showBoundaries}
        title="Show or hide the trust boundaries"
      >
        <Icon name="panel" size={13} />
        <span className="hide-narrow">Boundaries</span>
      </button>
    </div>
  );
}
