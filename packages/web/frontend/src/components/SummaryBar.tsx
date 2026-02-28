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
                  background: '#1e293b', borderRadius: '0.375rem', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
      <span style={{ color: '#94a3b8' }}>Components: <strong style={{ color: '#f8fafc' }}>{spec.components?.length || 0}</strong></span>
      {spec.cost_estimate && (
        <span style={{ color: '#94a3b8' }}>Est. <strong style={{ color: '#10b981' }}>${spec.cost_estimate.monthly_total?.toFixed(0)}/mo</strong></span>
      )}
      <span style={{ color: '#94a3b8' }}>{(spec.provider || 'aws').toUpperCase()} / {spec.region || 'us-east-1'}</span>
      {validationSummary && (
        <span style={{
          padding: '0.125rem 0.5rem',
          borderRadius: '0.25rem',
          fontSize: '0.75rem',
          fontWeight: 600,
          background: validationSummary.passed === validationSummary.total ? '#065f46' : '#7f1d1d',
          color: validationSummary.passed === validationSummary.total ? '#6ee7b7' : '#fca5a5',
        }}>
          WA: {validationSummary.passed}/{validationSummary.total}
        </span>
      )}
      <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
        {onDownloadTerraform && (
          <button onClick={onDownloadTerraform} style={{ padding: '0.25rem 0.75rem', background: '#10b981', color: 'white', border: 'none', borderRadius: '0.25rem', cursor: 'pointer', fontSize: '0.75rem' }}>
            Download Terraform
          </button>
        )}
        {onDownloadYaml && (
          <button onClick={onDownloadYaml} style={{ padding: '0.25rem 0.75rem', background: '#334155', color: '#94a3b8', border: '1px solid #475569', borderRadius: '0.25rem', cursor: 'pointer', fontSize: '0.75rem' }}>
            Download YAML
          </button>
        )}
      </div>
    </div>
  );
}
