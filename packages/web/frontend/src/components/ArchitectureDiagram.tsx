import React, { useMemo, useState, useCallback, useEffect } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import CloudServiceNode from "./CloudServiceNode";
import DiagramLegend from "./DiagramLegend";
import DiagramControls from "./DiagramControls";
import NodeSidePanel from "./NodeSidePanel";

interface Component {
  id: string;
  service: string;
  provider: string;
  label: string;
  description: string;
  tier: number;
  config?: Record<string, unknown>;
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

const NODE_WIDTH = 200;
const NODE_HEIGHT = 90;
const H_GAP = 300;
const V_GAP = 240;
const BOUNDARY_PADDING = 32;
const MAX_PER_ROW = 4;

// Custom node type registry — must be stable (defined outside component)
const nodeTypes = { cloudService: CloudServiceNode };

function buildNodes(
  spec: ArchSpec,
  showBoundaries: boolean,
  costMap: Record<string, number>
): Node[] {
  const nodes: Node[] = [];
  const boundaries = spec.boundaries || [];

  // Map component_id -> boundary id (first boundary that contains it)
  const compBoundary: Record<string, string> = {};
  if (showBoundaries) {
    for (const b of boundaries) {
      for (const cid of b.component_ids) {
        if (!compBoundary[cid]) compBoundary[cid] = b.id;
      }
    }
  }

  // Group components by tier
  const tierGroups: Record<number, Component[]> = {};
  for (const comp of spec.components) {
    const tier = comp.tier ?? 2;
    if (!tierGroups[tier]) tierGroups[tier] = [];
    tierGroups[tier].push(comp);
  }

  const sortedTiers = Object.keys(tierGroups).map(Number).sort();

  // Two-pass layout: first compute tier Y origins (accounting for multi-row tiers),
  // then position each component within its tier.
  const compPositions: Record<string, { x: number; y: number }> = {};
  let yOffset = 40;
  const tierBaseY: Record<number, number> = {};
  for (const tier of sortedTiers) {
    tierBaseY[tier] = yOffset;
    const rows = Math.ceil(tierGroups[tier].length / MAX_PER_ROW);
    yOffset += V_GAP + (rows - 1) * (NODE_HEIGHT + 60);
  }

  for (const tier of sortedTiers) {
    const comps = tierGroups[tier];
    const baseY = tierBaseY[tier];
    for (let i = 0; i < comps.length; i++) {
      const row = Math.floor(i / MAX_PER_ROW);
      const col = i % MAX_PER_ROW;
      const rowCount = Math.min(MAX_PER_ROW, comps.length - row * MAX_PER_ROW);
      const totalWidth = rowCount * H_GAP;
      const startX = (1200 - totalWidth) / 2;
      compPositions[comps[i].id] = { x: startX + col * H_GAP, y: baseY + row * (NODE_HEIGHT + 60) };
    }
  }

  // Build boundary group nodes
  if (showBoundaries && boundaries.length > 0) {
    for (const b of boundaries) {
      if (b.component_ids.length === 0) continue;

      // Compute bounding box from contained components
      const xs = b.component_ids.map((cid) => compPositions[cid]?.x ?? 0);
      const ys = b.component_ids.map((cid) => compPositions[cid]?.y ?? 0);
      const minX = Math.min(...xs) - BOUNDARY_PADDING;
      const minY = Math.min(...ys) - BOUNDARY_PADDING - 24; // room for label
      const maxX = Math.max(...xs) + NODE_WIDTH + BOUNDARY_PADDING;
      const maxY = Math.max(...ys) + NODE_HEIGHT + BOUNDARY_PADDING;

      const borderStyle =
        b.kind === "vpc"
          ? "2px dashed #cbd5e1"
          : b.kind === "subnet"
          ? "2px solid #cbd5e1"
          : "2px dotted #cbd5e1";

      nodes.push({
        id: `boundary-${b.id}`,
        type: "group",
        position: { x: minX, y: minY },
        data: { label: b.label || b.id },
        style: {
          background: "transparent",
          border: borderStyle,
          borderRadius: 12,
          padding: BOUNDARY_PADDING,
          width: maxX - minX,
          height: maxY - minY,
          fontSize: 11,
          color: "#64748b",
          fontWeight: 600,
        },
        // groups render behind their children
        zIndex: -1,
        draggable: false,
      });
    }
  }

  // Build component nodes
  for (const tier of sortedTiers) {
    const comps = tierGroups[tier];

    for (let i = 0; i < comps.length; i++) {
      const comp = comps[i];
      const boundaryId = compBoundary[comp.id];
      const boundaryNode = showBoundaries && boundaryId
        ? nodes.find((n) => n.id === `boundary-${boundaryId}`)
        : undefined;

      // Use pre-computed absolute positions; adjust for boundary parent offset
      let posX = compPositions[comp.id]?.x ?? 0;
      let posY = compPositions[comp.id]?.y ?? 0;
      if (boundaryNode) {
        posX -= boundaryNode.position.x;
        posY -= boundaryNode.position.y;
      }

      nodes.push({
        id: comp.id,
        type: "cloudService",
        position: { x: posX, y: posY },
        data: {
          label: comp.label,
          service: comp.service,
          provider: comp.provider,
          description: comp.description,
          tier: comp.tier,
          config: comp.config || {},
          monthlyCost: costMap[comp.id],
        },
        parentId: boundaryNode ? `boundary-${boundaryId}` : undefined,
        extent: boundaryNode ? "parent" : undefined,
      });
    }
  }

  return nodes;
}

function buildEdges(spec: ArchSpec): Edge[] {
  return spec.connections.map((conn, i) => {
    let edgeLabel = conn.label || "";
    if (conn.protocol && !edgeLabel.includes(conn.protocol)) {
      edgeLabel = conn.protocol + (conn.port ? `:${conn.port}` : "");
    }
    return {
      id: `e${i}`,
      source: conn.source,
      target: conn.target,
      label: edgeLabel,
      style: { stroke: "#94a3b8" },
      labelStyle: { fill: "#64748b", fontSize: 11 },
      animated: true,
    };
  });
}

function ArchitectureDiagram({ spec }: { spec: ArchSpec }) {
  const [showBoundaries, setShowBoundaries] = useState(true);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const costMap = useMemo<Record<string, number>>(() => {
    const m: Record<string, number> = {};
    for (const item of spec.cost_estimate?.breakdown ?? []) {
      m[item.component_id] = item.monthly;
    }
    return m;
  }, [spec.cost_estimate]);

  const selectedComponent = useMemo(
    () => (selectedNode ? spec.components.find((c) => c.id === selectedNode) ?? null : null),
    [selectedNode, spec.components]
  );

  const selectedCost = useMemo(
    () =>
      selectedNode
        ? (spec.cost_estimate?.breakdown.find((b) => b.component_id === selectedNode) ?? null)
        : null,
    [selectedNode, spec.cost_estimate]
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    // Only open panel for component nodes, not boundary groups
    if (!node.id.startsWith("boundary-")) {
      setSelectedNode(node.id);
    }
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    setNodes(buildNodes(spec, showBoundaries, costMap));
    setEdges(buildEdges(spec));
  }, [spec, showBoundaries, costMap]);

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        proOptions={{ hideAttribution: true }}
        style={{ background: "#f8fafc" }}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
      >
        <Background color="#e2e8f0" gap={20} />
        <Controls
          style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 8 }}
        />
      </ReactFlow>
      <DiagramLegend components={spec.components} />
      <DiagramControls
        showBoundaries={showBoundaries}
        onToggleBoundaries={() => setShowBoundaries((v) => !v)}
      />
      <NodeSidePanel
        component={selectedComponent ?? null}
        cost={selectedCost}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
}

export default ArchitectureDiagram;
