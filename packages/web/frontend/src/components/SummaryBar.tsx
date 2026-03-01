import React from 'react';

interface SummaryBarProps {
  spec: any | null;
  onDownloadTerraform?: () => void;
  onDownloadYaml?: () => void;
  validationSummary?: { passed: number; total: number } | null;
}

export default function SummaryBar({ spec, onDownloadTerraform, onDownloadYaml, validationSummary }: SummaryBarProps) {
  if (!spec) return null;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.5rem 1rem',
                  background: '#ffffff', borderRadius: '0.375rem', marginBottom: '0.5rem', fontSize: '0.875rem',
                  borderBottom: '1px solid #e2e8f0' }}>
      <span style={{ color: '#64748b' }}>Components: <strong style={{ color: '#334155' }}>{spec.components?.length || 0}</strong></span>
      {spec.cost_estimate && (
        <span style={{ color: '#64748b' }}>Est. <strong style={{ color: '#2563eb' }}>${spec.cost_estimate.monthly_total?.toFixed(0)}/mo</strong></span>
      )}
      <span style={{ color: '#64748b' }}>{(spec.provider || 'aws').toUpperCase()} / {spec.region || 'us-east-1'}</span>
      {validationSummary && (
        <span style={{
          padding: '0.125rem 0.5rem',
          borderRadius: '0.25rem',
          fontSize: '0.75rem',
          fontWeight: 600,
          background: validationSummary.passed === validationSummary.total ? '#d1fae5' : '#fee2e2',
          color: validationSummary.passed === validationSummary.total ? '#065f46' : '#991b1b',
        }}>
          WA: {validationSummary.passed}/{validationSummary.total}
        </span>
      )}
      <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
        {onDownloadTerraform && (
          <button onClick={onDownloadTerraform} style={{ padding: '0.25rem 0.75rem', background: '#2563eb', color: 'white', border: 'none', borderRadius: '0.25rem', cursor: 'pointer', fontSize: '0.75rem' }}>
            Download Terraform
          </button>
        )}
        {onDownloadYaml && (
          <button onClick={onDownloadYaml} style={{ padding: '0.25rem 0.75rem', background: '#f8fafc', color: '#475569', border: '1px solid #e2e8f0', borderRadius: '0.25rem', cursor: 'pointer', fontSize: '0.75rem' }}>
            Download YAML
          </button>
        )}
      </div>
    </div>
  );
}
