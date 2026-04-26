import React, { useMemo, useState, useCallback, useEffect } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type Connection as FlowConnection,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import CloudServiceNode from "./CloudServiceNode";
import BoundaryNode from "./BoundaryNode";
import DiagramLegend from "./DiagramLegend";
import DiagramControls from "./DiagramControls";
import NodeSidePanel from "./NodeSidePanel";
import CatalogDrawer from "./CatalogDrawer";

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

interface TerraformModuleRef {
  source: string;
  version?: string;
}

interface ModuleInstanceMetadata {
  module_id: string;
  module_version?: string;
  component_ids: string[];
  expected_component_count?: number;
  required_tags?: string[];
  naming_prefix?: string;
  approved?: boolean;
  terraform?: TerraformModuleRef;
  partial?: boolean;
}

interface ArchMetadata {
  canvas?: { nodes?: Record<string, { x: number; y: number }> };
  modules?: { instances?: Record<string, ModuleInstanceMetadata> };
  suggestions?: string[];
  [key: string]: unknown;
}

interface ArchSpec {
  name: string;
  provider: string;
  region: string;
  components: Component[];
  connections: Connection[];
  boundaries?: Boundary[];
  cost_estimate?: CostEstimate;
  metadata?: ArchMetadata;
}

interface ServiceSummary {
  service_key: string;
  provider: string;
  category: string;
  name: string;
  description?: string;
  default_config?: Record<string, unknown>;
}

interface ModuleDetail {
  id: string;
  name: string;
  provider: string;
  category: string;
  description?: string;
  approved: boolean;
  required_tags: string[];
  default_tags?: Record<string, string>;
  naming: { component_id_prefix: string };
  terraform: TerraformModuleRef;
  fragment: {
    components: Component[];
    connections: Connection[];
  };
}

interface StandardViolation {
  code: string;
  severity: string;
  message: string;
  component_id?: string | null;
  module_instance_id?: string | null;
}

interface StandardsResult {
  passed: boolean;
  violations: StandardViolation[];
}

const NODE_WIDTH = 200;
const NODE_HEIGHT = 90;
const H_GAP = 300;
const V_GAP = 240;
const BOUNDARY_PADDING = 32;
const VPC_LABEL_EXTRA = 36;
const MAX_PER_ROW = 4;
const API_BASE = "/api";

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
  border: "#94a3b8",
  bg: "rgba(241, 245, 249, 0.35)",
  labelColor: "#475569",
  labelBg: "rgba(241, 245, 249, 0.92)",
  dot: "#94a3b8",
};

const nodeTypes = { cloudService: CloudServiceNode, boundaryGroup: BoundaryNode };

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function cloneMetadata(metadata?: ArchMetadata): ArchMetadata {
  return cloneJson(metadata ?? {});
}

function safeId(value: string, fallback = "resource"): string {
  let id = value.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "_").replace(/^[_-]+|[_-]+$/g, "");
  if (!id) id = fallback;
  if (!/^[a-z_]/.test(id)) id = `${fallback}_${id}`;
  return id;
}

function uniqueId(base: string, used: Set<string>): string {
  let candidate = base;
  let suffix = 2;
  while (used.has(candidate)) {
    candidate = `${base}-${suffix}`;
    suffix += 1;
  }
  used.add(candidate);
  return candidate;
}

function tierForCategory(category: string): number {
  const key = category.toLowerCase();
  if (key.includes("cdn") || key.includes("edge")) return 0;
  if (key.includes("network") || key.includes("security")) return 1;
  if (key.includes("database") || key.includes("cache")) return 3;
  if (key.includes("storage") || key.includes("analytics") || key.includes("data")) return 4;
  return 2;
}

function newNodePosition(index: number): { x: number; y: number } {
  return {
    x: 360 + (index % 3) * 260,
    y: 80 + Math.floor(index / 3) * 150,
  };
}

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

function buildNodes(
  spec: ArchSpec,
  showBoundaries: boolean,
  costMap: Record<string, number>
): Node[] {
  const nodes: Node[] = [];
  const explicitBoundaries = spec.boundaries || [];
  const boundaries = explicitBoundaries.length > 0 ? explicitBoundaries : inferBoundaries(spec.components);
  const savedPositions = spec.metadata?.canvas?.nodes ?? {};

  const compBoundary: Record<string, string> = {};
  if (showBoundaries) {
    for (const b of boundaries) {
      if (b.kind === "vpc") continue;
      for (const cid of b.component_ids) {
        if (!compBoundary[cid]) compBoundary[cid] = b.id;
      }
    }
  }

  const tierGroups: Record<number, Component[]> = {};
  for (const comp of spec.components) {
    const tier = comp.tier ?? 2;
    if (!tierGroups[tier]) tierGroups[tier] = [];
    tierGroups[tier].push(comp);
  }

  const sortedTiers = Object.keys(tierGroups).map(Number).sort();
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
      const generated = { x: startX + col * H_GAP, y: baseY + row * (NODE_HEIGHT + 60) };
      const saved = savedPositions[comps[i].id];
      compPositions[comps[i].id] =
        saved && Number.isFinite(saved.x) && Number.isFinite(saved.y) ? saved : generated;
    }
  }

  const boundaryAbsPos: Record<string, { x: number; y: number }> = {};

  if (showBoundaries && boundaries.length > 0) {
    const vpcBoundary = boundaries.find((b) => b.kind === "vpc");
    let vpcNodeId: string | undefined;

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

    for (const b of boundaries) {
      if (b.kind === "vpc" || b.component_ids.length === 0) continue;

      const xs = b.component_ids.map((cid) => compPositions[cid]?.x ?? 0);
      const ys = b.component_ids.map((cid) => compPositions[cid]?.y ?? 0);
      const minX = Math.min(...xs) - BOUNDARY_PADDING;
      const minY = Math.min(...ys) - BOUNDARY_PADDING - 24;
      const maxX = Math.max(...xs) + NODE_WIDTH + BOUNDARY_PADDING;
      const maxY = Math.max(...ys) + NODE_HEIGHT + BOUNDARY_PADDING;

      boundaryAbsPos[b.id] = { x: minX, y: minY };
      const colors = getBoundaryColors(b.id, b.kind);
      const isInsideVpc = Boolean(
        vpcNodeId && vpcBoundary && b.component_ids.some((cid) => vpcBoundary.component_ids.includes(cid))
      );

      nodes.push({
        id: `boundary-${b.id}`,
        type: "boundaryGroup",
        position: isInsideVpc
          ? { x: minX - boundaryAbsPos[vpcBoundary!.id].x, y: minY - boundaryAbsPos[vpcBoundary!.id].y }
          : { x: minX, y: minY },
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

  for (const tier of sortedTiers) {
    const comps = tierGroups[tier];
    for (const comp of comps) {
      const boundaryId = compBoundary[comp.id];
      const hasBoundary = showBoundaries && boundaryId && boundaryAbsPos[boundaryId];
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

function connectionEdgeId(conn: Connection, index: number): string {
  return `edge:${conn.source}:${conn.target}:${index}`;
}

function buildEdges(spec: ArchSpec): Edge[] {
  return spec.connections.map((conn, i) => {
    let edgeLabel = conn.label || "";
    if (conn.protocol && !edgeLabel.includes(conn.protocol)) {
      edgeLabel = conn.protocol + (conn.port ? `:${conn.port}` : "");
    }
    return {
      id: connectionEdgeId(conn, i),
      source: conn.source,
      target: conn.target,
      label: edgeLabel,
      style: { stroke: "#94a3b8" },
      labelStyle: { fill: "#64748b", fontSize: 11 },
      animated: true,
    };
  });
}

function updateBoundariesAfterDelete(boundaries: Boundary[] | undefined, componentId: string): Boundary[] | undefined {
  if (!boundaries) return boundaries;
  return boundaries.map((boundary) => ({
    ...boundary,
    component_ids: boundary.component_ids.filter((id) => id !== componentId),
  }));
}

function ArchitectureDiagram({
  spec,
  onSpecChange,
}: {
  spec: ArchSpec;
  onSpecChange: (spec: ArchSpec) => void | Promise<void>;
}) {
  const [showBoundaries, setShowBoundaries] = useState(true);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [standardsResult, setStandardsResult] = useState<StandardsResult | null>(null);

  const applySpec = useCallback((nextSpec: ArchSpec) => {
    setStandardsResult(null);
    void onSpecChange(nextSpec);
  }, [onSpecChange]);

  const handleExport = useCallback(async (format: "svg" | "png") => {
    try {
      const res = await fetch(`${API_BASE}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spec, format }),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `architecture.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // export is best-effort
    }
  }, [spec]);

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

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    setNodes(buildNodes(spec, showBoundaries, costMap));
    setEdges(buildEdges(spec));
  }, [spec, showBoundaries, costMap, setNodes, setEdges]);

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    if (!node.id.startsWith("boundary-")) {
      setSelectedNode(node.id);
    }
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleNodeDragStop = useCallback((_event: React.MouseEvent, node: Node) => {
    if (node.id.startsWith("boundary-")) return;
    const metadata = cloneMetadata(spec.metadata);
    const canvas = metadata.canvas ?? {};
    const canvasNodes = { ...(canvas.nodes ?? {}) };
    const parentNode = nodes.find((candidate) => candidate.id === node.parentId);
    const absolutePosition = parentNode
      ? { x: parentNode.position.x + node.position.x, y: parentNode.position.y + node.position.y }
      : { x: node.position.x, y: node.position.y };
    canvasNodes[node.id] = absolutePosition;
    metadata.canvas = { ...canvas, nodes: canvasNodes };
    applySpec({ ...spec, metadata });
  }, [applySpec, nodes, spec]);

  const handleConnect = useCallback((connection: FlowConnection) => {
    if (!connection.source || !connection.target || connection.source === connection.target) return;
    const exists = spec.connections.some(
      (conn) => conn.source === connection.source && conn.target === connection.target
    );
    if (exists) return;
    applySpec({
      ...spec,
      connections: [
        ...spec.connections,
        {
          source: connection.source,
          target: connection.target,
          label: "HTTPS",
          protocol: "HTTPS",
          port: 443,
        },
      ],
    });
  }, [applySpec, spec]);

  const handleEdgesDelete = useCallback((deleted: Edge[]) => {
    if (deleted.length === 0) return;
    if (!window.confirm(`Delete ${deleted.length === 1 ? "this connection" : "these connections"}?`)) {
      setEdges(buildEdges(spec));
      return;
    }
    const deletedIds = new Set(deleted.map((edge) => edge.id));
    applySpec({
      ...spec,
      connections: spec.connections.filter((conn, index) => !deletedIds.has(connectionEdgeId(conn, index))),
    });
  }, [applySpec, setEdges, spec]);

  const handleApplyComponent = useCallback((updated: Component) => {
    applySpec({
      ...spec,
      components: spec.components.map((component) => (component.id === updated.id ? updated : component)),
    });
  }, [applySpec, spec]);

  const handleDeleteComponent = useCallback((componentId: string) => {
    const component = spec.components.find((candidate) => candidate.id === componentId);
    if (!component) return;
    if (!window.confirm(`Delete ${component.label || component.id} and its connections?`)) return;

    const metadata = cloneMetadata(spec.metadata);
    if (metadata.canvas?.nodes) {
      delete metadata.canvas.nodes[componentId];
    }

    const instances = metadata.modules?.instances ?? {};
    for (const instance of Object.values(instances)) {
      if (!instance.component_ids.includes(componentId)) continue;
      instance.component_ids = instance.component_ids.filter((id) => id !== componentId);
      instance.partial = true;
      instance.approved = false;
      delete instance.terraform;
    }
    if (metadata.modules) {
      metadata.modules.instances = instances;
    }

    applySpec({
      ...spec,
      components: spec.components.filter((candidate) => candidate.id !== componentId),
      connections: spec.connections.filter((conn) => conn.source !== componentId && conn.target !== componentId),
      boundaries: updateBoundariesAfterDelete(spec.boundaries, componentId),
      metadata,
    });
    setSelectedNode(null);
  }, [applySpec, spec]);

  const handleAddResource = useCallback((service: ServiceSummary) => {
    const used = new Set(spec.components.map((component) => component.id));
    const id = uniqueId(safeId(service.service_key), used);
    const metadata = cloneMetadata(spec.metadata);
    const canvas = metadata.canvas ?? {};
    const canvasNodes = { ...(canvas.nodes ?? {}) };
    canvasNodes[id] = newNodePosition(Object.keys(canvasNodes).length + spec.components.length);
    metadata.canvas = { ...canvas, nodes: canvasNodes };

    const component: Component = {
      id,
      service: service.service_key,
      provider: service.provider.toLowerCase(),
      label: service.name,
      description: service.description ?? "",
      tier: tierForCategory(service.category),
      config: cloneJson(service.default_config ?? {}),
    };

    applySpec({
      ...spec,
      components: [...spec.components, component],
      metadata,
    });
    setSelectedNode(id);
  }, [applySpec, spec]);

  const handleAddModule = useCallback(async (moduleId: string) => {
    try {
      const response = await fetch(`${API_BASE}/modules/${encodeURIComponent(moduleId)}`);
      if (!response.ok) return;
      const data = (await response.json()) as { module: ModuleDetail };
      const module = data.module;
      const usedComponents = new Set(spec.components.map((component) => component.id));
      const metadata = cloneMetadata(spec.metadata);
      const modules = metadata.modules ?? {};
      const instances = { ...(modules.instances ?? {}) };
      const usedInstances = new Set(Object.keys(instances));
      const instanceId = uniqueId(safeId(module.id, "module"), usedInstances);
      const prefix = safeId(module.naming.component_id_prefix, instanceId);
      const remap: Record<string, string> = {};

      for (const component of module.fragment.components) {
        remap[component.id] = uniqueId(safeId(`${prefix}_${component.id}`, prefix), usedComponents);
      }

      const canvas = metadata.canvas ?? {};
      const canvasNodes = { ...(canvas.nodes ?? {}) };
      const baseIndex = Object.keys(canvasNodes).length + spec.components.length;
      const addedComponents = module.fragment.components.map((component, index) => {
        const nextConfig = cloneJson(component.config ?? {});
        const tags = {
          ...(module.default_tags ?? {}),
          ...((typeof nextConfig.tags === "object" && nextConfig.tags !== null ? nextConfig.tags : {}) as Record<string, string>),
        };
        nextConfig.tags = tags;
        const id = remap[component.id];
        canvasNodes[id] = newNodePosition(baseIndex + index);
        return {
          ...component,
          id,
          provider: component.provider.toLowerCase(),
          config: nextConfig,
        };
      });

      const addedConnections = module.fragment.connections.map((connection) => ({
        ...connection,
        source: remap[connection.source],
        target: remap[connection.target],
      }));

      instances[instanceId] = {
        module_id: module.id,
        module_version: module.terraform.version,
        component_ids: addedComponents.map((component) => component.id),
        expected_component_count: addedComponents.length,
        required_tags: [...module.required_tags],
        naming_prefix: prefix,
        approved: module.approved,
        terraform: { ...module.terraform },
      };
      metadata.canvas = { ...canvas, nodes: canvasNodes };
      metadata.modules = { ...modules, instances };

      applySpec({
        ...spec,
        components: [...spec.components, ...addedComponents],
        connections: [...spec.connections, ...addedConnections],
        metadata,
      });
      setSelectedNode(addedComponents[0]?.id ?? null);
    } catch {
      // module insertion is best-effort
    }
  }, [applySpec, spec]);

  const handleCheckStandards = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/canvas/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spec }),
      });
      if (!response.ok) return;
      setStandardsResult((await response.json()) as StandardsResult);
    } catch {
      setStandardsResult({
        passed: false,
        violations: [{ code: "request_failed", severity: "error", message: "Standards check failed." }],
      });
    }
  }, [spec]);

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <CatalogDrawer
        provider={spec.provider || "aws"}
        standardsResult={standardsResult}
        onAddResource={handleAddResource}
        onAddModule={handleAddModule}
        onCheckStandards={handleCheckStandards}
      />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onEdgesDelete={handleEdgesDelete}
        onConnect={handleConnect}
        onNodeDragStop={handleNodeDragStop}
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
        onToggleBoundaries={() => setShowBoundaries((value) => !value)}
        onExportSvg={() => handleExport("svg")}
        onExportPng={() => handleExport("png")}
      />
      <NodeSidePanel
        component={selectedComponent ?? null}
        cost={selectedCost}
        onClose={() => setSelectedNode(null)}
        onApply={(component) => handleApplyComponent({
          ...component,
          description: component.description ?? "",
          config: component.config ?? {},
        })}
        onDelete={handleDeleteComponent}
      />
    </div>
  );
}

export default ArchitectureDiagram;
