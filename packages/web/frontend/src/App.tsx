import React, { useState, useRef, useEffect } from "react";
import ArchitectureDiagram from "./components/ArchitectureDiagram";
import CostTable from "./components/CostTable";

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

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentSpec, setCurrentSpec] = useState<ArchSpec | null>(null);
  const [activeTab, setActiveTab] = useState<
    "chat" | "diagram" | "cost" | "yaml" | "validate" | "export" | "modify"
  >("chat");
  const [validateResult, setValidateResult] = useState<unknown>(null);
  const [exportResult, setExportResult] = useState<string>("");
  const [exportFormat, setExportFormat] = useState("terraform");
  const [modifyInput, setModifyInput] = useState("");
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
      const spec = data.spec as ArchSpec;
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

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      {/* Sidebar - Chat */}
      <div
        style={{
          width: 420,
          borderRight: "1px solid #1e293b",
          display: "flex",
          flexDirection: "column",
          background: "#0f172a",
        }}
      >
        <div style={{ padding: "16px 20px", borderBottom: "1px solid #1e293b" }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "#f8fafc" }}>Cloudwright</h1>
          <p style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>Architecture Intelligence</p>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
          {messages.length === 0 && (
            <div style={{ color: "#475569", padding: 20, textAlign: "center" }}>
              <p style={{ fontSize: 14 }}>Describe your cloud architecture</p>
              <p style={{ fontSize: 12, marginTop: 8, color: "#334155" }}>
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
                background: msg.role === "user" ? "#1e40af" : "#1e293b",
                fontSize: 14,
                lineHeight: 1.5,
              }}
            >
              {msg.content}
            </div>
          ))}
          {loading && (
            <div style={{ padding: "10px 14px", color: "#64748b", fontSize: 14 }}>
              Designing architecture...
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
        <div style={{ padding: 16, borderTop: "1px solid #1e293b" }}>
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
                border: "1px solid #334155",
                background: "#1e293b",
                color: "#f8fafc",
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
                background: loading ? "#334155" : "#2563eb",
                color: "#fff",
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
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Tabs */}
        <div style={{ display: "flex", borderBottom: "1px solid #1e293b", background: "#0f172a" }}>
          {(["chat", "diagram", "cost", "yaml", "validate", "export", "modify"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: "12px 24px",
                border: "none",
                borderBottom: activeTab === tab ? "2px solid #3b82f6" : "2px solid transparent",
                background: "transparent",
                color: activeTab === tab ? "#f8fafc" : "#64748b",
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
        <div style={{ flex: 1, overflow: "auto" }}>
          {activeTab === "chat" && (
            <div style={{ padding: 32, maxWidth: 800 }}>
              <h2 style={{ fontSize: 18, marginBottom: 16 }}>Welcome to Cloudwright</h2>
              <p style={{ color: "#94a3b8", lineHeight: 1.6 }}>
                Describe your cloud architecture in natural language. Cloudwright will design it,
                estimate costs, validate compliance, and export to Terraform.
              </p>
              <div style={{ marginTop: 24 }}>
                <h3 style={{ fontSize: 14, color: "#64748b", marginBottom: 12 }}>Try these:</h3>
                {[
                  "3-tier web app on AWS with CloudFront, ALB, EC2, and RDS",
                  "Serverless API with API Gateway, Lambda, and DynamoDB",
                  "ML pipeline with S3, SageMaker, and Redshift",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      setInput(suggestion);
                      inputRef.current?.focus();
                    }}
                    style={{
                      display: "block",
                      width: "100%",
                      textAlign: "left",
                      padding: "12px 16px",
                      marginBottom: 8,
                      borderRadius: 8,
                      border: "1px solid #1e293b",
                      background: "#1e293b",
                      color: "#cbd5e1",
                      cursor: "pointer",
                      fontSize: 13,
                    }}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

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

          {activeTab === "yaml" && currentSpec && (
            <div style={{ padding: 32 }}>
              <pre
                style={{
                  background: "#1e293b",
                  padding: 20,
                  borderRadius: 8,
                  fontSize: 13,
                  lineHeight: 1.6,
                  overflow: "auto",
                  color: "#e2e8f0",
                }}
              >
                {messages.findLast((m) => m.yaml)?.yaml || "No YAML available"}
              </pre>
            </div>
          )}

          {activeTab === "validate" && currentSpec && (
            <div style={{ padding: 32, maxWidth: 800 }}>
              <h2 style={{ fontSize: 18, marginBottom: 16 }}>Validate Architecture</h2>
              <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                {["hipaa", "pci-dss", "soc2", "well-architected"].map((fw) => (
                  <button
                    key={fw}
                    onClick={async () => {
                      try {
                        const isWA = fw === "well-architected";
                        const res = await fetch(`${API_BASE}/validate`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({
                            spec: currentSpec,
                            compliance: isWA ? [] : [fw],
                            well_architected: isWA,
                          }),
                        });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail || "Validation failed");
                        setValidateResult(data.results);
                      } catch (err) {
                        setValidateResult({ error: err instanceof Error ? err.message : "Validation failed" });
                      }
                    }}
                    style={{
                      padding: "8px 16px",
                      borderRadius: 6,
                      border: "1px solid #334155",
                      background: "#1e293b",
                      color: "#cbd5e1",
                      cursor: "pointer",
                      fontSize: 13,
                    }}
                  >
                    {fw.toUpperCase()}
                  </button>
                ))}
              </div>
              {validateResult && (
                <pre style={{ background: "#1e293b", padding: 16, borderRadius: 8, fontSize: 12, color: "#e2e8f0", overflow: "auto" }}>
                  {JSON.stringify(validateResult, null, 2)}
                </pre>
              )}
            </div>
          )}
          {activeTab === "validate" && !currentSpec && (
            <div style={{ padding: 32, color: "#64748b" }}>Design an architecture first.</div>
          )}

          {activeTab === "export" && currentSpec && (
            <div style={{ padding: 32, maxWidth: 800 }}>
              <h2 style={{ fontSize: 18, marginBottom: 16 }}>Export Architecture</h2>
              <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                {["terraform", "cloudformation", "mermaid", "d2", "sbom", "aibom"].map((fmt) => (
                  <button
                    key={fmt}
                    onClick={async () => {
                      try {
                        setExportFormat(fmt);
                        const res = await fetch(`${API_BASE}/export`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ spec: currentSpec, format: fmt }),
                        });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail || "Export failed");
                        setExportResult(data.content || JSON.stringify(data, null, 2));
                      } catch (err) {
                        setExportResult(`Error: ${err instanceof Error ? err.message : "Export failed"}`);
                      }
                    }}
                    style={{
                      padding: "8px 16px",
                      borderRadius: 6,
                      border: exportFormat === fmt ? "1px solid #3b82f6" : "1px solid #334155",
                      background: exportFormat === fmt ? "#1e3a5f" : "#1e293b",
                      color: "#cbd5e1",
                      cursor: "pointer",
                      fontSize: 13,
                    }}
                  >
                    {fmt}
                  </button>
                ))}
              </div>
              {exportResult && (
                <pre style={{ background: "#1e293b", padding: 16, borderRadius: 8, fontSize: 12, color: "#e2e8f0", overflow: "auto", maxHeight: 600 }}>
                  {exportResult}
                </pre>
              )}
            </div>
          )}
          {activeTab === "export" && !currentSpec && (
            <div style={{ padding: 32, color: "#64748b" }}>Design an architecture first.</div>
          )}

          {activeTab === "modify" && currentSpec && (
            <div style={{ padding: 32, maxWidth: 800 }}>
              <h2 style={{ fontSize: 18, marginBottom: 16 }}>Modify Architecture</h2>
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
                    border: "1px solid #334155",
                    background: "#1e293b",
                    color: "#f8fafc",
                    fontSize: 14,
                    outline: "none",
                  }}
                />
              </div>
              <p style={{ fontSize: 12, color: "#475569", marginTop: 8 }}>Press Enter to apply modification</p>
            </div>
          )}
          {activeTab === "modify" && !currentSpec && (
            <div style={{ padding: 32, color: "#64748b" }}>Design an architecture first.</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
