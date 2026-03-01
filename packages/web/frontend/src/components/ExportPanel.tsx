import React, { useState, useCallback, useRef } from "react";

interface ExportPanelProps {
  spec: Record<string, unknown>;
  apiBase: string;
}

const FORMATS = [
  { key: "terraform", label: "Terraform", ext: "tf", lang: "hcl", desc: "HashiCorp Configuration Language" },
  { key: "cloudformation", label: "CloudFormation", ext: "yaml", lang: "yaml", desc: "AWS CloudFormation template" },
  { key: "mermaid", label: "Mermaid", ext: "mmd", lang: "mermaid", desc: "Mermaid diagram markup" },
  { key: "d2", label: "D2", ext: "d2", lang: "d2", desc: "D2 diagram language" },
  { key: "sbom", label: "SBOM", ext: "json", lang: "json", desc: "CycloneDX Software BOM" },
  { key: "aibom", label: "AIBOM", ext: "json", lang: "json", desc: "OWASP AI Bill of Materials" },
];

function FormatIcon({ format }: { format: string }) {
  const icons: Record<string, string> = {
    terraform: "HCL",
    cloudformation: "CFN",
    mermaid: "MMD",
    d2: "D2",
    sbom: "BOM",
    aibom: "AI",
  };
  const colors: Record<string, string> = {
    terraform: "#7c3aed",
    cloudformation: "#ea580c",
    mermaid: "#0891b2",
    d2: "#4f46e5",
    sbom: "#059669",
    aibom: "#2563eb",
  };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 32,
        height: 20,
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 700,
        background: `${colors[format] || "#64748b"}14`,
        color: colors[format] || "#64748b",
        letterSpacing: "0.02em",
        flexShrink: 0,
      }}
    >
      {icons[format] || format.slice(0, 3).toUpperCase()}
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
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Export failed");
        setContent(data.content || JSON.stringify(data, null, 2));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Export failed");
        setContent("");
      } finally {
        setLoading(false);
      }
    },
    [spec, apiBase]
  );

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const el = preRef.current;
      if (el) {
        const range = document.createRange();
        range.selectNodeContents(el);
        window.getSelection()?.removeAllRanges();
        window.getSelection()?.addRange(range);
      }
    }
  }, [content]);

  const handleDownload = useCallback(() => {
    if (!content || !activeFormat) return;
    const fmt = FORMATS.find((f) => f.key === activeFormat);
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `architecture.${fmt?.ext || "txt"}`;
    a.click();
    URL.revokeObjectURL(url);
  }, [content, activeFormat]);

  const lineCount = content ? content.split("\n").length : 0;
  const activeFmt = FORMATS.find((f) => f.key === activeFormat);

  return (
    <div style={{ padding: 32, maxWidth: 960 }}>
      <h2 style={{ fontSize: 18, marginBottom: 16, color: "#0f172a", fontWeight: 700 }}>
        Export Architecture
      </h2>

      {/* Format grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 10,
          marginBottom: 24,
        }}
      >
        {FORMATS.map((fmt) => {
          const isActive = activeFormat === fmt.key;
          return (
            <button
              key={fmt.key}
              onClick={() => runExport(fmt.key)}
              disabled={loading}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 14px",
                borderRadius: 8,
                border: isActive ? "1.5px solid #2563eb" : "1px solid #e2e8f0",
                background: isActive ? "#eff6ff" : "#ffffff",
                cursor: loading ? "wait" : "pointer",
                textAlign: "left",
                transition: "all 0.15s ease",
                opacity: loading && !isActive ? 0.6 : 1,
              }}
            >
              <FormatIcon format={fmt.key} />
              <div>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: isActive ? 600 : 500,
                    color: isActive ? "#1d4ed8" : "#0f172a",
                  }}
                >
                  {fmt.label}
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8" }}>{fmt.desc}</div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Loading */}
      {loading && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: 24,
            color: "#64748b",
            fontSize: 14,
          }}
        >
          <span
            style={{
              display: "inline-block",
              width: 16,
              height: 16,
              border: "2px solid #e2e8f0",
              borderTopColor: "#2563eb",
              borderRadius: "50%",
              animation: "spin 0.6s linear infinite",
            }}
          />
          Generating {activeFmt?.label || activeFormat}...
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Error */}
      {error && (
        <div
          style={{
            padding: "12px 16px",
            background: "#fef2f2",
            border: "1px solid #fca5a5",
            borderRadius: 8,
            color: "#991b1b",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      {/* Code output */}
      {content && !loading && (
        <div
          style={{
            border: "1px solid #e2e8f0",
            borderRadius: 10,
            overflow: "hidden",
          }}
        >
          {/* Toolbar */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "8px 14px",
              background: "#f8fafc",
              borderBottom: "1px solid #e2e8f0",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <FormatIcon format={activeFormat || ""} />
              <span style={{ fontSize: 12, color: "#64748b" }}>
                architecture.{activeFmt?.ext || "txt"}
              </span>
              <span style={{ fontSize: 11, color: "#cbd5e1" }}>
                {lineCount} lines
              </span>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <button
                onClick={handleCopy}
                style={{
                  padding: "4px 12px",
                  borderRadius: 4,
                  border: "1px solid #e2e8f0",
                  background: copied ? "#dcfce7" : "#ffffff",
                  color: copied ? "#166534" : "#475569",
                  cursor: "pointer",
                  fontSize: 12,
                  fontWeight: 500,
                  transition: "all 0.15s ease",
                }}
              >
                {copied ? "Copied" : "Copy"}
              </button>
              <button
                onClick={handleDownload}
                style={{
                  padding: "4px 12px",
                  borderRadius: 4,
                  border: "1px solid #e2e8f0",
                  background: "#ffffff",
                  color: "#475569",
                  cursor: "pointer",
                  fontSize: 12,
                  fontWeight: 500,
                }}
              >
                Download
              </button>
            </div>
          </div>

          {/* Code block with line numbers */}
          <div style={{ maxHeight: 560, overflow: "auto" }}>
            <pre
              ref={preRef}
              style={{
                margin: 0,
                padding: 16,
                fontSize: 12,
                lineHeight: 1.7,
                color: "#334155",
                background: "#ffffff",
                fontFamily: "'SF Mono', 'Cascadia Code', 'Fira Code', Menlo, monospace",
                counterReset: "line",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {content}
            </pre>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!content && !loading && !error && (
        <div
          style={{
            padding: 40,
            textAlign: "center",
            color: "#94a3b8",
            fontSize: 14,
            background: "#f8fafc",
            borderRadius: 8,
            border: "1px dashed #e2e8f0",
          }}
        >
          Select an export format above to generate infrastructure code.
        </div>
      )}
    </div>
  );
}
