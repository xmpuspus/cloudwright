import React, { useMemo, useState, useCallback, useEffect } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  useNodesState,
  useEdgesState,
  useReactFlow,
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
import ConfirmDialog from "./ConfirmDialog";
import { parseApiError } from "../lib/apiError";
import { useToast } from "../lib/toast";

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

/** Must match the fixed `.node` width in styles.css. */
const NODE_WIDTH = 260;
const NODE_HEIGHT = 104;
/** Leaves 120px of clear canvas between two cards, which is where a connection
 *  between neighbours in a row puts its label. */
const H_GAP = 380;
const V_GAP = 260;
const BOUNDARY_PADDING = 32;
const BOUNDARY_LABEL_SPACE = 24;
/** Clearance between a tier box and the VPC box that wraps it. Without it both
 *  rectangles come out of the same component positions and share a border. */
const VPC_GAP = 26;
const VPC_LABEL_EXTRA = 30;
const MAX_PER_ROW = 4;
const LAYOUT_WIDTH = 1400;
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

/** Every colour comes from a theme token, so the dark canvas gets a dark tint
 *  instead of the pale slab a hardcoded light rgba used to paint. */
function boundaryStyle(token: string): BoundaryStyle {
  return {
    border: `var(--${token})`,
    bg: `color-mix(in srgb, var(--${token}) var(--boundary-fill), transparent)`,
    labelColor: `var(--${token}-text)`,
    labelBg: `color-mix(in srgb, var(--${token}) var(--boundary-label-fill), var(--canvas))`,
    dot: `var(--${token})`,
  };
}

function tierStyle(tier: number): BoundaryStyle {
  return boundaryStyle(`tier-${Math.min(Math.max(tier, 0), 4)}`);
}

const VPC_COLORS: BoundaryStyle = boundaryStyle("tier-vpc");

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

function getBoundaryColors(boundaryId: string, kind: string): BoundaryStyle {
  if (kind === "vpc") return VPC_COLORS;
  const tierMatch = boundaryId.match(/^tier-(\d+)$/);
  if (tierMatch) return tierStyle(parseInt(tierMatch[1]));
  return tierStyle(2);
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
      label: "VPC",
      component_ids: innerIds,
    });
  }

  return boundaries;
}

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Order the components inside each tier so connected ones sit near each other.
 *  A barycentre sweep: every node moves to the average slot of its neighbours in
 *  the tier above, then below, then above again. Ties keep the spec's own order,
 *  so the same spec always draws the same picture. */
function orderTiers(
  tierGroups: Record<number, Component[]>,
  sortedTiers: number[],
  connections: Connection[],
): Record<number, Component[]> {
  const neighbours = new Map<string, string[]>();
  const link = (from: string, to: string) => {
    const list = neighbours.get(from);
    if (list) list.push(to);
    else neighbours.set(from, [to]);
  };
  for (const conn of connections) {
    link(conn.source, conn.target);
    link(conn.target, conn.source);
  }

  const ordered: Record<number, Component[]> = {};
  for (const tier of sortedTiers) ordered[tier] = [...tierGroups[tier]];

  const sweep = (tiers: number[]) => {
    for (let i = 1; i < tiers.length; i++) {
      const anchor = new Map(ordered[tiers[i - 1]].map((comp, index) => [comp.id, index]));
      const scored = ordered[tiers[i]].map((component, index) => {
        const slots = (neighbours.get(component.id) ?? [])
          .map((id) => anchor.get(id))
          .filter((slot): slot is number => slot !== undefined);
        const barycentre = slots.length
          ? slots.reduce((sum, slot) => sum + slot, 0) / slots.length
          : index;
        return { component, barycentre, index };
      });
      scored.sort((a, b) => a.barycentre - b.barycentre || a.index - b.index);
      ordered[tiers[i]] = scored.map((entry) => entry.component);
    }
  };

  sweep(sortedTiers);
  sweep([...sortedTiers].reverse());
  sweep(sortedTiers);
  return ordered;
}

interface Slot {
  tier: number;
  index: number;
  size: number;
}

interface LayoutOrder {
  sortedTiers: number[];
  ordered: Record<number, Component[]>;
  slots: Map<string, Slot>;
}

/** Group the components by tier, order each tier, and record where every
 *  component landed. `buildNodes` reads it for positions and `buildEdges` reads
 *  it to choose which side of a node a connection leaves from. */
function layoutOrder(spec: ArchSpec): LayoutOrder {
  const tierGroups: Record<number, Component[]> = {};
  for (const comp of spec.components) {
    const tier = comp.tier ?? 2;
    if (!tierGroups[tier]) tierGroups[tier] = [];
    tierGroups[tier].push(comp);
  }
  const sortedTiers = Object.keys(tierGroups).map(Number).sort((a, b) => a - b);
  const ordered = orderTiers(tierGroups, sortedTiers, spec.connections);
  const slots = new Map<string, Slot>();
  for (const tier of sortedTiers) {
    const size = ordered[tier].length;
    ordered[tier].forEach((comp, index) => slots.set(comp.id, { tier, index, size }));
  }
  return { sortedTiers, ordered, slots };
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

  const { sortedTiers, ordered } = layoutOrder(spec);

  const compPositions: Record<string, { x: number; y: number }> = {};
  let yOffset = 40;
  for (const tier of sortedTiers) {
    const comps = ordered[tier];
    const baseY = yOffset;
    for (let i = 0; i < comps.length; i++) {
      const row = Math.floor(i / MAX_PER_ROW);
      const col = i % MAX_PER_ROW;
      const rowCount = Math.min(MAX_PER_ROW, comps.length - row * MAX_PER_ROW);
      // Centre the nodes themselves, not the column slots they sit in. The old
      // form used rowCount * H_GAP, which left every row 50px off centre.
      const rowWidth = rowCount * NODE_WIDTH + (rowCount - 1) * (H_GAP - NODE_WIDTH);
      const startX = (LAYOUT_WIDTH - rowWidth) / 2;
      const generated = { x: startX + col * H_GAP, y: baseY + row * (NODE_HEIGHT + 60) };
      const saved = savedPositions[comps[i].id];
      compPositions[comps[i].id] =
        saved && Number.isFinite(saved.x) && Number.isFinite(saved.y) ? saved : generated;
    }
    const rows = Math.ceil(comps.length / MAX_PER_ROW);
    yOffset += V_GAP + (rows - 1) * (NODE_HEIGHT + 60);
  }

  if (showBoundaries && boundaries.length > 0) {
    const boundaryRects: Record<string, Rect> = {};
    const vpcBoundary = boundaries.find((b) => b.kind === "vpc");

    for (const b of boundaries) {
      if (b.kind === "vpc") continue;
      const members = b.component_ids.filter((cid) => compPositions[cid]);
      if (members.length === 0) continue;
      const xs = members.map((cid) => compPositions[cid].x);
      const ys = members.map((cid) => compPositions[cid].y);
      const x = Math.min(...xs) - BOUNDARY_PADDING;
      const y = Math.min(...ys) - BOUNDARY_PADDING - BOUNDARY_LABEL_SPACE;
      boundaryRects[b.id] = {
        x,
        y,
        w: Math.max(...xs) + NODE_WIDTH + BOUNDARY_PADDING - x,
        h: Math.max(...ys) + NODE_HEIGHT + BOUNDARY_PADDING - y,
      };
    }

    if (vpcBoundary && vpcBoundary.component_ids.length > 0) {
      // Wrap the tier boxes, not the raw components. Measuring both from the
      // same component rects gave the VPC and a tier the same border line.
      const inner: Rect[] = [];
      const covered = new Set<string>();
      for (const b of boundaries) {
        if (b.kind === "vpc" || !boundaryRects[b.id]) continue;
        if (!b.component_ids.some((cid) => vpcBoundary.component_ids.includes(cid))) continue;
        inner.push(boundaryRects[b.id]);
        for (const cid of b.component_ids) covered.add(cid);
      }
      for (const cid of vpcBoundary.component_ids) {
        if (covered.has(cid) || !compPositions[cid]) continue;
        inner.push({
          x: compPositions[cid].x - BOUNDARY_PADDING,
          y: compPositions[cid].y - BOUNDARY_PADDING,
          w: NODE_WIDTH + BOUNDARY_PADDING * 2,
          h: NODE_HEIGHT + BOUNDARY_PADDING * 2,
        });
      }
      if (inner.length > 0) {
        const x = Math.min(...inner.map((r) => r.x)) - VPC_GAP;
        const y = Math.min(...inner.map((r) => r.y)) - VPC_GAP - VPC_LABEL_EXTRA;
        boundaryRects[vpcBoundary.id] = {
          x,
          y,
          w: Math.max(...inner.map((r) => r.x + r.w)) + VPC_GAP - x,
          h: Math.max(...inner.map((r) => r.y + r.h)) + VPC_GAP - y,
        };
      }
    }

    // A boundary is decoration drawn behind the nodes. It takes no drag and no
    // selection, so a drag inside a VPC pans the canvas.
    const pushBoundary = (b: Boundary, zIndex: number) => {
      const rect = boundaryRects[b.id];
      if (!rect) return;
      const colors = getBoundaryColors(b.id, b.kind);
      const isVpc = b.kind === "vpc";
      nodes.push({
        id: `boundary-${b.id}`,
        type: "boundaryGroup",
        position: { x: rect.x, y: rect.y },
        data: {
          label: b.label || b.id,
          labelColor: colors.labelColor,
          labelBg: colors.labelBg,
          dotColor: colors.dot,
        },
        style: {
          background: colors.bg,
          border: isVpc ? `2px dashed ${colors.border}` : `1.5px solid ${colors.border}`,
          borderRadius: isVpc ? 16 : 10,
          width: rect.w,
          height: rect.h,
        },
        zIndex,
        draggable: false,
        selectable: false,
      });
    };

    if (vpcBoundary) pushBoundary(vpcBoundary, -2);
    for (const b of boundaries) {
      if (b.kind === "vpc") continue;
      pushBoundary(b, -1);
    }
  }

  for (const tier of sortedTiers) {
    for (const comp of ordered[tier]) {
      nodes.push({
        id: comp.id,
        type: "cloudService",
        position: {
          x: compPositions[comp.id]?.x ?? 0,
          y: compPositions[comp.id]?.y ?? 0,
        },
        data: {
          label: comp.label,
          service: comp.service,
          provider: comp.provider,
          description: comp.description,
          tier: comp.tier,
          config: comp.config || {},
          monthlyCost: costMap[comp.id],
        },
      });
    }
  }

  return nodes;
}

function connectionEdgeId(conn: Connection, index: number): string {
  return `edge:${conn.source}:${conn.target}:${index}`;
}

function buildEdges(spec: ArchSpec): Edge[] {
  const { slots } = layoutOrder(spec);
  return spec.connections.map((conn, i) => {
    let edgeLabel = conn.label || "";
    if (conn.protocol && !edgeLabel.includes(conn.protocol)) {
      edgeLabel = conn.protocol + (conn.port ? `:${conn.port}` : "");
    }

    // Down the stack leaves the bottom and up the stack leaves the top. The old
    // single pair of handles sent a same-tier connection out of the bottom and
    // back into the top of the node beside it, which is where most of the
    // crossings came from.
    //
    // Inside one tier there are two cases. Neighbours in the row link straight
    // across the gap between them. Anything further apart dips under the row,
    // because a straight line would cross every card in between and drop its
    // label on one of them.
    const source = slots.get(conn.source);
    const target = slots.get(conn.target);
    const from = source?.tier ?? 2;
    const to = target?.tier ?? 2;
    let sourceHandle = "s-bottom";
    let targetHandle = "t-top";
    if (to === from) {
      const gap = source && target ? target.index - source.index : 0;
      if (gap === 1) {
        sourceHandle = "s-right";
        targetHandle = "t-left";
      } else if (gap === -1) {
        sourceHandle = "s-left";
        targetHandle = "t-right";
      } else {
        sourceHandle = "s-bottom";
        targetHandle = "t-bottom";
      }
    } else if (Math.abs(to - from) >= 2) {
      // A connection that skips a tier runs down the outside. Straight down the
      // middle would pass behind whichever card sits in the tier between, and
      // drop its label on that card's name.
      const side = source && source.index * 2 < source.size - 1 ? "left" : "right";
      sourceHandle = `s-${side}`;
      targetHandle = `t-${side}`;
    } else if (to < from) {
      sourceHandle = "s-top";
      targetHandle = "t-bottom";
    }

    return {
      id: connectionEdgeId(conn, i),
      source: conn.source,
      target: conn.target,
      sourceHandle,
      targetHandle,
      type: "smoothstep",
      label: edgeLabel,
      style: { stroke: "var(--edge)", strokeWidth: 1.6 },
      // A directed diagram needs the direction drawn on it.
      markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: "var(--edge)" },
      labelStyle: { fill: "var(--edge-label)", fontSize: 11, fontWeight: 600 },
      // Opaque chip, so a label crossing a boundary border still reads.
      labelShowBg: true,
      labelBgStyle: { fill: "var(--surface)", stroke: "var(--border)" },
      labelBgPadding: [6, 3] as [number, number],
      labelBgBorderRadius: 4,
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

/** A phone-width canvas needs to zoom well past ReactFlow's 0.5 floor. At 0.5 a
 *  microservices architecture left 2 of its 8 nodes outside the pane. */
const MIN_ZOOM = 0.12;
const MAX_ZOOM = 2.5;
const FIT_VIEW_OPTIONS = { padding: 0.16, minZoom: MIN_ZOOM };
/** ReactFlow listens for Backspace alone by default, so the Delete key did
 *  nothing to a selected connection. */
const DELETE_KEYS = ["Backspace", "Delete"];

/** ReactFlow's `fitView` prop only fires when nodes exist at mount, and this
 *  diagram builds its nodes in an effect. Refit whenever the node set changes,
 *  but not when a drag only moves one, so a hand-placed layout survives. */
function FitOnChange({ signature }: { signature: string }) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    const id = window.setTimeout(() => {
      void fitView({ ...FIT_VIEW_OPTIONS, duration: 250 });
    }, 60);
    return () => window.clearTimeout(id);
  }, [signature, fitView]);
  return null;
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
  const [pendingDelete, setPendingDelete] = useState<
    { kind: "component"; id: string; label: string } | { kind: "edges"; ids: string[] } | null
  >(null);
  const { notify } = useToast();

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
      if (!res.ok) {
        notify(await parseApiError(res));
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `architecture.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      notify(`The ${format.toUpperCase()} export failed. Check that the server is still running.`);
    }
  }, [notify, spec]);

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

  // Changes only when the graph gains or loses a node, never on a drag.
  const layoutSignature = useMemo(
    () => `${showBoundaries}:${spec.components.map((c) => c.id).sort().join(",")}`,
    [showBoundaries, spec.components],
  );

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

  // Every node now carries an absolute position, so there is no parent origin to
  // add back on. Boundaries are not draggable; the guard stays as a backstop.
  const handleNodeDragStop = useCallback((_event: React.MouseEvent, node: Node) => {
    if (node.id.startsWith("boundary-")) return;
    const metadata = cloneMetadata(spec.metadata);
    const canvas = metadata.canvas ?? {};
    const canvasNodes = { ...(canvas.nodes ?? {}) };
    canvasNodes[node.id] = { x: node.position.x, y: node.position.y };
    metadata.canvas = { ...canvas, nodes: canvasNodes };
    applySpec({ ...spec, metadata });
  }, [applySpec, spec]);

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
    // React Flow already removed them from its own state. Put them back until the
    // user confirms, so a stray Delete key press cannot silently drop a connection.
    setEdges(buildEdges(spec));
    setPendingDelete({ kind: "edges", ids: deleted.map((edge) => edge.id) });
  }, [setEdges, spec]);

  const confirmDelete = useCallback(() => {
    if (!pendingDelete) return;
    if (pendingDelete.kind === "edges") {
      const deletedIds = new Set(pendingDelete.ids);
      applySpec({
        ...spec,
        connections: spec.connections.filter(
          (conn, index) => !deletedIds.has(connectionEdgeId(conn, index)),
        ),
      });
      setPendingDelete(null);
      return;
    }

    const componentId = pendingDelete.id;
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
    setPendingDelete(null);
  }, [applySpec, pendingDelete, spec]);

  const handleApplyComponent = useCallback((updated: Component) => {
    applySpec({
      ...spec,
      components: spec.components.map((component) => (component.id === updated.id ? updated : component)),
    });
  }, [applySpec, spec]);

  const handleDeleteComponent = useCallback((componentId: string) => {
    const component = spec.components.find((candidate) => candidate.id === componentId);
    if (!component) return;
    setPendingDelete({
      kind: "component",
      id: componentId,
      label: component.label || component.id,
    });
  }, [spec.components]);

  // A new resource gets no saved position, so the tier layout places it in the
  // row its category belongs to. The old fixed grid dropped it at (360, 80),
  // which landed on top of whatever the generated layout had put there.
  const handleAddResource = useCallback((service: ServiceSummary) => {
    const used = new Set(spec.components.map((component) => component.id));
    const id = uniqueId(safeId(service.service_key), used);
    const metadata = cloneMetadata(spec.metadata);

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
      if (!response.ok) {
        notify(await parseApiError(response));
        return;
      }
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

      // No saved positions here either: the tier layout places every component
      // the module brings with it.
      const addedComponents = module.fragment.components.map((component) => {
        const nextConfig = cloneJson(component.config ?? {});
        const tags = {
          ...(module.default_tags ?? {}),
          ...((typeof nextConfig.tags === "object" && nextConfig.tags !== null ? nextConfig.tags : {}) as Record<string, string>),
        };
        nextConfig.tags = tags;
        return {
          ...component,
          id: remap[component.id],
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
      metadata.modules = { ...modules, instances };

      applySpec({
        ...spec,
        components: [...spec.components, ...addedComponents],
        connections: [...spec.connections, ...addedConnections],
        metadata,
      });
      setSelectedNode(addedComponents[0]?.id ?? null);
    } catch {
      notify("That module could not be added. Check that the server is still running.");
    }
  }, [applySpec, notify, spec]);

  const handleCheckStandards = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/canvas/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spec }),
      });
      if (!response.ok) {
        notify(await parseApiError(response));
        return;
      }
      setStandardsResult((await response.json()) as StandardsResult);
    } catch {
      setStandardsResult({
        passed: false,
        violations: [{ code: "request_failed", severity: "error", message: "Standards check failed." }],
      });
    }
  }, [notify, spec]);

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
        fitViewOptions={FIT_VIEW_OPTIONS}
        minZoom={MIN_ZOOM}
        maxZoom={MAX_ZOOM}
        nodeDragThreshold={2}
        connectionRadius={28}
        deleteKeyCode={DELETE_KEYS}
        proOptions={{ hideAttribution: true }}
        style={{ background: "var(--canvas)" }}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
      >
        <Background color="var(--canvas-dot)" gap={20} />
        <Controls />
        <FitOnChange signature={layoutSignature} />
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
      <ConfirmDialog
        open={pendingDelete !== null}
        title={pendingDelete?.kind === "component" ? "Delete this component?" : "Delete this connection?"}
        body={
          pendingDelete?.kind === "component"
            ? `${pendingDelete.label} and every connection into or out of it are removed from the spec.`
            : pendingDelete?.kind === "edges"
              ? `${pendingDelete.ids.length} connection${pendingDelete.ids.length === 1 ? "" : "s"} removed from the spec.`
              : ""
        }
        confirmLabel="Delete"
        destructive
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}

export default ArchitectureDiagram;
