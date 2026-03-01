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

type LoadingStage = "idle" | "generating" | "modifying" | "costing" | "done";

const API_BASE = "/api";

function renderMarkdown(text: string): React.ReactNode[] {
  return text.split(/(\*\*.*?\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : <span key={i}>{part}</span>
  );
}

async function enrichSpec(
  rawSpec: ArchSpec,
  setValidationSummary: (v: { passed: number; total: number } | null) => void,
): Promise<ArchSpec> {
  let spec = rawSpec;
  const [costResult, valResult] = await Promise.all([
    fetch(`${API_BASE}/cost`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec }),
    }).then(r => r.ok ? r.json() : null).catch(() => null),
    fetch(`${API_BASE}/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec, compliance: [], well_architected: true }),
    }).then(r => r.ok ? r.json() : null).catch(() => null),
  ]);

  if (costResult?.estimate) {
    spec = { ...spec, cost_estimate: costResult.estimate };
  }
  if (valResult?.results?.length > 0) {
    const checks = valResult.results[0].checks || [];
    const passed = checks.filter((c: { passed: boolean }) => c.passed).length;
    setValidationSummary({ passed, total: checks.length });
  }
  return spec;
}

async function streamDesignOrModify(
  isModify: boolean,
  payload: object,
  callbacks: {
    onStage: (stage: string, message?: string) => void;
    onSpec: (spec: ArchSpec, yaml: string) => void;
    onCost: (estimate: CostEstimate | null) => void;
    onValidation: (passed: number | null, total: number | null) => void;
    onDone: (spec: ArchSpec, yaml: string) => void;
    onError: (message: string) => void;
  }
) {
  const endpoint = isModify ? `${API_BASE}/modify/stream` : `${API_BASE}/design/stream`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const data = await response.json();
    callbacks.onError(data.detail || "Request failed");
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const event = JSON.parse(line.slice(6));
        switch (event.stage) {
          case "generating":
          case "costing":
          case "validating":
            callbacks.onStage(event.stage, event.message);
            break;
          case "generated":
            callbacks.onSpec(event.spec, event.yaml);
            break;
          case "costed":
            callbacks.onCost(event.cost_estimate);
            break;
          case "validated":
            callbacks.onValidation(event.passed, event.total);
            break;
          case "done":
            callbacks.onDone(event.spec, event.yaml);
            break;
          case "error":
            callbacks.onError(event.message);
            break;
        }
      } catch { /* skip malformed events */ }
    }
  }
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loadingStage, setLoadingStage] = useState<LoadingStage>("idle");
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
    if (!input.trim() || loadingStage !== "idle") return;
    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    const isModify = currentSpec !== null;
    setLoadingStage(isModify ? "modifying" : "generating");

    // Track final spec and yaml across streaming callbacks
    let finalSpec: ArchSpec | null = null;
    let finalYaml = "";
    let streamSucceeded = false;

    try {
      const payload = isModify
        ? { spec: currentSpec, instruction: input }
        : { description: input };

      // Try streaming endpoint first; fall back to regular on failure
      try {
        await streamDesignOrModify(isModify, payload, {
          onStage: (stage) => {
            if (stage === "generating") setLoadingStage("generating");
            else if (stage === "costing" || stage === "validating") setLoadingStage("costing");
          },
          onSpec: (spec) => {
            // Early render — show diagram as soon as spec is ready
            setCurrentSpec(spec);
            finalSpec = spec;
            setLoadingStage("costing");
          },
          onCost: (estimate) => {
            if (estimate && finalSpec) {
              finalSpec = { ...finalSpec, cost_estimate: estimate };
              setCurrentSpec(finalSpec);
            }
          },
          onValidation: (passed, total) => {
            if (passed !== null) setValidationSummary({ passed, total: total! });
          },
          onDone: (spec, yaml) => {
            finalSpec = spec;
            finalYaml = yaml;
            setCurrentSpec(spec);
            setLoadingStage("done");
          },
          onError: (msg) => { throw new Error(msg); },
        });
        streamSucceeded = finalSpec !== null;
      } catch {
        // Streaming endpoint not available or failed — fall through to non-streaming
        setLoadingStage(isModify ? "modifying" : "generating");
      }

      if (!streamSucceeded) {
        // Non-streaming fallback
        const res = isModify
          ? await fetch(`${API_BASE}/modify`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ spec: currentSpec, instruction: input }),
            })
          : await fetch(`${API_BASE}/design`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ description: input }),
            });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Request failed");
        finalSpec = data.spec as ArchSpec;
        finalYaml = data.yaml;

        setLoadingStage("costing");
        finalSpec = await enrichSpec(finalSpec, setValidationSummary);
        setCurrentSpec(finalSpec);
        setLoadingStage("done");
      }

      const spec = finalSpec!;
      const verb = isModify ? "Modified" : "Designed";
      const assistantMsg: Message = {
        role: "assistant",
        content: `${verb} **${spec.name}** with ${spec.components.length} components on ${spec.provider.toUpperCase()}.${spec.cost_estimate ? ` Estimated cost: $${spec.cost_estimate.monthly_total.toFixed(2)}/mo.` : ""}`,
        spec,
        yaml: finalYaml,
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
      setLoadingStage("idle");
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
        <div style={{ padding: "16px 20px", borderBottom: "1px solid #e2e8f0", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "#0f172a" }}>Cloudwright</h1>
            <p style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>Architecture Intelligence</p>
          </div>
          {currentSpec && (
            <button
              onClick={() => { setCurrentSpec(null); setMessages([]); setValidationSummary(null); }}
              style={{ padding: "5px 12px", borderRadius: 6, border: "1px solid #e2e8f0", background: "#ffffff", color: "#64748b", cursor: "pointer", fontSize: 12, fontWeight: 500 }}
            >
              New
            </button>
          )}
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
          {loadingStage !== "idle" && (
            <div style={{ padding: "10px 14px", color: "#64748b", fontSize: 14 }}>
              {loadingStage === "generating" && "Generating architecture..."}
              {loadingStage === "modifying" && "Modifying architecture..."}
              {loadingStage === "costing" && "Estimating cost & validating..."}
              {loadingStage === "done" && "Finalizing..."}
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
              disabled={loadingStage !== "idle" || !input.trim()}
              style={{
                padding: "10px 20px",
                borderRadius: 8,
                border: "none",
                background: loadingStage !== "idle" ? "#e2e8f0" : "#2563eb",
                color: loadingStage !== "idle" ? "#94a3b8" : "#fff",
                cursor: loadingStage !== "idle" ? "not-allowed" : "pointer",
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

          {activeTab === "diagram" && (currentSpec || loadingStage !== "idle") && (
            <div style={{ position: "relative", width: "100%", height: "100%" }}>
              {currentSpec && <ArchitectureDiagram spec={currentSpec} />}
              {loadingStage !== "idle" && (
                <div style={{
                  position: "absolute", top: 16, right: 16,
                  background: "rgba(37, 99, 235, 0.9)", color: "white",
                  padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500,
                  display: "flex", alignItems: "center", gap: 8,
                }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: "50%",
                    background: "white", animation: "pulse 1s infinite",
                  }} />
                  {loadingStage === "generating" ? "Generating..." :
                   loadingStage === "modifying" ? "Modifying..." :
                   loadingStage === "costing" ? "Costing & validating..." : "Finalizing..."}
                </div>
              )}
            </div>
          )}
          {activeTab === "diagram" && !currentSpec && loadingStage === "idle" && (
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
                    if (e.key === "Enter" && modifyInput.trim() && loadingStage === "idle") {
                      const instruction = modifyInput;
                      setModifyInput("");
                      setLoadingStage("modifying");
                      try {
                        const res = await fetch(`${API_BASE}/modify`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ spec: currentSpec, instruction }),
                        });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail || "Modification failed");
                        const rawSpec = data.spec as ArchSpec;

                        setLoadingStage("costing");
                        const spec = await enrichSpec(rawSpec, setValidationSummary);
                        setCurrentSpec(spec);
                        setLoadingStage("done");

                        setMessages((prev) => [...prev,
                          { role: "user", content: instruction },
                          { role: "assistant", content: `Modified **${spec.name}** with ${spec.components.length} components on ${spec.provider.toUpperCase()}.${spec.cost_estimate ? ` Estimated cost: $${spec.cost_estimate.monthly_total.toFixed(2)}/mo.` : ""}`, spec, yaml: data.yaml },
                        ]);
                      } catch (err) {
                        setMessages((prev) => [...prev,
                          { role: "user", content: instruction },
                          { role: "assistant", content: `Error: ${err instanceof Error ? err.message : "Modification failed"}` },
                        ]);
                      } finally {
                        setLoadingStage("idle");
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
