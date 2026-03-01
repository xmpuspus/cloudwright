import React from "react";

interface CostEstimate {
  monthly_total: number;
  breakdown: { component_id: string; service: string; monthly: number; notes: string }[];
  currency: string;
}

function CostTable({ estimate }: { estimate: CostEstimate }) {
  return (
    <div style={{ padding: 32 }}>
      <h2 style={{ fontSize: 18, marginBottom: 16, color: "#0f172a" }}>Cost Breakdown</h2>
      <table
        style={{
          width: "100%",
          maxWidth: 700,
          borderCollapse: "collapse",
          fontSize: 14,
        }}
      >
        <thead>
          <tr style={{ borderBottom: "2px solid #e2e8f0", background: "#f8fafc" }}>
            <th style={{ textAlign: "left", padding: "10px 12px", color: "#475569" }}>Component</th>
            <th style={{ textAlign: "left", padding: "10px 12px", color: "#475569" }}>Service</th>
            <th style={{ textAlign: "right", padding: "10px 12px", color: "#475569" }}>Monthly</th>
            <th style={{ textAlign: "left", padding: "10px 12px", color: "#475569" }}>Notes</th>
          </tr>
        </thead>
        <tbody>
          {estimate.breakdown.map((item) => (
            <tr key={item.component_id} style={{ borderBottom: "1px solid #f1f5f9" }}>
              <td style={{ padding: "10px 12px", color: "#0f172a" }}>{item.component_id}</td>
              <td style={{ padding: "10px 12px", color: "#475569" }}>{item.service}</td>
              <td style={{ padding: "10px 12px", textAlign: "right", fontFamily: "monospace", color: "#0f172a" }}>
                ${item.monthly.toFixed(2)}
              </td>
              <td style={{ padding: "10px 12px", color: "#64748b", fontSize: 12 }}>{item.notes}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr style={{ borderTop: "2px solid #e2e8f0", background: "#f0f9ff" }}>
            <td style={{ padding: "12px", fontWeight: 700, fontSize: 15, color: "#0f172a" }} colSpan={2}>
              Total
            </td>
            <td
              style={{
                padding: "12px",
                textAlign: "right",
                fontWeight: 700,
                fontSize: 15,
                fontFamily: "monospace",
                color: "#2563eb",
              }}
            >
              ${estimate.monthly_total.toFixed(2)}
            </td>
            <td style={{ padding: "12px", color: "#64748b", fontSize: 12 }}>
              {estimate.currency}/month
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

export default CostTable;
