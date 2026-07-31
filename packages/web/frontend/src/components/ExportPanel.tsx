import React, { useState, useCallback, useRef } from "react";
import { parseApiError } from "../lib/apiError";
import EmptyState from "./EmptyState";
import Icon from "./Icon";

interface ExportPanelProps {
  spec: Record<string, unknown>;
  apiBase: string;
}

interface Format {
  key: string;
  label: string;
  ext: string;
  tag: string;
  desc: string;
  group: string;
}

/** Mirrors cloudwright.exporter.FORMATS. svg and png are binary, so the diagram
 *  toolbar downloads those instead of showing them as text here. */
const FORMATS: Format[] = [
  { key: "terraform", label: "Terraform", ext: "tf", tag: "HCL", desc: "HashiCorp Configuration Language", group: "Infrastructure as code" },
  { key: "opentofu", label: "OpenTofu", ext: "tf", tag: "TOFU", desc: "Fork-safe Terraform dialect", group: "Infrastructure as code" },
  { key: "pulumi-ts", label: "Pulumi TypeScript", ext: "ts", tag: "TS", desc: "Pulumi program in TypeScript", group: "Infrastructure as code" },
  { key: "pulumi-python", label: "Pulumi Python", ext: "py", tag: "PY", desc: "Pulumi program in Python", group: "Infrastructure as code" },
  { key: "cloudformation", label: "CloudFormation", ext: "yaml", tag: "CFN", desc: "AWS CloudFormation template", group: "Infrastructure as code" },
  { key: "mermaid", label: "Mermaid", ext: "mmd", tag: "MMD", desc: "Renders in GitHub and Notion", group: "Diagram source" },
  { key: "d2", label: "D2", ext: "d2", tag: "D2", desc: "D2 diagram language", group: "Diagram source" },
  { key: "c4", label: "C4", ext: "dsl", tag: "C4", desc: "Structurizr C4 model", group: "Diagram source" },
  { key: "ascii", label: "ASCII", ext: "txt", tag: "TXT", desc: "Plain text for a terminal or a commit message", group: "Diagram source" },
  { key: "sbom", label: "SBOM", ext: "json", tag: "BOM", desc: "CycloneDX software bill of materials", group: "Inventory and report" },
  { key: "aibom", label: "AIBOM", ext: "json", tag: "AI", desc: "OWASP AI bill of materials", group: "Inventory and report" },
  { key: "compliance", label: "Compliance report", ext: "md", tag: "MD", desc: "Findings and controls in Markdown", group: "Inventory and report" },
  { key: "html", label: "HTML report", ext: "html", tag: "WEB", desc: "Self-contained shareable page", group: "Inventory and report" },
];

const GROUPS = ["Infrastructure as code", "Diagram source", "Inventory and report"];

const TAG_COLORS: Record<string, string> = {
  terraform: "#7c3aed",
  opentofu: "#facc15",
  "pulumi-ts": "#4f46e5",
  "pulumi-python": "#4f46e5",
  cloudformation: "#ea580c",
  mermaid: "#0891b2",
  d2: "#4f46e5",
  c4: "#0f766e",
  ascii: "#64748b",
  sbom: "#059669",
  aibom: "#2563eb",
  compliance: "#be123c",
  html: "#0284c7",
};

function FormatTag({ format }: { format: Format | undefined }) {
  if (!format) return null;
  const color = TAG_COLORS[format.key] || "var(--text-subtle)";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        minWidth: 36,
        height: 20,
        padding: "0 5px",
        borderRadius: "var(--radius-sm)",
        fontSize: "var(--text-2xs)",
        fontWeight: 700,
        letterSpacing: "0.04em",
        background: `${color}1f`,
        color,
        flexShrink: 0,
      }}
    >
      {format.tag}
    </span>
  );
}

export default function ExportPanel({ spec, apiBase }: ExportPanelProps) {
  const [activeFormat, setActiveFormat] = useState<string | null>(null);
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const preRef = useRef<HTMLPreElement>(null);

  const runExport = useCallback(
    async (fmt: string) => {
      setActiveFormat(fmt);
      setLoading(true);
      setError(null);
      setCopied(false);
      try {
        const res = await fetch(`${apiBase}/export`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ spec, format: fmt }),
        });
        if (!res.ok) throw new Error(await parseApiError(res));
        const data = await res.json();
        setContent(data.content || JSON.stringify(data, null, 2));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Export failed");
        setContent("");
      } finally {
        setLoading(false);
      }
    },
    [spec, apiBase],
  );

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard is blocked outside a secure context. Select the text instead.
      const el = preRef.current;
      if (el) {
        const range = document.createRange();
        range.selectNodeContents(el);
        window.getSelection()?.removeAllRanges();
        window.getSelection()?.addRange(range);
      }
    }
  }, [content]);

  const activeFmt = FORMATS.find((f) => f.key === activeFormat);

  const handleDownload = useCallback(() => {
    if (!content || !activeFormat) return;
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `architecture.${activeFmt?.ext || "txt"}`;
    a.click();
    URL.revokeObjectURL(url);
  }, [content, activeFormat, activeFmt]);

  const lineCount = content ? content.split("\n").length : 0;

  return (
    <div className="panel__body panel__body--wide">
      <h2 className="panel__title">Export Architecture</h2>
      <p className="panel__lede">
        Thirteen formats off one spec. The infrastructure formats carry the safe defaults, so
        encryption, versioning and public-access blocks are already in the generated code.
      </p>

      {GROUPS.map((group) => (
        <div key={group} style={{ marginBottom: "var(--space-5)" }}>
          <p className="section-label" style={{ marginBottom: "var(--space-2)" }}>{group}</p>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))",
              gap: "var(--space-2)",
            }}
          >
            {FORMATS.filter((f) => f.group === group).map((fmt) => (
              <button
                key={fmt.key}
                className="list-btn"
                onClick={() => runExport(fmt.key)}
                disabled={loading}
                aria-pressed={activeFormat === fmt.key}
                style={{
                  marginBottom: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-2)",
                  borderColor: activeFormat === fmt.key ? "var(--accent)" : undefined,
                  background: activeFormat === fmt.key ? "var(--accent-soft)" : undefined,
                }}
              >
                <FormatTag format={fmt} />
                <span style={{ minWidth: 0 }}>
                  <span style={{ display: "block", fontSize: "var(--text-base)", fontWeight: 600 }}>
                    {fmt.label}
                  </span>
                  <span style={{ display: "block", fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>
                    {fmt.desc}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}

      {loading && (
        <div className="status-row">
          <span className="spinner" />
          Generating {activeFmt?.label || activeFormat}...
        </div>
      )}

      {error && <div className="callout callout--danger">{error}</div>}

      {content && !loading && (
        <div className="card">
          <div className="card__header">
            <span style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", minWidth: 0 }}>
              <FormatTag format={activeFmt} />
              <code className="inline">architecture.{activeFmt?.ext || "txt"}</code>
              <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>
                {lineCount} lines
              </span>
            </span>
            <span style={{ display: "flex", gap: "var(--space-2)" }}>
              <button className="btn btn--sm" onClick={handleCopy}>
                <Icon name={copied ? "check" : "copy"} size={13} />
                {copied ? "Copied" : "Copy"}
              </button>
              <button className="btn btn--sm" onClick={handleDownload}>
                <Icon name="download" size={13} />
                Download
              </button>
            </span>
          </div>
          <div style={{ maxHeight: "60vh", overflow: "auto" }}>
            <pre ref={preRef} className="code-block">
              {content}
            </pre>
          </div>
        </div>
      )}

      {!content && !loading && !error && (
        <EmptyState
          icon="download"
          title="No format generated yet."
          hint="Pick a format above. The output appears here, ready to copy or download."
        />
      )}
    </div>
  );
}
