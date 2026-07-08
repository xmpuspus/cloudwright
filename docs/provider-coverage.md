# Provider coverage: what is real, what is a guess

Cloudwright supports four providers (AWS, GCP, Azure, Databricks) with one shared
code path for cost, compliance, and export. That code path does not have equal
data behind it for every provider. This page states plainly what is backed by
real catalog pricing versus formula or fallback pricing, so a reader can judge
how much to trust a cost number before they act on it.

All counts below were queried directly from the bundled catalog
(`packages/core/cloudwright/data/catalog.db`) and from the exporter/importer
source files in this repository. They are not estimates.

## Catalog pricing data

| Provider | Instance rows (compute) | Managed-service rows | Real per-region pricing |
|---|---|---|---|
| AWS | 1174 | 281 | Yes, 4 regions (us-east, us-west, eu-west, ap-southeast) |
| GCP | 117 | 17 | Yes, same 4 regions |
| Azure | 17 | 8 | Yes, same 4 regions |
| Databricks | 0 | 0 | No catalog rows at all |

Notes:

- The catalog seeds only AWS, GCP, and Azure from JSON price files. Databricks has
  no `providers` row and no instance or managed-service rows. Every Databricks cost
  number comes from a hardcoded formula, not a price list.
- "4 regions" means the catalog carries real, provider-specific pricing rows for
  one baseline region plus three others (a US west equivalent, an EU west
  equivalent, an Asia-Pacific southeast equivalent) per provider. That is 174 real
  non-baseline pricing rows total across AWS, GCP, and Azure combined. Any region
  outside those four falls back to a static multiplier against the baseline price,
  which is an estimate, not a verified price.
- Managed services (RDS/Cloud SQL/Azure SQL, load balancers, CDNs, caches, and so
  on) have no region column in the catalog schema at all. Their pricing is always
  the baseline-region row, rescaled by the static regional multiplier for any
  non-baseline region. Only compute instance pricing (EC2/Compute Engine/Virtual
  Machines) can use a real per-region row.
- AWS's compute and managed-service row counts dwarf GCP's and Azure's. GCP and
  Azure catalog coverage is real but thin: most non-compute Azure services and a
  meaningful share of GCP services still fall through to formula pricing
  (`packages/core/cloudwright/catalog/formula.py`) because no matching catalog row
  exists for them.

## Terraform exporter service coverage

Counted as `if svc ==` / `elif svc ==` / `elif svc in (...)` dispatch branches in
each provider's exporter file:

| Provider | File | Dispatch branches |
|---|---|---|
| AWS | `exporter/terraform/aws.py` | 24 |
| GCP | `exporter/terraform/gcp.py` | 10 |
| Azure | `exporter/terraform/azure.py` | 9 |
| Databricks | `exporter/terraform/databricks.py` | 12 |

AWS has more than double the dispatch branches of GCP or Azure, meaning more
service types can be rendered as real Terraform resources rather than being
silently dropped or emitted as a generic placeholder.

## Live import coverage

Counted from `SUPPORTED_SERVICES` in each provider's live importer:

| Provider | File | Services |
|---|---|---|
| AWS | `importer/live_aws.py` | 13 (ec2, vpc, rds, s3, lambda, ecs, eks, dynamodb, alb, cloudfront, sqs, api_gateway, cloudtrail) |
| GCP | `importer/live_gcp.py` | 3 (compute_engine, cloud_storage, cloud_sql) |
| Azure | `importer/live_azure.py` | 4 (virtual_machines, blob_storage, azure_sql, aks) |
| Databricks | none | 0, no live importer exists |

`cloudwright import-live` can pull a real running AWS account into an ArchSpec
across 13 service types. For GCP and Azure it can only see a handful of core
services. For Databricks it cannot import anything at all.

## Cost basis, plainly stated

| Provider | Cost basis |
|---|---|
| AWS | Catalog-real for compute and the managed services with rows in `managed_services`. Falls to formula/fallback only for services outside catalog coverage. |
| GCP | Partially catalog-real (compute, cloud_storage, cloud_sql, and a handful of networking services). Most other managed services are formula/fallback. |
| Azure | Mostly formula/fallback. The catalog has only 17 instance rows and 8 managed-service rows, so most Azure services price through formulas, not real price data. |
| Databricks | 100% formula/fallback. No catalog rows exist for any Databricks service. |

Multi-cloud cost comparisons (`cloudwright compare`, `cloudwright cost --compare`)
now show a Confidence column per provider so a GCP or Azure total is not presented
with the same authority as an AWS total backed by real catalog pricing. A "high"
aggregate confidence means every priced line item came from a catalog row (either
an exact regional row or the baseline row); it does not mean every line item is
region-accurate. Per-line-item confidence in `cloudwright cost` distinguishes
"high" (real per-region catalog data), "medium" (real catalog data at a different
region, rescaled by a static multiplier), and "low" (formula or hardcoded
fallback, not catalog data at all).

## What this means for a cost estimate

- If your spec is AWS-only, in one of the four catalog regions, using services
  with catalog rows: the estimate is close to real published pricing.
- If your spec is AWS-only but in a region outside the four catalog regions, or
  uses a managed service (which is never region-specific in this catalog): the
  estimate uses a static regional multiplier and should be treated as directional,
  not exact.
- If your spec is GCP or Azure: expect a meaningful share of line items to be
  formula-priced, not catalog-priced. Check the per-line Confidence column before
  trusting a total.
- If your spec is Databricks: every number is a formula estimate. Treat the total
  as a rough order of magnitude only.
