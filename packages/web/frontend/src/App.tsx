import React, { useState, useRef, useEffect } from "react";
import ArchitectureDiagram from "./components/ArchitectureDiagram";
import CostTable from "./components/CostTable";
import SummaryBar from "./components/SummaryBar";
import ValidationPanel from "./components/ValidationPanel";
import ExportPanel from "./components/ExportPanel";
import SpecPanel from "./components/SpecPanel";

interface ArchSpec {
  name: string;
  provider: string;
  region: string;
  components: Component[];
  connections: Connection[];
  cost_estimate?: CostEstimate;
}

interface Component {
  id: string;
  service: string;
  provider: string;
  label: string;
  description: string;
  tier: number;
  config: Record<string, unknown>;
}

interface Connection {
  source: string;
  target: string;
  label: string;
  protocol?: string;
  port?: number;
}

interface CostEstimate {
  monthly_total: number;
  breakdown: { component_id: string; service: string; monthly: number; notes: string }[];
  currency: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  spec?: ArchSpec;
  yaml?: string;
}

const API_BASE = "/api";

function renderMarkdown(text: string): React.ReactNode[] {
  return text.split(/(\*\*.*?\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : <span key={i}>{part}</span>
  );
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentSpec, setCurrentSpec] = useState<ArchSpec | null>(null);
  const [activeTab, setActiveTab] = useState<
    "diagram" | "cost" | "validate" | "export" | "spec" | "modify"
  >("diagram");

  const [modifyInput, setModifyInput] = useState("");
  const [validationSummary, setValidationSummary] = useState<{ passed: number; total: number } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/design`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: input }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");
      let spec = data.spec as ArchSpec;

      // Auto-populate cost after design
      if (!spec.cost_estimate) {
        try {
          const costRes = await fetch(`${API_BASE}/cost`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ spec }),
          });
          if (costRes.ok) {
            const costData = await costRes.json();
            spec = { ...spec, cost_estimate: costData.estimate };
          }
        } catch {
          // cost is best-effort
        }
      }

      // Auto-validate (Well-Architected, best-effort)
      try {
        const valRes = await fetch(`${API_BASE}/validate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ spec, compliance: [], well_architected: true }),
        });
        if (valRes.ok) {
          const valData = await valRes.json();
          const results = valData.results || [];
          if (results.length > 0) {
            const checks = results[0].checks || [];
            const passed = checks.filter((c: { passed: boolean }) => c.passed).length;
            setValidationSummary({ passed, total: checks.length });
          }
        }
      } catch {
        // validation is best-effort
      }

      setCurrentSpec(spec);
      const assistantMsg: Message = {
        role: "assistant",
        content: `Designed **${spec.name}** with ${spec.components.length} components on ${spec.provider.toUpperCase()}.${spec.cost_estimate ? ` Estimated cost: $${spec.cost_estimate.monthly_total.toFixed(2)}/mo.` : ""}`,
        spec,
        yaml: data.yaml,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setActiveTab("diagram");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${errorMsg}` },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleDownload = async (format: string) => {
    if (!currentSpec) return;
    try {
      const res = await fetch(`${API_BASE}/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spec: currentSpec, format }),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const disposition = res.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename=([^\s;]+)/);
      const filename = match ? match[1] : `architecture.${format === "terraform" ? "tf" : "yaml"}`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // download is best-effort
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", background: "#ffffff" }}>
      {/* Sidebar - Chat */}
      <div
        style={{
          width: 420,
          borderRight: "1px solid #e2e8f0",
          display: "flex",
          flexDirection: "column",
          background: "#f8fafc",
        }}
      >
        <div style={{ padding: "16px 20px", borderBottom: "1px solid #e2e8f0" }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "#0f172a" }}>Cloudwright</h1>
          <p style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>Architecture Intelligence</p>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
          {messages.length === 0 && (
            <div style={{ color: "#64748b", padding: 20, textAlign: "center" }}>
              <p style={{ fontSize: 14 }}>Describe your cloud architecture</p>
              <p style={{ fontSize: 12, marginTop: 8, color: "#94a3b8" }}>
                "3-tier web app on AWS with CloudFront, ALB, EC2, and RDS"
              </p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                marginBottom: 12,
                padding: "10px 14px",
                borderRadius: 8,
                background: msg.role === "user" ? "#2563eb" : "#f1f5f9",
                color: msg.role === "user" ? "#ffffff" : "#1e293b",
                fontSize: 14,
                lineHeight: 1.5,
              }}
            >
              {renderMarkdown(msg.content)}
            </div>
          ))}
          {loading && (
            <div style={{ padding: "10px 14px", color: "#64748b", fontSize: 14 }}>
              Designing architecture...
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
        <div style={{ padding: 16, borderTop: "1px solid #e2e8f0" }}>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Describe your architecture..."
              style={{
                flex: 1,
                padding: "10px 14px",
                borderRadius: 8,
                border: "1px solid #e2e8f0",
                background: "#ffffff",
                color: "#0f172a",
                fontSize: 14,
                outline: "none",
              }}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              style={{
                padding: "10px 20px",
                borderRadius: 8,
                border: "none",
                background: loading ? "#e2e8f0" : "#2563eb",
                color: loading ? "#94a3b8" : "#fff",
                cursor: loading ? "not-allowed" : "pointer",
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Main content area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "#ffffff" }}>
        {/* Tabs */}
        <div style={{ display: "flex", borderBottom: "1px solid #e2e8f0", background: "#ffffff" }}>
          {(["diagram", "cost", "validate", "export", "spec", "modify"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: "12px 24px",
                border: "none",
                borderBottom: activeTab === tab ? "2px solid #2563eb" : "2px solid transparent",
                background: "transparent",
                color: activeTab === tab ? "#2563eb" : "#64748b",
                cursor: "pointer",
                fontSize: 14,
                fontWeight: 500,
                textTransform: "capitalize",
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "0.5rem 1rem" }}>
            <SummaryBar
              spec={currentSpec}
              onDownloadTerraform={currentSpec ? () => handleDownload("terraform") : undefined}
              onDownloadYaml={currentSpec ? () => handleDownload("yaml") : undefined}
              validationSummary={validationSummary}
            />
          </div>
          <div style={{ flex: 1, overflow: "auto" }}>

          {activeTab === "diagram" && currentSpec && (
            <ArchitectureDiagram spec={currentSpec} />
          )}
          {activeTab === "diagram" && !currentSpec && (
            <div style={{ padding: 32, color: "#64748b" }}>Design an architecture to see the diagram.</div>
          )}

          {activeTab === "cost" && currentSpec?.cost_estimate && (
            <CostTable estimate={currentSpec.cost_estimate} />
          )}
          {activeTab === "cost" && (!currentSpec || !currentSpec.cost_estimate) && (
            <div style={{ padding: 32, color: "#64748b" }}>No cost estimate available.</div>
          )}

          {activeTab === "spec" && currentSpec && (
            <SpecPanel
              spec={currentSpec as ArchSpec & { boundaries?: { id: string; kind: string; label?: string; component_ids: string[] }[] }}
              yaml={messages.findLast((m) => m.yaml)?.yaml || "No YAML available"}
            />
          )}
          {activeTab === "spec" && !currentSpec && (
            <div style={{ padding: 32, color: "#64748b" }}>Design an architecture first.</div>
          )}

          {activeTab === "validate" && currentSpec && (
            <ValidationPanel spec={currentSpec as unknown as Record<string, unknown>} apiBase={API_BASE} />
          )}
          {activeTab === "validate" && !currentSpec && (
            <div style={{ padding: 32, color: "#64748b" }}>Design an architecture first.</div>
          )}

          {activeTab === "export" && currentSpec && (
            <ExportPanel spec={currentSpec as unknown as Record<string, unknown>} apiBase={API_BASE} />
          )}
          {activeTab === "export" && !currentSpec && (
            <div style={{ padding: 32, color: "#64748b" }}>Design an architecture first.</div>
          )}

          {activeTab === "modify" && currentSpec && (
            <div style={{ padding: 32, maxWidth: 800 }}>
              <h2 style={{ fontSize: 18, marginBottom: 16, color: "#0f172a" }}>Modify Architecture</h2>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  value={modifyInput}
                  onChange={(e) => setModifyInput(e.target.value)}
                  onKeyDown={async (e) => {
                    if (e.key === "Enter" && modifyInput.trim()) {
                      setLoading(true);
                      try {
                        const res = await fetch(`${API_BASE}/modify`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ spec: currentSpec, instruction: modifyInput }),
                        });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail || "Modification failed");
                        setCurrentSpec(data.spec);
                        setModifyInput("");
                        setMessages((prev) => [...prev,
                          { role: "user", content: `Modify: ${modifyInput}` },
                          { role: "assistant", content: `Updated to ${data.spec.name} with ${data.spec.components.length} components.`, spec: data.spec, yaml: data.yaml },
                        ]);
                      } catch (err) {
                        setMessages((prev) => [...prev,
                          { role: "user", content: `Modify: ${modifyInput}` },
                          { role: "assistant", content: `Error: ${err instanceof Error ? err.message : "Modification failed"}` },
                        ]);
                      } finally {
                        setLoading(false);
                      }
                    }
                  }}
                  placeholder="e.g. Add a Redis cache between web and database"
                  style={{
                    flex: 1,
                    padding: "10px 14px",
                    borderRadius: 8,
                    border: "1px solid #e2e8f0",
                    background: "#ffffff",
                    color: "#0f172a",
                    fontSize: 14,
                    outline: "none",
                  }}
                />
              </div>
              <p style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>Press Enter to apply modification</p>
            </div>
          )}
          {activeTab === "modify" && !currentSpec && (
            <div style={{ padding: 32, color: "#64748b" }}>Design an architecture first.</div>
          )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
