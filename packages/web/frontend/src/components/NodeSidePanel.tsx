import React from 'react';
import { getCategoryColor, getServiceCategory, getCategoryIconPath } from '../lib/icons';

interface ComponentData {
  id: string;
  label: string;
  service: string;
  provider: string;
  description?: string;
  tier: number;
  config?: Record<string, unknown>;
}

interface CostBreakdownItem {
  component_id: string;
  service: string;
  monthly: number;
  notes?: string;
}

interface NodeSidePanelProps {
  component: ComponentData | null;
  cost?: CostBreakdownItem | null;
  onClose: () => void;
}

const TIER_LABELS: Record<number, string> = {
  0: 'Edge',
  1: 'Ingress',
  2: 'Compute',
  3: 'Data',
  4: 'Storage',
};

const CONFIG_LABELS: Record<string, string> = {
  instance_type: 'Instance Type',
  engine: 'Engine',
  multi_az: 'Multi-AZ',
  count: 'Count',
  encryption: 'Encryption',
};

function formatConfigValue(value: unknown): string {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (value === null || value === undefined) return '—';
  return String(value);
}

const divider = { borderTop: '1px solid #e2e8f0', margin: '12px 0' };

const sectionLabel: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  color: '#64748b',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginBottom: 8,
};

const rowStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 6,
};

const keyStyle: React.CSSProperties = { color: '#64748b', fontSize: 13 };
const valStyle: React.CSSProperties = { color: '#0f172a', fontSize: 13, fontWeight: 500 };

export default function NodeSidePanel({ component, cost, onClose }: NodeSidePanelProps) {
  const visible = component !== null;

  const category = component ? getServiceCategory(component.service) : 'compute';
  const color = getCategoryColor(category);
  const iconPath = getCategoryIconPath(category);

  const configEntries = component?.config
    ? Object.entries(component.config).filter(([, v]) => v !== null && v !== undefined)
    : [];

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        right: 0,
        width: 320,
        height: '100%',
        background: '#ffffff',
        borderLeft: '1px solid #e2e8f0',
        transform: visible ? 'translateX(0)' : 'translateX(100%)',
        transition: 'transform 0.2s ease',
        zIndex: 20,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        boxShadow: '-2px 0 8px rgba(0,0,0,0.06)',
      }}
    >
      {/* Header */}
      <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid #e2e8f0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: color + '22',
              border: `1.5px solid ${color}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <svg
              width={20}
              height={20}
              viewBox="0 0 24 24"
              fill="none"
              stroke={color}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ display: 'block' }}
            >
              <path d={iconPath} />
            </svg>
          </div>
          <span
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: '#0f172a',
              flex: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {component?.label}
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              fontSize: 18,
              lineHeight: 1,
              padding: '2px 4px',
              flexShrink: 0,
            }}
            aria-label="Close panel"
          >
            ×
          </button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            style={{
              background: '#f1f5f9',
              color: '#475569',
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 600,
              padding: '2px 8px',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            {component?.provider}
          </span>
          <span style={{ color: '#64748b', fontSize: 12 }}>{component?.service}</span>
        </div>
      </div>

      {/* Scrollable body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px' }}>

        {/* Overview */}
        <div style={sectionLabel as React.CSSProperties}>Overview</div>
        {component?.description && (
          <p style={{ color: '#475569', fontSize: 13, marginBottom: 10, lineHeight: 1.5 }}>
            {component.description}
          </p>
        )}
        <div style={rowStyle}>
          <span style={keyStyle}>Tier</span>
          <span style={valStyle}>{TIER_LABELS[component?.tier ?? 2] ?? `Tier ${component?.tier}`}</span>
        </div>
        <div style={rowStyle}>
          <span style={keyStyle}>Service</span>
          <span style={valStyle}>{component?.service}</span>
        </div>
        <div style={rowStyle}>
          <span style={keyStyle}>Provider</span>
          <span style={valStyle}>{component?.provider?.toUpperCase()}</span>
        </div>

        <div style={divider} />

        {/* Cost */}
        <div style={sectionLabel as React.CSSProperties}>Cost</div>
        {cost ? (
          <>
            <div style={rowStyle}>
              <span style={keyStyle}>Monthly</span>
              <span style={{ ...valStyle, color: '#2563eb' }}>
                ${cost.monthly.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            {cost.notes && (
              <p style={{ color: '#64748b', fontSize: 12, marginTop: 4 }}>{cost.notes}</p>
            )}
          </>
        ) : (
          <p style={{ color: '#94a3b8', fontSize: 13 }}>No cost data</p>
        )}

        <div style={divider} />

        {/* Configuration */}
        <div style={sectionLabel as React.CSSProperties}>Configuration</div>
        {configEntries.length > 0 ? (
          configEntries.map(([key, value]) => (
            <div key={key} style={rowStyle}>
              <span style={keyStyle}>{CONFIG_LABELS[key] ?? key.replace(/_/g, ' ')}</span>
              <span style={valStyle}>{formatConfigValue(value)}</span>
            </div>
          ))
        ) : (
          <p style={{ color: '#94a3b8', fontSize: 13 }}>No configuration</p>
        )}

        <div style={divider} />

        {/* Connections */}
        <div style={sectionLabel as React.CSSProperties}>Connections</div>
        <p style={{ color: '#94a3b8', fontSize: 13 }}>See diagram for connections</p>
      </div>
    </div>
  );
}
