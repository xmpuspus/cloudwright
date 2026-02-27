import React from "react";

interface CostEstimate {
  monthly_total: number;
  breakdown: { component_id: string; service: string; monthly: number; notes: string }[];
  currency: string;
}

function CostTable({ estimate }: { estimate: CostEstimate }) {
  return (
    <div style={{ padding: 32 }}>
      <h2 style={{ fontSize: 18, marginBottom: 16 }}>Cost Breakdown</h2>
      <table
        style={{
          width: "100%",
          maxWidth: 700,
          borderCollapse: "collapse",
          fontSize: 14,
        }}
      >
        <thead>
          <tr style={{ borderBottom: "2px solid #334155" }}>
            <th style={{ textAlign: "left", padding: "10px 12px", color: "#94a3b8" }}>Component</th>
            <th style={{ textAlign: "left", padding: "10px 12px", color: "#94a3b8" }}>Service</th>
            <th style={{ textAlign: "right", padding: "10px 12px", color: "#94a3b8" }}>Monthly</th>
            <th style={{ textAlign: "left", padding: "10px 12px", color: "#94a3b8" }}>Notes</th>
          </tr>
        </thead>
        <tbody>
          {estimate.breakdown.map((item) => (
            <tr key={item.component_id} style={{ borderBottom: "1px solid #1e293b" }}>
              <td style={{ padding: "10px 12px" }}>{item.component_id}</td>
              <td style={{ padding: "10px 12px", color: "#94a3b8" }}>{item.service}</td>
              <td style={{ padding: "10px 12px", textAlign: "right", fontFamily: "monospace" }}>
                ${item.monthly.toFixed(2)}
              </td>
              <td style={{ padding: "10px 12px", color: "#64748b", fontSize: 12 }}>{item.notes}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr style={{ borderTop: "2px solid #334155" }}>
            <td style={{ padding: "12px", fontWeight: 700, fontSize: 15 }} colSpan={2}>
              Total
            </td>
            <td
              style={{
                padding: "12px",
                textAlign: "right",
                fontWeight: 700,
                fontSize: 15,
                fontFamily: "monospace",
                color: "#3b82f6",
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
