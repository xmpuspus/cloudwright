import React, { useEffect, useMemo, useState } from "react";
import { getCategoryColor, getServiceCategory, getCategoryIconPath } from "../lib/icons";
import Icon from "./Icon";

interface ComponentData {
  id: string;
  label: string;
  service: string;
  provider: string;
  description?: string;
  tier: number;
  config?: Record<string, unknown>;
}

interface CostBreakdownItem {
  component_id: string;
  service: string;
  monthly: number;
  notes?: string;
}

interface NodeSidePanelProps {
  component: ComponentData | null;
  cost?: CostBreakdownItem | null;
  onClose: () => void;
  onApply: (component: ComponentData) => void;
  onDelete: (componentId: string) => void;
}

function formatValue(value: unknown): string {
  if (typeof value === "boolean") return value ? "true" : "false";
  if (value === null || value === undefined) return "";
  return String(value);
}

function stringifyKeyValue(config: Record<string, unknown> | undefined, omitTags: boolean): string {
  return Object.entries(config ?? {})
    .filter(([key, value]) => value !== null && value !== undefined && (!omitTags || key !== "tags"))
    .map(([key, value]) => `${key}=${formatValue(value)}`)
    .join("\n");
}

function stringifyTags(config: Record<string, unknown> | undefined): string {
  const tags = config?.tags;
  if (!tags || typeof tags !== "object" || Array.isArray(tags)) return "";
  return Object.entries(tags as Record<string, unknown>)
    .map(([key, value]) => `${key}=${formatValue(value)}`)
    .join("\n");
}

function parseScalar(value: string): unknown {
  const trimmed = value.trim();
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (trimmed !== "" && !Number.isNaN(Number(trimmed))) return Number(trimmed);
  return value;
}

function parseKeyValue(text: string): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const equalsIndex = trimmed.indexOf("=");
    if (equalsIndex === -1) {
      result[trimmed] = true;
      continue;
    }
    const key = trimmed.slice(0, equalsIndex).trim();
    if (!key) continue;
    result[key] = parseScalar(trimmed.slice(equalsIndex + 1));
  }
  return result;
}

export default function NodeSidePanel({
  component,
  cost,
  onClose,
  onApply,
  onDelete,
}: NodeSidePanelProps) {
  const [label, setLabel] = useState("");
  const [description, setDescription] = useState("");
  const [tier, setTier] = useState("2");
  const [configText, setConfigText] = useState("");
  const [tagsText, setTagsText] = useState("");

  useEffect(() => {
    if (!component) return;
    setLabel(component.label);
    setDescription(component.description ?? "");
    setTier(String(component.tier ?? 2));
    setConfigText(stringifyKeyValue(component.config, true));
    setTagsText(stringifyTags(component.config));
  }, [component]);

  useEffect(() => {
    if (!component) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [component, onClose]);

  const parsedTier = useMemo(() => {
    const value = Number(tier);
    return Number.isFinite(value) ? value : 2;
  }, [tier]);

  // Unmount when closed. The old version kept the inputs in the tab order off-screen.
  if (!component) return null;

  const category = getServiceCategory(component.service);
  const color = getCategoryColor(category);
  const monthly = cost?.monthly ?? null;

  const handleApply = () => {
    const nextConfig = parseKeyValue(configText);
    const tags = parseKeyValue(tagsText);
    if (Object.keys(tags).length > 0) nextConfig.tags = tags;
    onApply({
      ...component,
      label: label.trim() || component.label,
      description,
      tier: parsedTier,
      config: nextConfig,
    });
  };

  return (
    <aside
      className="drawer drawer--right"
      aria-label={`Edit ${component.label}`}
      style={{ animation: "cw-rise var(--duration) var(--ease)" }}
    >
      <div className="drawer__header">
        <div className="drawer__title">
          <span style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", minWidth: 0 }}>
            <span
              style={{
                width: 32,
                height: 32,
                borderRadius: "var(--radius)",
                background: `${color}22`,
                border: `1.5px solid ${color}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <svg
                width={18}
                height={18}
                viewBox="0 0 24 24"
                fill="none"
                stroke={color}
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d={getCategoryIconPath(category)} />
              </svg>
            </span>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {component.label}
            </span>
          </span>
          <button className="btn btn--ghost btn--icon" onClick={onClose} aria-label="Close panel">
            <Icon name="close" size={15} />
          </button>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
          <span className="badge badge--neutral">{component.provider}</span>
          <code className="inline">{component.service}</code>
          {monthly !== null && (
            <span style={{ marginLeft: "auto", color: "var(--accent-text)", fontWeight: 650, fontSize: "var(--text-base)" }}>
              ${monthly.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/mo
            </span>
          )}
        </div>
      </div>

      <div className="drawer__body">
        <p className="section-label" style={{ marginBottom: "var(--space-2)" }}>Overview</p>

        <label className="field-label" htmlFor="resource-label">Label</label>
        <input
          id="resource-label"
          className="field"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          style={{ marginBottom: "var(--space-3)" }}
        />

        <label className="field-label" htmlFor="resource-description">Description</label>
        <textarea
          id="resource-description"
          className="field"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
          style={{ marginBottom: "var(--space-3)", resize: "vertical" }}
        />

        <label className="field-label" htmlFor="resource-tier">Tier</label>
        <input
          id="resource-tier"
          className="field"
          type="number"
          value={tier}
          onChange={(event) => setTier(event.target.value)}
          style={{ marginBottom: "var(--space-4)" }}
        />

        <label className="field-label" htmlFor="resource-config">
          Configuration, one <code className="inline">key=value</code> per line
        </label>
        <textarea
          id="resource-config"
          className="field field--mono"
          value={configText}
          onChange={(event) => setConfigText(event.target.value)}
          rows={7}
          style={{ marginBottom: "var(--space-4)", minHeight: 130 }}
        />

        <label className="field-label" htmlFor="resource-tags">Tags</label>
        <textarea
          id="resource-tags"
          className="field field--mono"
          value={tagsText}
          onChange={(event) => setTagsText(event.target.value)}
          rows={4}
          style={{ minHeight: 96 }}
        />
      </div>

      <div className="drawer__footer">
        <button className="btn btn--primary" style={{ flex: 1 }} onClick={handleApply}>
          Apply
        </button>
        <button className="btn btn--danger" onClick={() => onDelete(component.id)}>
          Delete
        </button>
      </div>
    </aside>
  );
}
