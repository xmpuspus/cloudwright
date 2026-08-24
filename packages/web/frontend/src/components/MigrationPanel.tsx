import React, { useCallback, useMemo, useState } from "react";
import { parseApiError } from "../lib/apiError";
import Icon from "./Icon";

type Scalar = boolean | number | string | null;

interface MigrationAction {
  source_asset_id: string;
  source_name: string;
  disposition: string;
  target_asset_ids: string[];
  owner: string;
}

interface MigrationWave {
  id: string;
  order: number;
  name: string;
  actions: MigrationAction[];
  prerequisites: string[];
  rollback_procedures: string[];
  gate_ids: string[];
}

interface Economics {
  current_monthly_cost: number;
  target_monthly_cost: number;
  monthly_delta: number;
  net_migration_cost: number;
  payback_months: number | null;
  currency: string;
}

interface CriterionResult {
  criterion_id: string;
  name: string;
  category: string;
  passed: boolean;
  blocking: boolean;
  expected: Scalar;
  actual: Scalar;
  source: string;
  detail: string;
}

interface MigrationDemoResponse {
  project: {
    name: string;
    industry: string;
    estate: { assets: unknown[] };
    target: { assets: unknown[] };
  };
  assessment: {
    domain_pack: string | null;
    transition: {
      complete: boolean;
      waves: MigrationWave[];
      warnings: string[];
      economics: Economics;
    };
    assurance: { criteria: unknown[] };
  };
  evidence_pack: {
    closed: boolean;
    passed: number;
    failed: number;
    missing: number;
    blocking_failures: number;
    results: CriterionResult[];
  };
}

interface MigrationPanelProps {
  apiBase: string;
}

function money(value: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

function displayValue(value: Scalar) {
  if (value === null) return "No observation";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export default function MigrationPanel({ apiBase }: MigrationPanelProps) {
  const [result, setResult] = useState<MigrationDemoResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runDemo = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}/migration/demo`);
      if (!response.ok) throw new Error(await parseApiError(response));
      setResult((await response.json()) as MigrationDemoResponse);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The proof project could not run.");
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  const evidenceByCategory = useMemo(() => {
    const grouped: Record<string, CriterionResult[]> = {};
    for (const item of result?.evidence_pack.results ?? []) {
      (grouped[item.category] ??= []).push(item);
    }
    return grouped;
  }, [result]);

  const economics = result?.assessment.transition.economics;
  const monthlySavings = economics ? Math.max(0, -economics.monthly_delta) : 0;

  return (
    <div className="panel__body panel__body--wide migration">
      <div className="migration__intro">
        <div>
          <p className="migration__context">Migration intelligence</p>
          <h2 className="migration__title">Order the move. Prove the outcome.</h2>
          <p className="panel__lede migration__lede">
            Turn an estate, a target and their dependencies into migration waves, costs and
            evidence gates. The engine stays industry-neutral; optional packs add domain rules.
          </p>
        </div>
        <button className="btn btn--primary migration__run" onClick={runDemo} disabled={loading}>
          {loading ? <span className="spinner" /> : <Icon name="route" size={15} />}
          {loading ? "Running proof project..." : "Run PH telco proof project"}
        </button>
      </div>

      <div className="migration__boundary">
        This view plans and checks evidence. It does not move data or change systems.
      </div>

      {error && (
        <div className="callout callout--danger migration__error">
          <span>{error}</span>
          <button className="btn btn--sm" onClick={runDemo}>Retry proof project</button>
        </div>
      )}

      {!result && !loading && !error && (
        <div className="migration__empty">
          <div>
            <span className="migration__empty-mark">1</span>
            <strong>Dependency order</strong>
            <p>Every declared dependency moves before the asset that relies on it.</p>
          </div>
          <div>
            <span className="migration__empty-mark">2</span>
            <strong>Evidence contract</strong>
            <p>Missing or failed blocking observations keep the migration open.</p>
          </div>
          <div>
            <span className="migration__empty-mark">3</span>
            <strong>Explicit economics</strong>
            <p>One-time, dual-run and recurring costs come from supplied values.</p>
          </div>
        </div>
      )}

      {result && economics && (
        <>
          <section
            className={`migration__outcome ${result.evidence_pack.closed ? "migration__outcome--closed" : "migration__outcome--blocked"}`}
            role="status"
            aria-live="polite"
          >
            <div>
              <span className="migration__proof">PH telecommunications proof project</span>
              <h3>{result.evidence_pack.closed ? "Ready to close" : "Blocked"}</h3>
              <p>{result.project.name}</p>
            </div>
            <div className="migration__outcome-counts" aria-label="Migration result counts">
              <span><strong>{result.evidence_pack.passed}</strong> passed</span>
              <span><strong>{result.evidence_pack.missing}</strong> missing</span>
              <span><strong>{result.evidence_pack.blocking_failures}</strong> blocking</span>
            </div>
          </section>

          <section className="migration__metrics" aria-label="Migration summary">
            <div><strong>{result.project.estate.assets.length}</strong><span>Source assets</span></div>
            <div><strong>{result.project.target.assets.length}</strong><span>Target assets</span></div>
            <div><strong>{result.assessment.transition.waves.length}</strong><span>Ordered waves</span></div>
            <div><strong>{result.assessment.assurance.criteria.length}</strong><span>Evidence gates</span></div>
          </section>

          <section className="migration__economics" aria-label="Migration economics">
            <div><span>Current run cost</span><strong>{money(economics.current_monthly_cost, economics.currency)}</strong><small>per month</small></div>
            <div><span>Target run cost</span><strong>{money(economics.target_monthly_cost, economics.currency)}</strong><small>per month</small></div>
            <div className="migration__economics-highlight"><span>Monthly savings</span><strong>{money(monthlySavings, economics.currency)}</strong><small>from supplied costs</small></div>
            <div><span>Net migration cost</span><strong>{money(economics.net_migration_cost, economics.currency)}</strong><small>{economics.payback_months === null ? "No payback calculated" : `${economics.payback_months} month payback`}</small></div>
          </section>

          <div className="migration__workbench">
            <section className="migration__route" aria-labelledby="migration-route-title">
              <div className="migration__section-head">
                <div>
                  <p className="migration__context">Dependency route</p>
                  <h3 id="migration-route-title">What moves first</h3>
                </div>
                <span>{result.assessment.transition.waves.length} waves</span>
              </div>
              <div className="migration__route-list">
                {result.assessment.transition.waves.map((wave, index) => (
                  <article className="migration-wave" key={wave.id}>
                    <div className="migration-wave__rail" aria-hidden="true">
                      <span>{wave.order}</span>
                      {index < result.assessment.transition.waves.length - 1 && <i />}
                    </div>
                    <div className="migration-wave__card">
                      <div className="migration-wave__head">
                        <h4>{wave.name}</h4>
                        <span>{wave.gate_ids.length} {wave.gate_ids.length === 1 ? "gate" : "gates"}</span>
                      </div>
                      <div className="migration-wave__actions">
                        {wave.actions.map((action) => (
                          <div key={action.source_asset_id}>
                            <span className="migration-wave__disposition">{action.disposition}</span>
                            <strong>{action.source_name}</strong>
                            <small>{action.target_asset_ids.length ? action.target_asset_ids.join(", ") : "No target"}</small>
                          </div>
                        ))}
                      </div>
                      <p className="migration-wave__meta">
                        {wave.prerequisites.length ? `Needs ${wave.prerequisites.join(", ")}` : "No earlier migration prerequisite"}
                        <span>{wave.rollback_procedures.length} rollback {wave.rollback_procedures.length === 1 ? "path" : "paths"}</span>
                      </p>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="migration__evidence" aria-labelledby="migration-evidence-title">
              <div className="migration__section-head">
                <div>
                  <p className="migration__context">Acceptance contract</p>
                  <h3 id="migration-evidence-title">Why it can close</h3>
                </div>
                <span>{result.evidence_pack.passed}/{result.evidence_pack.results.length} passed</span>
              </div>
              <div className="migration__evidence-groups">
                {Object.entries(evidenceByCategory).map(([category, items]) => (
                  <section className="migration-evidence-group" key={category}>
                    <div className="migration-evidence-group__head">
                      <h4>{category}</h4>
                      <span>{items.filter((item) => item.passed).length}/{items.length}</span>
                    </div>
                    {items.map((item) => {
                      const status = item.passed ? "Passed" : item.actual === null ? "Missing" : "Failed";
                      return (
                        <div className="migration-evidence-row" key={item.criterion_id}>
                          <span className={`migration-evidence-row__mark migration-evidence-row__mark--${status.toLowerCase()}`} aria-label={status}>
                            {item.passed ? <Icon name="check" size={12} /> : <Icon name="cross" size={12} />}
                          </span>
                          <div>
                            <strong>{item.name}</strong>
                            <small>Observed {displayValue(item.actual)} · Required {displayValue(item.expected)}</small>
                          </div>
                        </div>
                      );
                    })}
                  </section>
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
