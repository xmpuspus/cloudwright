import React, { useEffect, useMemo, useState } from "react";

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

const buttonStyle: React.CSSProperties = {
  border: "1px solid #cbd5e1",
  background: "#ffffff",
  color: "#0f172a",
  borderRadius: 6,
  padding: "7px 10px",
  cursor: "pointer",
  fontSize: 12,
  fontWeight: 600,
};

export default function CatalogDrawer({
  provider,
  standardsResult,
  onAddResource,
  onAddModule,
  onCheckStandards,
}: CatalogDrawerProps) {
  const providerKey = (provider || "aws").toLowerCase();
  const [open, setOpen] = useState(true);
  const [mode, setMode] = useState<"resources" | "modules" | "standards">("resources");
  const [query, setQuery] = useState("");
  const [services, setServices] = useState<ServiceSummary[]>([]);
  const [modules, setModules] = useState<ModuleSummary[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/catalog/services?provider=${encodeURIComponent(providerKey)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setServices(data?.services ?? []))
      .catch(() => setServices([]));
  }, [providerKey]);

  useEffect(() => {
    fetch(`${API_BASE}/modules`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setModules(data?.modules ?? []))
      .catch(() => setModules([]));
  }, []);

  const filteredServices = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return services;
    return services.filter((s) =>
      [s.name, s.service_key, s.category, s.description ?? ""].some((value) => value.toLowerCase().includes(q))
    );
  }, [services, query]);

  const filteredModules = useMemo(() => {
    const q = query.trim().toLowerCase();
    const providerModules = modules.filter((m) => m.provider.toLowerCase() === providerKey);
    if (!q) return providerModules;
    return providerModules.filter((m) =>
      [m.name, m.id, m.category, m.description ?? "", ...(m.tags ?? [])].some((value) =>
        value.toLowerCase().includes(q)
      )
    );
  }, [modules, providerKey, query]);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          ...buttonStyle,
          position: "absolute",
          left: 16,
          top: 16,
          zIndex: 15,
          boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
        }}
      >
        Add Resource
      </button>
    );
  }

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: 320,
        height: "100%",
        zIndex: 14,
        background: "#ffffff",
        borderRight: "1px solid #e2e8f0",
        boxShadow: "2px 0 8px rgba(0,0,0,0.06)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ padding: 14, borderBottom: "1px solid #e2e8f0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a" }}>Catalog</div>
          <button
            onClick={() => setOpen(false)}
            style={{ border: "none", background: "transparent", color: "#64748b", cursor: "pointer", fontSize: 18 }}
            aria-label="Close catalog"
          >
            x
          </button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 4, marginBottom: 10 }}>
          {(["resources", "modules", "standards"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setMode(tab)}
              style={{
                ...buttonStyle,
                padding: "6px 4px",
                borderColor: mode === tab ? "#2563eb" : "#cbd5e1",
                color: mode === tab ? "#2563eb" : "#475569",
                background: mode === tab ? "#eff6ff" : "#ffffff",
                textTransform: "capitalize",
              }}
            >
              {tab}
            </button>
          ))}
        </div>
        {mode !== "standards" && (
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search"
            style={{
              width: "100%",
              boxSizing: "border-box",
              border: "1px solid #cbd5e1",
              borderRadius: 6,
              padding: "8px 10px",
              color: "#0f172a",
              fontSize: 13,
              outline: "none",
            }}
          />
        )}
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 12 }}>
        {mode === "resources" &&
          filteredServices.map((service) => (
            <button
              key={`${service.provider}:${service.service_key}`}
              onClick={() => onAddResource(service)}
              style={{
                width: "100%",
                textAlign: "left",
                border: "1px solid #e2e8f0",
                background: "#ffffff",
                borderRadius: 8,
                padding: 10,
                marginBottom: 8,
                cursor: "pointer",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span style={{ color: "#0f172a", fontSize: 13, fontWeight: 700 }}>{service.name}</span>
                <span style={{ color: "#64748b", fontSize: 10, textTransform: "uppercase" }}>
                  {service.category.replace(/_/g, " ")}
                </span>
              </div>
              <div style={{ color: "#64748b", fontSize: 11, marginTop: 4 }}>{service.service_key}</div>
            </button>
          ))}
        {mode === "resources" && filteredServices.length === 0 && (
          <p style={{ color: "#64748b", fontSize: 13 }}>No resources found for {providerKey.toUpperCase()}.</p>
        )}

        {mode === "modules" &&
          filteredModules.map((module) => (
            <button
              key={module.id}
              onClick={() => onAddModule(module.id)}
              style={{
                width: "100%",
                textAlign: "left",
                border: "1px solid #bfdbfe",
                background: "#eff6ff",
                borderRadius: 8,
                padding: 10,
                marginBottom: 8,
                cursor: "pointer",
              }}
            >
              <div style={{ color: "#0f172a", fontSize: 13, fontWeight: 700 }}>{module.name}</div>
              <div style={{ color: "#475569", fontSize: 12, marginTop: 4, lineHeight: 1.35 }}>
                {module.description}
              </div>
              <div style={{ color: "#2563eb", fontSize: 11, marginTop: 6, textTransform: "uppercase" }}>
                {module.category}
              </div>
            </button>
          ))}
        {mode === "modules" && filteredModules.length === 0 && (
          <p style={{ color: "#64748b", fontSize: 13 }}>No approved modules found for {providerKey.toUpperCase()}.</p>
        )}

        {mode === "standards" && (
          <>
            <button onClick={onCheckStandards} style={{ ...buttonStyle, width: "100%", marginBottom: 12 }}>
              Check Standards
            </button>
            {!standardsResult && <p style={{ color: "#64748b", fontSize: 13 }}>No standards check has run.</p>}
            {standardsResult?.passed && (
              <div style={{ color: "#166534", background: "#dcfce7", borderRadius: 8, padding: 10, fontSize: 13 }}>
                Standards passed.
              </div>
            )}
            {standardsResult && !standardsResult.passed && (
              <div>
                {standardsResult.violations.map((violation, index) => (
                  <div
                    key={`${violation.code}:${index}`}
                    style={{
                      border: "1px solid #fecaca",
                      background: "#fef2f2",
                      borderRadius: 8,
                      padding: 10,
                      marginBottom: 8,
                    }}
                  >
                    <div style={{ color: "#991b1b", fontSize: 12, fontWeight: 700 }}>
                      {violation.code.replace(/_/g, " ")}
                    </div>
                    <div style={{ color: "#7f1d1d", fontSize: 12, marginTop: 4, lineHeight: 1.4 }}>
                      {violation.message}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
