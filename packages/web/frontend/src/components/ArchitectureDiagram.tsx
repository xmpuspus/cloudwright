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
import BoundaryNode from "./BoundaryNode";
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
const VPC_LABEL_EXTRA = 36;
const MAX_PER_ROW = 4;

const TIER_LABELS: Record<number, string> = {
  0: "Edge / CDN",
  1: "Network / Ingress",
  2: "Application",
  3: "Data Layer",
  4: "Platform Services",
  5: "Platform Services",
};

const TIER_KINDS: Record<number, string> = {
  0: "edge",
  1: "subnet",
  2: "subnet",
  3: "subnet",
};

interface BoundaryStyle {
  border: string;
  bg: string;
  labelColor: string;
  labelBg: string;
  dot: string;
}

const TIER_COLORS: Record<number, BoundaryStyle> = {
  0: { border: "#60a5fa", bg: "rgba(219, 234, 254, 0.18)", labelColor: "#1d4ed8", labelBg: "rgba(219, 234, 254, 0.92)", dot: "#3b82f6" },
  1: { border: "#34d399", bg: "rgba(209, 250, 229, 0.18)", labelColor: "#047857", labelBg: "rgba(209, 250, 229, 0.92)", dot: "#10b981" },
  2: { border: "#fb923c", bg: "rgba(255, 237, 213, 0.18)", labelColor: "#9a3412", labelBg: "rgba(255, 237, 213, 0.92)", dot: "#f97316" },
  3: { border: "#a78bfa", bg: "rgba(237, 233, 254, 0.18)", labelColor: "#5b21b6", labelBg: "rgba(237, 233, 254, 0.92)", dot: "#8b5cf6" },
  4: { border: "#2dd4bf", bg: "rgba(204, 251, 241, 0.18)", labelColor: "#0f766e", labelBg: "rgba(204, 251, 241, 0.92)", dot: "#14b8a6" },
  5: { border: "#2dd4bf", bg: "rgba(204, 251, 241, 0.18)", labelColor: "#0f766e", labelBg: "rgba(204, 251, 241, 0.92)", dot: "#14b8a6" },
};

const VPC_COLORS: BoundaryStyle = {
  border: "#94a3b8", bg: "rgba(241, 245, 249, 0.35)", labelColor: "#475569", labelBg: "rgba(241, 245, 249, 0.92)", dot: "#94a3b8",
};

function getBoundaryColors(boundaryId: string, kind: string): BoundaryStyle {
  if (kind === "vpc") return VPC_COLORS;
  const tierMatch = boundaryId.match(/^tier-(\d+)$/);
  if (tierMatch) return TIER_COLORS[parseInt(tierMatch[1])] || TIER_COLORS[2];
  return TIER_COLORS[2];
}

function inferBoundaries(components: Component[]): Boundary[] {
  const tierGroups: Record<number, string[]> = {};
  for (const c of components) {
    const t = c.tier ?? 2;
    if (!tierGroups[t]) tierGroups[t] = [];
    tierGroups[t].push(c.id);
  }

  const tiers = Object.keys(tierGroups).map(Number).sort();
  const boundaries: Boundary[] = [];

  for (const t of tiers) {
    boundaries.push({
      id: `tier-${t}`,
      kind: TIER_KINDS[t] || "subnet",
      label: TIER_LABELS[t] || `Tier ${t}`,
      component_ids: tierGroups[t],
    });
  }

  // Wrap non-edge tiers in a VPC boundary if there are inner boundaries
  const innerIds = boundaries.filter((b) => b.id !== "tier-0").flatMap((b) => b.component_ids);
  if (innerIds.length >= 2) {
    boundaries.unshift({
      id: "vpc",
      kind: "vpc",
      label: "VPC / Virtual Network",
      component_ids: innerIds,
    });
  }

  return boundaries;
}

// Custom node type registry — must be stable (defined outside component)
const nodeTypes = { cloudService: CloudServiceNode, boundaryGroup: BoundaryNode };

function buildNodes(
  spec: ArchSpec,
  showBoundaries: boolean,
  costMap: Record<string, number>
): Node[] {
  const nodes: Node[] = [];
  const explicitBoundaries = spec.boundaries || [];
  const boundaries = explicitBoundaries.length > 0 ? explicitBoundaries : inferBoundaries(spec.components);

  // Map component_id -> most specific boundary (skip VPC — it's visual-only)
  const compBoundary: Record<string, string> = {};
  if (showBoundaries) {
    for (const b of boundaries) {
      if (b.kind === "vpc") continue;
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

  // Track absolute positions of boundaries (for computing child offsets)
  const boundaryAbsPos: Record<string, { x: number; y: number }> = {};

  // Build boundary group nodes in two phases: VPC first, then tier boundaries
  if (showBoundaries && boundaries.length > 0) {
    const vpcBoundary = boundaries.find((b) => b.kind === "vpc");
    let vpcNodeId: string | undefined;

    // Phase 1: Build VPC boundary (outermost container)
    if (vpcBoundary && vpcBoundary.component_ids.length > 0) {
      const xs = vpcBoundary.component_ids.map((cid) => compPositions[cid]?.x ?? 0);
      const ys = vpcBoundary.component_ids.map((cid) => compPositions[cid]?.y ?? 0);
      const minX = Math.min(...xs) - BOUNDARY_PADDING;
      const minY = Math.min(...ys) - BOUNDARY_PADDING - 24 - VPC_LABEL_EXTRA;
      const maxX = Math.max(...xs) + NODE_WIDTH + BOUNDARY_PADDING;
      const maxY = Math.max(...ys) + NODE_HEIGHT + BOUNDARY_PADDING;

      vpcNodeId = `boundary-${vpcBoundary.id}`;
      boundaryAbsPos[vpcBoundary.id] = { x: minX, y: minY };

      nodes.push({
        id: vpcNodeId,
        type: "boundaryGroup",
        position: { x: minX, y: minY },
        data: {
          label: vpcBoundary.label || vpcBoundary.id,
          labelColor: VPC_COLORS.labelColor,
          labelBg: VPC_COLORS.labelBg,
          dotColor: VPC_COLORS.dot,
        },
        style: {
          background: VPC_COLORS.bg,
          border: `2px dashed ${VPC_COLORS.border}`,
          borderRadius: 16,
          padding: BOUNDARY_PADDING,
          width: maxX - minX,
          height: maxY - minY,
        },
        zIndex: -2,
      });
    }

    // Phase 2: Build tier boundaries (nested inside VPC when applicable)
    for (const b of boundaries) {
      if (b.kind === "vpc") continue;
      if (b.component_ids.length === 0) continue;

      const xs = b.component_ids.map((cid) => compPositions[cid]?.x ?? 0);
      const ys = b.component_ids.map((cid) => compPositions[cid]?.y ?? 0);
      const minX = Math.min(...xs) - BOUNDARY_PADDING;
      const minY = Math.min(...ys) - BOUNDARY_PADDING - 24;
      const maxX = Math.max(...xs) + NODE_WIDTH + BOUNDARY_PADDING;
      const maxY = Math.max(...ys) + NODE_HEIGHT + BOUNDARY_PADDING;

      boundaryAbsPos[b.id] = { x: minX, y: minY };
      const colors = getBoundaryColors(b.id, b.kind);

      // Nest inside VPC if this tier shares components with it
      const isInsideVpc = vpcNodeId && vpcBoundary &&
        b.component_ids.some((cid) => vpcBoundary.component_ids.includes(cid));

      const position = isInsideVpc
        ? { x: minX - boundaryAbsPos[vpcBoundary!.id].x, y: minY - boundaryAbsPos[vpcBoundary!.id].y }
        : { x: minX, y: minY };

      nodes.push({
        id: `boundary-${b.id}`,
        type: "boundaryGroup",
        position,
        data: {
          label: b.label || b.id,
          labelColor: colors.labelColor,
          labelBg: colors.labelBg,
          dotColor: colors.dot,
        },
        style: {
          background: colors.bg,
          border: `1.5px solid ${colors.border}`,
          borderRadius: 10,
          padding: BOUNDARY_PADDING,
          width: maxX - minX,
          height: maxY - minY,
        },
        zIndex: -1,
        parentId: isInsideVpc ? vpcNodeId : undefined,
      });
    }
  }

  // Build component nodes
  for (const tier of sortedTiers) {
    const comps = tierGroups[tier];

    for (let i = 0; i < comps.length; i++) {
      const comp = comps[i];
      const boundaryId = compBoundary[comp.id];
      const hasBoundary = showBoundaries && boundaryId && boundaryAbsPos[boundaryId];

      // Position relative to parent boundary using absolute offsets
      let posX = compPositions[comp.id]?.x ?? 0;
      let posY = compPositions[comp.id]?.y ?? 0;
      if (hasBoundary) {
        posX -= boundaryAbsPos[boundaryId].x;
        posY -= boundaryAbsPos[boundaryId].y;
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
        parentId: hasBoundary ? `boundary-${boundaryId}` : undefined,
        extent: hasBoundary ? "parent" : undefined,
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
