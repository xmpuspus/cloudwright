import React, { useEffect, useMemo, useState } from "react";
import { getCategoryColor, getServiceCategory, getCategoryIconPath } from "../lib/icons";

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

const divider = { borderTop: "1px solid #e2e8f0", margin: "12px 0" };

const sectionLabel: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginBottom: 8,
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  fontWeight: 600,
  color: "#64748b",
  marginBottom: 5,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  border: "1px solid #cbd5e1",
  borderRadius: 6,
  padding: "8px 10px",
  color: "#0f172a",
  fontSize: 13,
  outline: "none",
  background: "#ffffff",
};

const readOnlyRow: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 10,
  color: "#475569",
  fontSize: 13,
  marginBottom: 7,
};

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
  const visible = component !== null;
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

  const category = component ? getServiceCategory(component.service) : "compute";
  const color = getCategoryColor(category);
  const iconPath = getCategoryIconPath(category);
  const monthly = cost?.monthly ?? null;

  const parsedTier = useMemo(() => {
    const value = Number(tier);
    return Number.isFinite(value) ? value : 2;
  }, [tier]);

  const handleApply = () => {
    if (!component) return;
    const nextConfig = parseKeyValue(configText);
    const tags = parseKeyValue(tagsText);
    if (Object.keys(tags).length > 0) {
      nextConfig.tags = tags;
    }
    onApply({
      ...component,
      label: label.trim() || component.label,
      description,
      tier: parsedTier,
      config: nextConfig,
    });
  };

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        right: 0,
        width: 340,
        height: "100%",
        background: "#ffffff",
        borderLeft: "1px solid #e2e8f0",
        transform: visible ? "translateX(0)" : "translateX(100%)",
        transition: "transform 0.2s ease",
        zIndex: 20,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        boxShadow: "-2px 0 8px rgba(0,0,0,0.06)",
      }}
    >
      <div style={{ padding: "16px 16px 12px", borderBottom: "1px solid #e2e8f0" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: `${color}22`,
              border: `1.5px solid ${color}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <svg
              width={20}
              height={20}
              viewBox="0 0 24 24"
              fill="none"
              stroke={color}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ display: "block" }}
            >
              <path d={iconPath} />
            </svg>
          </div>
          <span
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: "#0f172a",
              flex: 1,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {component?.label ?? "Resource"}
          </span>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: "#94a3b8",
              cursor: "pointer",
              fontSize: 18,
              lineHeight: 1,
              padding: "2px 4px",
              flexShrink: 0,
            }}
            aria-label="Close panel"
          >
            x
          </button>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              background: "#f1f5f9",
              color: "#475569",
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 8px",
              textTransform: "uppercase",
            }}
          >
            {component?.provider}
          </span>
          <span style={{ color: "#64748b", fontSize: 12 }}>{component?.service}</span>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "12px 16px" }}>
        <div style={sectionLabel}>Overview</div>
        <label style={labelStyle} htmlFor="resource-label">Label</label>
        <input
          id="resource-label"
          aria-label="Label"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          style={{ ...inputStyle, marginBottom: 10 }}
        />

        <label style={labelStyle} htmlFor="resource-description">Description</label>
        <textarea
          id="resource-description"
          aria-label="Description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
          style={{ ...inputStyle, marginBottom: 10, resize: "vertical", minHeight: 72 }}
        />

        <label style={labelStyle} htmlFor="resource-tier">Tier</label>
        <input
          id="resource-tier"
          aria-label="Tier"
          type="number"
          value={tier}
          onChange={(event) => setTier(event.target.value)}
          style={{ ...inputStyle, marginBottom: 10 }}
        />

        <div style={readOnlyRow}>
          <span>Service</span>
          <strong style={{ color: "#0f172a" }}>{component?.service}</strong>
        </div>
        <div style={readOnlyRow}>
          <span>Provider</span>
          <strong style={{ color: "#0f172a" }}>{component?.provider?.toUpperCase()}</strong>
        </div>

        <div style={divider} />

        <div style={sectionLabel}>Cost</div>
        {monthly !== null ? (
          <div style={readOnlyRow}>
            <span>Monthly</span>
            <strong style={{ color: "#2563eb" }}>
              ${monthly.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </strong>
          </div>
        ) : (
          <p style={{ color: "#94a3b8", fontSize: 13 }}>No cost data</p>
        )}

        <div style={divider} />

        <div style={sectionLabel}>Configuration</div>
        <textarea
          aria-label="Configuration"
          value={configText}
          onChange={(event) => setConfigText(event.target.value)}
          rows={7}
          style={{ ...inputStyle, resize: "vertical", minHeight: 140, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
        />

        <div style={{ ...sectionLabel, marginTop: 16 }}>Tags</div>
        <textarea
          aria-label="Tags"
          value={tagsText}
          onChange={(event) => setTagsText(event.target.value)}
          rows={5}
          style={{ ...inputStyle, resize: "vertical", minHeight: 110, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
        />
      </div>

      <div style={{ padding: 12, borderTop: "1px solid #e2e8f0", display: "flex", gap: 8 }}>
        <button
          onClick={handleApply}
          disabled={!component}
          style={{
            flex: 1,
            border: "none",
            borderRadius: 6,
            padding: "10px 12px",
            background: "#2563eb",
            color: "#ffffff",
            cursor: component ? "pointer" : "not-allowed",
            fontSize: 14,
            fontWeight: 700,
          }}
        >
          Apply
        </button>
        <button
          onClick={() => component && onDelete(component.id)}
          disabled={!component}
          style={{
            border: "1px solid #fecaca",
            borderRadius: 6,
            padding: "10px 12px",
            background: "#fef2f2",
            color: "#b91c1c",
            cursor: component ? "pointer" : "not-allowed",
            fontSize: 14,
            fontWeight: 700,
          }}
        >
          Delete
        </button>
      </div>
    </div>
  );
}
