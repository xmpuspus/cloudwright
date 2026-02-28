import React, { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

interface Component {
  id: string;
  service: string;
  provider: string;
  label: string;
  description: string;
  tier: number;
}

interface Connection {
  source: string;
  target: string;
  label: string;
  protocol?: string;
  port?: number;
}

interface Boundary {
  id: string;
  kind: string;
  label?: string;
  parent?: string;
  component_ids: string[];
  config?: Record<string, unknown>;
}

interface CostEstimate {
  monthly_total: number;
  breakdown: { component_id: string; service: string; monthly: number; notes: string }[];
  currency: string;
}

interface ArchSpec {
  name: string;
  components: Component[];
  connections: Connection[];
  boundaries?: Boundary[];
  cost_estimate?: CostEstimate;
}

const TIER_COLORS: Record<number, string> = {
  0: "#f59e0b",
  1: "#3b82f6",
  2: "#10b981",
  3: "#8b5cf6",
  4: "#6366f1",
};

const TIER_LABELS: Record<number, string> = {
  0: "Edge",
  1: "Ingress",
  2: "Compute",
  3: "Data",
  4: "Storage",
};

function ArchitectureDiagram({ spec }: { spec: ArchSpec }) {
  const { nodes, edges } = useMemo(() => {
    const tierGroups: Record<number, Component[]> = {};
    for (const comp of spec.components) {
      const tier = comp.tier ?? 2;
      if (!tierGroups[tier]) tierGroups[tier] = [];
      tierGroups[tier].push(comp);
    }

    const n: Node[] = [];
    const sortedTiers = Object.keys(tierGroups)
      .map(Number)
      .sort();

    for (const tier of sortedTiers) {
      const comps = tierGroups[tier];
      const y = tier * 180 + 40;
      const totalWidth = comps.length * 220;
      const startX = (800 - totalWidth) / 2;

      for (let i = 0; i < comps.length; i++) {
        const comp = comps[i];
        n.push({
          id: comp.id,
          position: { x: startX + i * 220, y },
          data: {
            label: (
              <div style={{ textAlign: "center" }}>
                <div
                  style={{
                    fontSize: 10,
                    color: TIER_COLORS[tier] || "#94a3b8",
                    textTransform: "uppercase",
                    letterSpacing: 1,
                    marginBottom: 4,
                  }}
                >
                  {TIER_LABELS[tier] || `Tier ${tier}`}
                </div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{comp.label}</div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                  {comp.service} ({comp.provider})
                </div>
              </div>
            ),
          },
          style: {
            background: "#1e293b",
            border: `2px solid ${TIER_COLORS[tier] || "#334155"}`,
            borderRadius: 8,
            padding: "12px 16px",
            color: "#f8fafc",
            width: 200,
          },
        });
      }
    }

    const e: Edge[] = spec.connections.map((conn, i) => {
      let edgeLabel = conn.label || "";
      if (conn.protocol && !edgeLabel.includes(conn.protocol)) {
        edgeLabel = conn.protocol + (conn.port ? `:${conn.port}` : "");
      }
      return {
        id: `e${i}`,
        source: conn.source,
        target: conn.target,
        label: edgeLabel,
        style: { stroke: "#475569" },
        labelStyle: { fill: "#94a3b8", fontSize: 11 },
        animated: true,
      };
    });

    return { nodes: n, edges: e };
  }, [spec]);

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        proOptions={{ hideAttribution: true }}
        style={{ background: "#0f172a" }}
      >
        <Background color="#1e293b" gap={20} />
        <Controls
          style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
        />
      </ReactFlow>
    </div>
  );
}

export default ArchitectureDiagram;
