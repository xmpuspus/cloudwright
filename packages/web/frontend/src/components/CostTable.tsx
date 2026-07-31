import React from "react";

interface CostEstimate {
  monthly_total: number;
  breakdown: { component_id: string; service: string; monthly: number; notes: string }[];
  currency: string;
}

function CostTable({ estimate }: { estimate: CostEstimate }) {
  const largest = estimate.breakdown.reduce((max, item) => Math.max(max, item.monthly), 0);

  return (
    <div className="panel__body">
      <h2 className="panel__title">Cost Breakdown</h2>
      <p className="panel__lede">
        Per-component monthly price from the built-in catalog, at the region on the spec. The bar
        shows each line item against the largest one.
      </p>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Component</th>
              <th scope="col">Service</th>
              <th scope="col" style={{ textAlign: "right" }}>Monthly</th>
              <th scope="col">Share</th>
              <th scope="col">Notes</th>
            </tr>
          </thead>
          <tbody>
            {estimate.breakdown.map((item) => (
              <tr key={item.component_id}>
                <td>{item.component_id}</td>
                <td>
                  <code className="inline">{item.service}</code>
                </td>
                <td className="num">${item.monthly.toFixed(2)}</td>
                <td style={{ minWidth: 110 }}>
                  <span
                    aria-hidden="true"
                    style={{
                      display: "block",
                      height: 6,
                      borderRadius: 3,
                      background: "var(--accent)",
                      opacity: 0.85,
                      width: `${largest > 0 ? Math.max(3, (item.monthly / largest) * 100) : 0}%`,
                    }}
                  />
                </td>
                <td style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>{item.notes}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={2}>Total</td>
              <td className="num" style={{ color: "var(--accent-text)" }}>
                ${estimate.monthly_total.toFixed(2)}
              </td>
              <td colSpan={2} style={{ color: "var(--text-muted)", fontWeight: 400, fontSize: "var(--text-sm)" }}>
                {estimate.currency} per month
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

export default CostTable;
