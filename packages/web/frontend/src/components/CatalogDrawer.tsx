import React, { useEffect, useMemo, useState } from "react";
import Icon from "./Icon";

interface ServiceSummary {
  service_key: string;
  provider: string;
  category: string;
  name: string;
  description?: string;
  default_config?: Record<string, unknown>;
}

interface ModuleSummary {
  id: string;
  name: string;
  provider: string;
  category: string;
  description?: string;
  tags?: string[];
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

interface CatalogDrawerProps {
  provider: string;
  standardsResult: StandardsResult | null;
  onAddResource: (service: ServiceSummary) => void;
  onAddModule: (moduleId: string) => void;
  onCheckStandards: () => void;
}

const API_BASE = "/api";
const MODES = ["resources", "modules", "standards"] as const;
type Mode = (typeof MODES)[number];

export default function CatalogDrawer({
  provider,
  standardsResult,
  onAddResource,
  onAddModule,
  onCheckStandards,
}: CatalogDrawerProps) {
  const providerKey = (provider || "aws").toLowerCase();
  // Closed by default. The old default covered the diagram on every page load.
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<Mode>("resources");
  const [query, setQuery] = useState("");
  const [services, setServices] = useState<ServiceSummary[]>([]);
  const [modules, setModules] = useState<ModuleSummary[]>([]);

  useEffect(() => {
    if (!open) return;
    fetch(`${API_BASE}/catalog/services?provider=${encodeURIComponent(providerKey)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setServices(data?.services ?? []))
      .catch(() => setServices([]));
  }, [providerKey, open]);

  useEffect(() => {
    if (!open) return;
    fetch(`${API_BASE}/modules`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setModules(data?.modules ?? []))
      .catch(() => setModules([]));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const filteredServices = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return services;
    return services.filter((s) =>
      [s.name, s.service_key, s.category, s.description ?? ""].some((value) =>
        value.toLowerCase().includes(q),
      ),
    );
  }, [services, query]);

  const filteredModules = useMemo(() => {
    const q = query.trim().toLowerCase();
    const providerModules = modules.filter((m) => m.provider.toLowerCase() === providerKey);
    if (!q) return providerModules;
    return providerModules.filter((m) =>
      [m.name, m.id, m.category, m.description ?? "", ...(m.tags ?? [])].some((value) =>
        value.toLowerCase().includes(q),
      ),
    );
  }, [modules, providerKey, query]);

  if (!open) {
    return (
      <button
        className="btn"
        onClick={() => setOpen(true)}
        aria-expanded={false}
        style={{
          position: "absolute",
          left: "var(--space-4)",
          top: "var(--space-4)",
          zIndex: 15,
          boxShadow: "var(--shadow)",
        }}
      >
        <Icon name="plus" size={14} />
        Add Resource
      </button>
    );
  }

  return (
    <aside className="drawer drawer--left" aria-label="Service catalog">
      <div className="drawer__header">
        <div className="drawer__title">
          Catalog
          <button
            className="btn btn--ghost btn--icon"
            onClick={() => setOpen(false)}
            aria-label="Close catalog"
          >
            <Icon name="close" size={15} />
          </button>
        </div>
        <div
          role="tablist"
          aria-label="Catalog sections"
          style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 4, margin: "var(--space-3) 0 var(--space-2)" }}
        >
          {MODES.map((tab) => (
            <button
              key={tab}
              role="tab"
              aria-selected={mode === tab}
              tabIndex={mode === tab ? 0 : -1}
              className="btn btn--sm"
              onClick={() => setMode(tab)}
              style={
                mode === tab
                  ? { background: "var(--accent-soft)", borderColor: "var(--accent)", color: "var(--accent-text)", textTransform: "capitalize" }
                  : { textTransform: "capitalize" }
              }
            >
              {tab}
            </button>
          ))}
        </div>
        {mode !== "standards" && (
          <input
            className="field"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search the catalog"
            aria-label="Search the catalog"
            type="search"
          />
        )}
      </div>

      <div className="drawer__body">
        {mode === "resources" &&
          filteredServices.map((service) => (
            <button
              key={`${service.provider}:${service.service_key}`}
              className="list-btn"
              onClick={() => onAddResource(service)}
            >
              <span style={{ display: "flex", justifyContent: "space-between", gap: "var(--space-2)" }}>
                <span style={{ fontSize: "var(--text-base)", fontWeight: 650 }}>{service.name}</span>
                <span className="section-label" style={{ fontSize: "var(--text-2xs)" }}>
                  {service.category.replace(/_/g, " ")}
                </span>
              </span>
              <span style={{ display: "block", color: "var(--text-subtle)", fontSize: "var(--text-xs)", marginTop: 3 }}>
                {service.service_key}
              </span>
            </button>
          ))}
        {mode === "resources" && filteredServices.length === 0 && (
          <p style={{ color: "var(--text-subtle)", fontSize: "var(--text-base)" }}>
            No resources match that search for {providerKey.toUpperCase()}.
          </p>
        )}

        {mode === "modules" &&
          filteredModules.map((module) => (
            <button
              key={module.id}
              className="list-btn"
              onClick={() => onAddModule(module.id)}
              style={{ borderColor: "var(--accent)", background: "var(--accent-soft)" }}
            >
              <span style={{ display: "block", fontSize: "var(--text-base)", fontWeight: 650 }}>{module.name}</span>
              <span style={{ display: "block", color: "var(--text-muted)", fontSize: "var(--text-sm)", marginTop: 3, lineHeight: 1.4 }}>
                {module.description}
              </span>
              <span className="section-label" style={{ display: "block", marginTop: 6, color: "var(--accent-text)" }}>
                {module.category}
              </span>
            </button>
          ))}
        {mode === "modules" && filteredModules.length === 0 && (
          <p style={{ color: "var(--text-subtle)", fontSize: "var(--text-base)" }}>
            No approved modules match that search for {providerKey.toUpperCase()}.
          </p>
        )}

        {mode === "standards" && (
          <>
            <button className="btn btn--block" onClick={onCheckStandards} style={{ marginBottom: "var(--space-3)" }}>
              Check Standards
            </button>
            {!standardsResult && (
              <p style={{ color: "var(--text-subtle)", fontSize: "var(--text-base)" }}>
                No standards check has run.
              </p>
            )}
            {standardsResult?.passed && (
              <div className="callout callout--success">Standards passed.</div>
            )}
            {standardsResult && !standardsResult.passed &&
              standardsResult.violations.map((violation, index) => (
                <div
                  key={`${violation.code}:${index}`}
                  className="callout callout--danger"
                  style={{ marginBottom: "var(--space-2)" }}
                >
                  <strong style={{ display: "block", fontSize: "var(--text-sm)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                    {violation.code.replace(/_/g, " ")}
                  </strong>
                  <span style={{ display: "block", marginTop: 4, lineHeight: 1.45 }}>{violation.message}</span>
                </div>
              ))}
          </>
        )}
      </div>
    </aside>
  );
}
