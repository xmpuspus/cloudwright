import React from "react";
import { NodeResizer } from "@xyflow/react";

interface BoundaryNodeData {
  label: string;
  labelColor: string;
  labelBg: string;
  dotColor: string;
  [key: string]: unknown;
}

function BoundaryNode({ data, selected }: { data: BoundaryNodeData; selected?: boolean }) {
  return (
    <>
      <NodeResizer
        color={data.dotColor}
        isVisible={selected ?? false}
        minWidth={200}
        minHeight={100}
        lineStyle={{ borderWidth: 1.5 }}
        handleStyle={{ width: 8, height: 8, borderRadius: 2 }}
      />
      <div
        style={{
          position: "absolute",
          top: 6,
          left: 8,
          display: "inline-flex",
          alignItems: "center",
          gap: 5,
          padding: "3px 10px 3px 7px",
          borderRadius: 5,
          background: data.labelBg,
          border: `1px solid ${data.dotColor}30`,
          boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
          pointerEvents: "none",
        }}
      >
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: data.dotColor,
            flexShrink: 0,
          }}
        />
        <span
          style={{
            color: data.labelColor,
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.02em",
            whiteSpace: "nowrap",
            lineHeight: 1,
          }}
        >
          {data.label}
        </span>
      </div>
    </>
  );
}

export default BoundaryNode;
