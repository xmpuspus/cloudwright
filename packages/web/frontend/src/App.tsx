import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ArchitectureDiagram from "./components/ArchitectureDiagram";
import CostTable from "./components/CostTable";
import SummaryBar from "./components/SummaryBar";
import ValidationPanel from "./components/ValidationPanel";
import CompliancePanel from "./components/CompliancePanel";
import PlanPanel from "./components/PlanPanel";
import ReviewPanel from "./components/ReviewPanel";
import ExportPanel from "./components/ExportPanel";
import SpecPanel from "./components/SpecPanel";
import ConfirmDialog from "./components/ConfirmDialog";
import EmptyState from "./components/EmptyState";
import Icon, { type IconName } from "./components/Icon";
import { parseApiError, formatApiError } from "./lib/apiError";
import { useTheme } from "./lib/theme";
import { useToast } from "./lib/toast";

interface ArchSpec {
  name: string;
  provider: string;
  region: string;
  components: Component[];
  connections: Connection[];
  cost_estimate?: CostEstimate;
  metadata?: {
    suggestions?: string[];
    canvas?: { nodes?: Record<string, { x: number; y: number }> };
    modules?: {
      instances?: Record<string, {
        module_id: string;
        component_ids: string[];
        expected_component_count?: number;
        partial?: boolean;
        approved?: boolean;
      }>;
    };
    [key: string]: unknown;
  };
}

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

interface CostEstimate {
  monthly_total: number;
  breakdown: { component_id: string; service: string; monthly: number; notes: string }[];
  currency: string;
}

interface UsageInfo {
  model?: string;
  input_tokens?: number;
  output_tokens?: number;
  cost_usd?: number;
  latency_ms?: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  isError?: boolean;
  spec?: ArchSpec;
  yaml?: string;
  suggestions?: string[];
}

type LoadingStage = "idle" | "generating" | "modifying" | "costing" | "done";
type TabKey =
  | "diagram" | "cost" | "validate" | "compliance"
  | "plan" | "review" | "export" | "spec" | "modify";

const API_BASE = "/api";

const TABS: { key: TabKey; icon: IconName }[] = [
  { key: "diagram", icon: "grid" },
  { key: "cost", icon: "layers" },
  { key: "validate", icon: "check" },
  { key: "compliance", icon: "check" },
  { key: "plan", icon: "refresh" },
  { key: "review", icon: "alert" },
  { key: "export", icon: "download" },
  { key: "spec", icon: "panel" },
  { key: "modify", icon: "chat" },
];

const STAGE_TEXT: Record<Exclude<LoadingStage, "idle">, string> = {
  generating: "Generating architecture...",
  modifying: "Modifying architecture...",
  costing: "Estimating cost and validating...",
  done: "Finalizing...",
};

const EXAMPLE_PROMPT = "3-tier web app on AWS with CloudFront, ALB, EC2, and RDS";

const ALL_SUGGESTIONS = [
  "Add caching layer",
  "Reduce cost",
  "Increase redundancy",
  "Add monitoring",
  "Add security",
];

function pickSuggestions(spec: ArchSpec): string[] {
  // Prefer LLM-generated suggestions from spec metadata when available
  if (spec.metadata?.suggestions && spec.metadata.suggestions.length > 0) {
    return spec.metadata.suggestions.slice(0, 3);
  }

  const labels = spec.components.map((c) => c.label.toLowerCase());
  const services = spec.components.map((c) => c.service.toLowerCase());
  const hasCache = labels.some((l) => l.includes("cache") || l.includes("redis") || l.includes("elasticache")) ||
    services.some((s) => s.includes("cache") || s.includes("redis"));
  const hasMonitor = labels.some((l) => l.includes("monitor") || l.includes("cloudwatch") || l.includes("grafana")) ||
    services.some((s) => s.includes("cloudwatch") || s.includes("monitor"));
  const hasSecurity = labels.some((l) => l.includes("waf") || l.includes("firewall") || l.includes("security")) ||
    services.some((s) => s.includes("waf") || s.includes("shield"));

  return ALL_SUGGESTIONS
    .filter((s) => {
      if (s === "Add caching layer" && hasCache) return false;
      if (s === "Add monitoring" && hasMonitor) return false;
      if (s === "Add security" && hasSecurity) return false;
      return true;
    })
    .slice(0, 3);
}

function renderMarkdown(text: string): React.ReactNode[] {
  return text.split(/(\*\*.*?\*\*|`[^`]+`)/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return <code className="inline" key={i}>{part.slice(1, -1)}</code>;
    }
    return <span key={i}>{part}</span>;
  });
}

async function enrichSpec(
  rawSpec: ArchSpec,
  setValidationSummary: (v: { passed: number; total: number } | null) => void,
  signal?: AbortSignal,
): Promise<ArchSpec> {
  let spec = rawSpec;
  const [costResult, valResult] = await Promise.all([
    fetch(`${API_BASE}/cost`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec }),
      signal,
    }).then(r => r.ok ? r.json() : null).catch(() => null),
    fetch(`${API_BASE}/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec, compliance: [], well_architected: true }),
      signal,
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

interface StreamCallbacks {
  onStage: (stage: string, message?: string) => void;
  onSpec: (spec: ArchSpec, yaml: string) => void;
  onCost: (estimate: CostEstimate | null) => void;
  onValidation: (passed: number | null, total: number | null) => void;
  onDone: (spec: ArchSpec, yaml: string) => void;
  onUsage?: (usage: UsageInfo) => void;
}

/** Reads the SSE stream. Throws on a transport failure or a server `error` event,
 *  so the caller can decide whether a retry is safe. */
async function streamDesignOrModify(
  isModify: boolean,
  payload: object,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
) {
  const endpoint = isModify ? `${API_BASE}/modify/stream` : `${API_BASE}/design/stream`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) throw new Error(await parseApiError(response));

  const reader = response.body?.getReader();
  if (!reader) throw new Error("Streaming is not available in this browser.");

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
      let event: Record<string, unknown>;
      try {
        event = JSON.parse(line.slice(6));
      } catch {
        continue; // skip malformed events
      }
      switch (event.stage) {
        case "generating":
        case "costing":
        case "validating":
          callbacks.onStage(event.stage as string, event.message as string | undefined);
          break;
        case "generated":
          callbacks.onSpec(event.spec as ArchSpec, event.yaml as string);
          if (event.usage && callbacks.onUsage) callbacks.onUsage(event.usage as UsageInfo);
          break;
        case "costed":
          callbacks.onCost(event.cost_estimate as CostEstimate | null);
          break;
        case "validated":
          callbacks.onValidation(event.passed as number | null, event.total as number | null);
          break;
        case "done":
          callbacks.onDone(event.spec as ArchSpec, event.yaml as string);
          if (event.usage && callbacks.onUsage) callbacks.onUsage(event.usage as UsageInfo);
          break;
        case "error":
          throw new Error((event.message as string) || "The server reported an error.");
      }
    }
  }
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loadingStage, setLoadingStage] = useState<LoadingStage>("idle");
  const [currentSpec, setCurrentSpec] = useState<ArchSpec | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("diagram");
  const [visited, setVisited] = useState<Set<TabKey>>(() => new Set<TabKey>(["diagram"]));
  const [mobilePane, setMobilePane] = useState<"chat" | "workspace">("chat");
  const [confirmReset, setConfirmReset] = useState(false);

  const [modifyInput, setModifyInput] = useState("");
  const [validationSummary, setValidationSummary] = useState<{ passed: number; total: number } | null>(null);
  const [lastUsage, setLastUsage] = useState<UsageInfo | null>(null);

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const abortRef = useRef<AbortController | null>(null);

  const { theme, toggleTheme } = useTheme();
  const { notify } = useToast();

  const busy = loadingStage !== "idle";

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loadingStage]);

  const selectTab = useCallback((key: TabKey) => {
    setActiveTab(key);
    setVisited((seen) => (seen.has(key) ? seen : new Set(seen).add(key)));
    setMobilePane("workspace");
  }, []);

  // Grow the composer with its content, up to the CSS max-height.
  useEffect(() => {
    const node = inputRef.current;
    if (!node) return;
    node.style.height = "auto";
    node.style.height = `${Math.min(node.scrollHeight, 168)}px`;
  }, [input]);

  const runTurn = useCallback(
    async (instruction: string, options: { echoUser: boolean }) => {
      const isModify = currentSpec !== null;
      const controller = new AbortController();
      abortRef.current = controller;
      setLoadingStage(isModify ? "modifying" : "generating");

      let finalSpec: ArchSpec | null = null;
      let finalYaml = "";
      let streamFailed = false;
      let streamError: unknown = null;

      if (options.echoUser) {
        setMessages((prev) => [...prev, { role: "user", content: instruction }]);
      }

      const callbacks: StreamCallbacks = {
        onStage: (stage) => {
          if (stage === "generating") setLoadingStage(isModify ? "modifying" : "generating");
          else if (stage === "costing" || stage === "validating") setLoadingStage("costing");
        },
        onSpec: (spec) => {
          // Early render, so the diagram appears before pricing finishes.
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
          if (passed !== null) setValidationSummary({ passed, total: total ?? 0 });
        },
        onDone: (spec, yaml) => {
          finalSpec = spec;
          finalYaml = yaml;
          setCurrentSpec(spec);
          setLoadingStage("done");
        },
        onUsage: (usage) => setLastUsage(usage),
      };

      try {
        const payload = isModify ? { spec: currentSpec, instruction } : { description: instruction };

        try {
          await streamDesignOrModify(isModify, payload, callbacks, controller.signal);
        } catch (err) {
          if (controller.signal.aborted) throw err;
          streamFailed = true;
          streamError = err;
        }

        // Retry without streaming only when the stream produced nothing. Retrying
        // after a spec arrived would bill a second generation and overwrite the first.
        if (streamFailed && finalSpec !== null) throw streamError;

        if (streamFailed) {
          setLoadingStage(isModify ? "modifying" : "generating");
          const res = await fetch(`${API_BASE}/${isModify ? "modify" : "design"}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal: controller.signal,
          });
          const data = await res.json();
          if (!res.ok) throw new Error(formatApiError(data));
          finalYaml = data.yaml;
          if (data.usage) setLastUsage(data.usage as UsageInfo);

          setLoadingStage("costing");
          finalSpec = await enrichSpec(data.spec as ArchSpec, setValidationSummary, controller.signal);
          setCurrentSpec(finalSpec);
          setLoadingStage("done");
        }

        const spec = finalSpec as ArchSpec | null;
        if (!spec) throw new Error("The server returned no architecture.");

        const verb = isModify ? "Modified" : "Designed";
        const cost = spec.cost_estimate
          ? ` Estimated cost: $${spec.cost_estimate.monthly_total.toFixed(2)}/mo.`
          : "";
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `${verb} **${spec.name}** with ${spec.components.length} components on ${spec.provider.toUpperCase()}.${cost}`,
            spec,
            yaml: finalYaml,
            suggestions: pickSuggestions(spec),
          },
        ]);
        selectTab("diagram");
      } catch (err) {
        if (controller.signal.aborted) {
          setMessages((prev) => [...prev, { role: "assistant", content: "Stopped.", isError: true }]);
        } else {
          const text = err instanceof Error ? err.message : "Unknown error";
          setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${text}`, isError: true }]);
          notify(text);
        }
      } finally {
        abortRef.current = null;
        setLoadingStage("idle");
        inputRef.current?.focus();
      }
    },
    [currentSpec, notify, selectTab],
  );

  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    void runTurn(text, { echoUser: true });
  }, [busy, input, runTurn]);

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const resetSession = useCallback(() => {
    setConfirmReset(false);
    setCurrentSpec(null);
    setMessages([]);
    setValidationSummary(null);
    setLastUsage(null);
    setVisited(new Set<TabKey>(["diagram"]));
    setActiveTab("diagram");
    inputRef.current?.focus();
  }, []);

  const handleDownload = useCallback(
    async (format: string) => {
      if (!currentSpec) return;
      try {
        const res = await fetch(`${API_BASE}/download`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ spec: currentSpec, format }),
        });
        if (!res.ok) {
          notify(await parseApiError(res));
          return;
        }
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
        notify("Download failed. Check that the server is still running.");
      }
    },
    [currentSpec, notify],
  );

  const handleSpecChange = useCallback(
    async (updatedSpec: ArchSpec) => {
      setCurrentSpec(updatedSpec);
      setValidationSummary(null);
      try {
        setCurrentSpec(await enrichSpec(updatedSpec, setValidationSummary));
      } catch {
        // Keep the deterministic canvas edit even if cost or validation refresh fails.
      }
    },
    [],
  );

  // Arrow-key roving focus across the tab list, per the WAI-ARIA tabs pattern.
  const onTabKeyDown = useCallback(
    (event: React.KeyboardEvent, index: number) => {
      const keys: Record<string, number> = {
        ArrowRight: index + 1,
        ArrowLeft: index - 1,
        Home: 0,
        End: TABS.length - 1,
      };
      const target = keys[event.key];
      if (target === undefined) return;
      event.preventDefault();
      const next = TABS[(target + TABS.length) % TABS.length];
      selectTab(next.key);
      tabRefs.current[next.key]?.focus();
    },
    [selectTab],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const meta = event.metaKey || event.ctrlKey;
      if (meta && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setMobilePane("chat");
        inputRef.current?.focus();
        return;
      }
      if (meta && /^[1-9]$/.test(event.key)) {
        event.preventDefault();
        selectTab(TABS[Number(event.key) - 1].key);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectTab]);

  const lastYaml = useMemo(
    () => messages.filter((m) => m.yaml).pop()?.yaml ?? "",
    [messages],
  );

  const specRecord = currentSpec as unknown as Record<string, unknown>;

  const panelPlaceholder = (label: string) => (
    <EmptyState
      icon="layers"
      title={`No architecture yet, so ${label} has nothing to work on.`}
      hint="Describe a system in the chat panel, then come back to this tab."
      action={{
        label: "Write a description",
        onClick: () => {
          setMobilePane("chat");
          inputRef.current?.focus();
        },
      }}
    />
  );

  return (
    <div className="app">
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>

      <aside className={`sidebar app__pane${mobilePane === "chat" ? " app__pane--active" : ""}`}>
        <div className="sidebar__header">
          <div className="brand">
            <Icon className="brand__mark" name="cloud" size={22} strokeWidth={1.7} />
            <div>
              <h1 className="brand__name">Cloudwright</h1>
              <p className="brand__tagline">Architecture Intelligence</p>
            </div>
          </div>
          <button
            className="btn btn--ghost btn--icon"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          >
            <Icon name={theme === "dark" ? "sun" : "moon"} size={16} />
          </button>
          {currentSpec && (
            <button className="btn btn--sm" onClick={() => setConfirmReset(true)}>
              New
            </button>
          )}
        </div>

        <div className="chat">
          {messages.length === 0 && (
            <div className="empty">
              <Icon className="empty__icon" name="chat" size={34} strokeWidth={1.4} />
              <p className="empty__title">Describe your cloud architecture</p>
              <p className="empty__hint">
                Plain English in, a typed spec with costs, compliance findings and Terraform out.
              </p>
              <button
                className="chip"
                onClick={() => {
                  setInput(EXAMPLE_PROMPT);
                  inputRef.current?.focus();
                }}
              >
                {EXAMPLE_PROMPT}
              </button>
            </div>
          )}

          {messages.map((msg, i) => (
            <div className="msg-group" key={i}>
              <div
                data-testid={msg.role === "user" ? "msg-user" : "msg-assistant"}
                className={`msg msg--${msg.isError ? "error" : msg.role}`}
              >
                {renderMarkdown(msg.content)}
              </div>
              {msg.role === "assistant" && msg.spec && msg.suggestions && msg.suggestions.length > 0 && (
                <div className="suggestions">
                  {msg.suggestions.map((s) => (
                    <button
                      key={s}
                      className="chip"
                      disabled={busy}
                      onClick={() => {
                        setInput(s);
                        inputRef.current?.focus();
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          <div className="status-row" role="status" aria-live="polite">
            {busy && (
              <>
                <span className="spinner" />
                {STAGE_TEXT[loadingStage as Exclude<LoadingStage, "idle">]}
              </>
            )}
          </div>
          <div ref={chatEndRef} />
        </div>

        <div className="composer">
          <div className="composer__box">
            <textarea
              ref={inputRef}
              className="composer__input"
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                // isComposing guard: an input method confirming a candidate also fires Enter.
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Describe your architecture..."
              aria-label="Describe your architecture"
            />
            {busy ? (
              <button className="btn btn--sm" onClick={stopGeneration}>
                <Icon name="stop" size={13} />
                Stop
              </button>
            ) : (
              <button className="btn btn--primary btn--sm" onClick={sendMessage} disabled={!input.trim()}>
                <Icon name="send" size={13} />
                Send
              </button>
            )}
          </div>
          <div className="composer__hint">
            <span>
              <kbd>Enter</kbd> sends, <kbd>Shift</kbd>+<kbd>Enter</kbd> adds a line
            </span>
            <span>
              <kbd>{navigator.platform.includes("Mac") ? "Cmd" : "Ctrl"}</kbd>+<kbd>K</kbd> focuses
            </span>
          </div>
        </div>

        <div className="pane-switch">
          <button className="btn btn--sm" aria-pressed="true" onClick={() => setMobilePane("chat")}>
            Chat
          </button>
          <button className="btn btn--sm" aria-pressed="false" onClick={() => setMobilePane("workspace")}>
            Workspace
          </button>
        </div>
      </aside>

      <main
        id="workspace"
        className={`workspace app__pane${mobilePane === "workspace" ? " app__pane--active" : ""}`}
      >
        <div className="workspace__header">
          <div className="tabs" role="tablist" aria-label="Workspace views">
            {TABS.map((tab, index) => (
              <button
                key={tab.key}
                ref={(node) => { tabRefs.current[tab.key] = node; }}
                className="tab"
                role="tab"
                id={`tab-${tab.key}`}
                aria-selected={activeTab === tab.key}
                aria-controls={`panel-${tab.key}`}
                tabIndex={activeTab === tab.key ? 0 : -1}
                onClick={() => selectTab(tab.key)}
                onKeyDown={(event) => onTabKeyDown(event, index)}
              >
                {tab.key}
              </button>
            ))}
          </div>
        </div>

        <SummaryBar
          spec={currentSpec}
          onDownloadTerraform={currentSpec ? () => handleDownload("terraform") : undefined}
          onDownloadYaml={currentSpec ? () => handleDownload("yaml") : undefined}
          validationSummary={validationSummary}
          usage={lastUsage}
        />

        <div className="panel-host">
          {visited.has("diagram") && (
            <section
              className="panel"
              id="panel-diagram"
              role="tabpanel"
              aria-labelledby="tab-diagram"
              hidden={activeTab !== "diagram"}
              style={{ overflow: "hidden" }}
            >
              {currentSpec ? (
                <div className="diagram">
                  <ArchitectureDiagram spec={currentSpec} onSpecChange={handleSpecChange} />
                  {busy && (
                    <div className="canvas-status">
                      <span className="dot-pulse" />
                      {STAGE_TEXT[loadingStage as Exclude<LoadingStage, "idle">]}
                    </div>
                  )}
                </div>
              ) : (
                <EmptyState
                  icon="grid"
                  title="Design an architecture to see the diagram."
                  hint="Every component, connection and trust boundary is drawn from the spec, and stays editable."
                  action={{
                    label: "Start with the example",
                    onClick: () => {
                      setMobilePane("chat");
                      setInput(EXAMPLE_PROMPT);
                      inputRef.current?.focus();
                    },
                  }}
                />
              )}
            </section>
          )}

          {visited.has("cost") && (
            <section className="panel" id="panel-cost" role="tabpanel" aria-labelledby="tab-cost" hidden={activeTab !== "cost"}>
              {currentSpec?.cost_estimate
                ? <CostTable estimate={currentSpec.cost_estimate} />
                : panelPlaceholder("the cost breakdown")}
            </section>
          )}

          {visited.has("validate") && (
            <section className="panel" id="panel-validate" role="tabpanel" aria-labelledby="tab-validate" hidden={activeTab !== "validate"}>
              {currentSpec ? <ValidationPanel spec={specRecord} apiBase={API_BASE} /> : panelPlaceholder("validation")}
            </section>
          )}

          {visited.has("compliance") && (
            <section className="panel" id="panel-compliance" role="tabpanel" aria-labelledby="tab-compliance" hidden={activeTab !== "compliance"}>
              {currentSpec ? <CompliancePanel spec={specRecord} apiBase={API_BASE} /> : panelPlaceholder("the control mapping")}
            </section>
          )}

          {visited.has("plan") && (
            <section className="panel" id="panel-plan" role="tabpanel" aria-labelledby="tab-plan" hidden={activeTab !== "plan"}>
              {currentSpec ? <PlanPanel spec={specRecord} apiBase={API_BASE} /> : panelPlaceholder("the deploy check")}
            </section>
          )}

          {visited.has("review") && (
            <section className="panel" id="panel-review" role="tabpanel" aria-labelledby="tab-review" hidden={activeTab !== "review"}>
              {currentSpec ? <ReviewPanel spec={specRecord} apiBase={API_BASE} /> : panelPlaceholder("the review")}
            </section>
          )}

          {visited.has("export") && (
            <section className="panel" id="panel-export" role="tabpanel" aria-labelledby="tab-export" hidden={activeTab !== "export"}>
              {currentSpec ? <ExportPanel spec={specRecord} apiBase={API_BASE} /> : panelPlaceholder("export")}
            </section>
          )}

          {visited.has("spec") && (
            <section className="panel" id="panel-spec" role="tabpanel" aria-labelledby="tab-spec" hidden={activeTab !== "spec"}>
              {currentSpec
                ? <SpecPanel spec={currentSpec as ArchSpec & { boundaries?: { id: string; kind: string; label?: string; component_ids: string[] }[] }} yaml={lastYaml} apiBase={API_BASE} />
                : panelPlaceholder("the spec view")}
            </section>
          )}

          {visited.has("modify") && (
            <section className="panel" id="panel-modify" role="tabpanel" aria-labelledby="tab-modify" hidden={activeTab !== "modify"}>
              {currentSpec ? (
                <div className="panel__body">
                  <h2 className="panel__title">Change this architecture in one sentence</h2>
                  <p className="panel__lede">
                    The same engine the chat panel uses. Cost and validation refresh after every change.
                  </p>
                  <div style={{ display: "flex", gap: "var(--space-2)", maxWidth: 640 }}>
                    <input
                      className="field"
                      value={modifyInput}
                      aria-label="Modification instruction"
                      disabled={busy}
                      onChange={(e) => setModifyInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key !== "Enter" || e.nativeEvent.isComposing) return;
                        const instruction = modifyInput.trim();
                        if (!instruction || busy) return;
                        setModifyInput("");
                        void runTurn(instruction, { echoUser: true });
                      }}
                      placeholder="e.g. Add a Redis cache between web and database"
                    />
                    <button
                      className="btn btn--primary"
                      disabled={busy || !modifyInput.trim()}
                      onClick={() => {
                        const instruction = modifyInput.trim();
                        if (!instruction) return;
                        setModifyInput("");
                        void runTurn(instruction, { echoUser: true });
                      }}
                    >
                      Apply
                    </button>
                  </div>
                  <div className="status-row" role="status" aria-live="polite">
                    {busy && (
                      <>
                        <span className="spinner" />
                        {STAGE_TEXT[loadingStage as Exclude<LoadingStage, "idle">]}
                      </>
                    )}
                  </div>
                </div>
              ) : (
                panelPlaceholder("modification")
              )}
            </section>
          )}
        </div>

        <div className="pane-switch">
          <button className="btn btn--sm" aria-pressed="false" onClick={() => setMobilePane("chat")}>
            Chat
          </button>
          <button className="btn btn--sm" aria-pressed="true" onClick={() => setMobilePane("workspace")}>
            Workspace
          </button>
        </div>
      </main>

      <ConfirmDialog
        open={confirmReset}
        title="Discard this session?"
        body="The current architecture, the chat history and every panel result are cleared."
        confirmLabel="Discard and start fresh"
        destructive
        onConfirm={resetSession}
        onCancel={() => setConfirmReset(false)}
      />
    </div>
  );
}

export default App;
