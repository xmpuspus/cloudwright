# Cloudwright Fix Plan

Full prioritized fix list from strategic analysis (2026-02-28).
Reference this file when executing fixes — every item has exact file paths,
root causes, and done definitions.

---

## P0 — Fix before anyone sees this

### P0.1: Cost engine accuracy (formula.py, cost.py, architect.py)

Root cause: 3-tier pricing cascade fails systematically.
- Tier 1 (catalog DB): Only fires when instance_type/instance_class is in
  component config. LLM often omits these, so Tier 1 returns None.
- Tier 2 (formula dispatch): per_hour returns None when no price_per_hour
  or base_rate available. Many services have no formula entry.
- Tier 3 (static fallback): _FALLBACK_PRICES in formula.py:108-216 has
  absolute minimums. EC2 not even listed (defaults to $10). EKS $73
  (control plane only). RDS $50 (db.t3.micro).

Files to change:
- packages/core/cloudwright/catalog/formula.py
  - Replace _FALLBACK_PRICES with realistic "default medium production" prices:
    - EC2: $150 (m5.large equivalent)
    - ECS/EKS/GKE/AKS: $400 (control plane + 3 worker nodes)
    - Fargate: $120
    - Cloud Run/Container Apps: $50
    - RDS/Aurora: $200 (db.r5.large equivalent)
    - Cloud SQL/Azure SQL: $180
    - ElastiCache/Memorystore/Azure Cache: $180 (cache.r5.large)
    - DynamoDB: $75
    - Cosmos DB: $100
    - Firestore: $40
    - S3/Cloud Storage/Blob Storage: $10 (100GB + requests)
    - CloudFront/Cloud CDN/Azure CDN: $85 (1TB transfer)
    - ALB/NLB: $25 (roughly correct already)
    - SQS: $10
    - SNS: $5
    - Kinesis: $50
    - Redshift: $500 (dc2.large 2-node)
    - BigQuery: $25
    - Synapse: $500
    - SageMaker/Vertex AI/Azure ML: $200
    - Lambda/Cloud Functions/Azure Functions: $15
    - WAF/Cloud Armor/Azure WAF: $15
    - API Gateway: $15
    - NAT Gateway: $35
    - MSK: $250
    - App Service: $55
    - App Engine: $60
    - Keep all $0 services as-is (users, internet, iam, vpc, etc.)
  - In default_managed_price: already handles count and storage_gb — just
    fixing base prices flows through

- packages/core/cloudwright/cost.py
  - In _price_component (line 167-194): After getting monthly price from
    any tier, apply these multipliers:
    - If config.get("multi_az") is True: multiply by 2.0 (standby instance)
    - If service is in container orchestration set (eks, gke, aks, ecs) and
      config doesn't have "count" or "node_count": multiply by 3 (default
      3-node cluster, since the fallback already handles explicit counts)
  - These multipliers should apply AFTER the 3-tier resolution, before return

- packages/core/cloudwright/architect.py
  - In _DESIGN_SYSTEM prompt (line 105-176): Add to the RULES section:
    "- ALWAYS include instance_type on EC2/compute_engine/virtual_machines
    (e.g. m5.large, n2-standard-4, Standard_D4s_v3)
    - ALWAYS include instance_class on RDS/Aurora/Cloud SQL/Azure SQL
    (e.g. db.r5.large, db-n1-standard-4)
    - ALWAYS include node_type on ElastiCache/Memorystore
    (e.g. cache.r5.large)
    - Include storage_gb on all database and storage components
    - Include count on compute components when multiple instances needed"

- packages/core/tests/test_cost.py
  - Add regression test: build a known 3-tier web app ArchSpec manually
    (ALB + 2x EC2 m5.large + RDS db.r5.large multi-AZ + ElastiCache +
    S3 + CloudFront). Assert total estimate is between $800 and $3000/mo.
  - Add test: component with multi_az=True costs more than without.
  - Add test: EKS with no explicit node_count gets 3x multiplier.

Done: Cost estimate for a healthcare EHR architecture is >$1000/mo, not $182.
Effort: M (2-3 days)

### P0.2: CloudFormation plaintext password (cloudformation.py)

File: packages/core/cloudwright/exporter/cloudformation.py
- Find MasterUserPassword: "changeme" in _build_properties
- Replace with: add a Parameters section to the template with a NoEcho
  parameter "DBPassword", then use !Ref DBPassword in the RDS resource
- Find "arn:aws:iam::ACCOUNT_ID:role/lambda-role" and similar
- Replace ACCOUNT_ID with !Sub "arn:aws:iam::${AWS::AccountId}:role/..."
- Update test_exporter.py to assert no "changeme" in CFN output

Done: No plaintext passwords or literal "ACCOUNT_ID" in generated CFN.
Effort: S (1-2 hours)

### P0.3: Terraform export quality (terraform.py)

File: packages/core/cloudwright/exporter/terraform.py
Fixes:
- Replace hardcoded AMI "ami-0c55b159cbfafe1f0" with:
  data "aws_ssm_parameter" "amazon_linux" {
    name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
  }
  Then reference data.aws_ssm_parameter.amazon_linux.value
- Replace "123456789012" with data.aws_caller_identity.current.account_id
  Add: data "aws_caller_identity" "current" {}
- Add data sources for default VPC and subnets:
  data "aws_vpc" "default" { default = true }
  data "aws_subnets" "default" { filter { name = "vpc-id"; values = [data.aws_vpc.default.id] } }
- Fix Azure Functions: generate azurerm_storage_account and
  azurerm_service_plan resources alongside the function app
- Fix EBS availability_zone: use data.aws_availability_zones.available.names[0]
  Add: data "aws_availability_zones" "available" { state = "available" }
- Replace codepipeline comment with actual aws_codepipeline resource
- Pin provider versions: aws = "= 5.82.2", google = "= 6.14.1",
  azurerm = "= 4.14.0"
- Fix CloudFront origin: use a variable instead of "origin.example.com"
- Add var.trail_bucket variable block for CloudTrail

Update test_exporter.py:
- Assert no "ami-0c55b159" in terraform output
- Assert no "123456789012" in terraform output
- Assert "data.aws_caller_identity" present when Lambda/EKS used

Done: Generated Terraform passes terraform validate (when providers init'd).
Effort: L (3-5 days)

### P0.4: Pipeline failures for import/migration/comparison (architect.py)

Root cause: _DESIGN_SYSTEM only describes greenfield. No instructions for
import/migrate/compare. Greedy JSON regex. No retry. max_tokens=4000.

File: packages/core/cloudwright/architect.py
Fixes:
- Add use-case routing in design() method:
  - Detect keywords in description: "import", "terraform state",
    "cloudformation template", "migrate", "re-architect", "modernize",
    "compare", "versus", "vs", "TCO"
  - Route to appropriate system prompt variant
- Add _IMPORT_SYSTEM prompt: instructs LLM to parse infrastructure
  descriptions/state into ArchSpec JSON. Emphasize mapping existing
  resources to service keys, preserving topology.
- Add _MIGRATION_SYSTEM prompt: instructs LLM to design target
  architecture given source architecture constraints. Include
  service equivalence guidance.
- Add _COMPARISON_SYSTEM prompt: instructs LLM to generate a single
  representative architecture that can be compared across providers.
- Replace _extract_json greedy regex r"\{[\s\S]*\}" with a proper
  brace-counting parser:
  - Find first '{', count depth, find matching '}'
  - Handle nested braces, string literals with escaped braces
- Add retry logic in design():
  - On ValueError from _extract_json or json.JSONDecodeError:
    retry once with appended instruction "You must respond with ONLY
    a valid JSON object. No markdown, no explanation."
  - Log first failure for debugging
- Increase max_tokens: 8000 for complex cases (description length >200
  chars or contains import/migration keywords), keep 4000 for simple
- Add tests:
  - test_architect_chat.py: test use-case routing detects keywords
  - test_architect_chat.py: test _extract_json with nested braces,
    markdown-wrapped JSON, explanation text around JSON
  - test_architect_chat.py: test retry behavior (mock LLM to fail
    first call, succeed second)

Done: Pipeline failure rate <5% (from 20%). Import/migration/comparison
use cases produce valid specs.
Effort: M (2-3 days)

### P0.5: Drift detection ID mismatch (differ.py, importers)

Root cause: Design specs use user-authored IDs ("primary_db"), importers
generate IDs from service keys ("rds"). Differ matches on ID.

File: packages/core/cloudwright/differ.py
- In Differ.diff(), after ID-based matching, add service-based fallback:
  - For unmatched old components (in old_map but not new_map) and
    unmatched new components (in new_map but not old_map):
  - Try to match by (service, provider) tuple
  - If exactly one old matches one new by service+provider, treat as
    a "renamed" component and generate changes instead of add+remove
  - If multiple match, leave as add/remove (ambiguous)
- Add test in test_differ.py: two specs with different IDs but same
  service/provider/config should show as changed (or renamed), not
  as removed+added

File: packages/core/cloudwright/importer/terraform_state.py
File: packages/core/cloudwright/importer/cloudformation.py
- Both: add optional parameter design_spec: ArchSpec | None = None
- When provided, try to match imported components to design spec
  component IDs by service+provider. Use design spec ID if matched.
- Update import_spec() in importer/__init__.py to accept and pass through

Done: Drift detection between a design spec and its imported deployment
shows actual config drift, not 100% false positives from ID mismatch.
Effort: M (2-3 days)

---

## P1 — Next 30 days (drives adoption)

### P1.1: Register D2 exporter

File: packages/core/cloudwright/exporter/__init__.py
- Add "d2" to FORMATS tuple
- Add elif fmt == "d2": dispatch to d2.render(spec)
- Update test_exporter.py: add test for d2 format

Done: cloudwright export spec.yaml --format d2 works.
Effort: S (30 min)

### P1.2: Fix AIBOM provider detection

File: packages/core/cloudwright/exporter/aibom.py
- Replace: from cloudwright.llm.anthropic import GENERATE_MODEL
- With: detect active provider and import the correct model name.
  Try: from cloudwright.llm import get_llm; model = get_llm().model_name
  Or add a get_model_name() function to the LLM abstraction.
- Update test to verify AIBOM model name matches configured provider

Done: AIBOM output cites the correct LLM model regardless of provider.
Effort: S (1 hour)

### P1.3: Wire all backend endpoints to web frontend

File: packages/web/frontend/src/App.tsx
- Add tabs/panels for: Validate, Export, Diff, Modify
- Validate tab: call POST /api/validate with current spec + framework selector
- Export tab: call POST /api/export with format selector, display result
- Diff tab: upload two specs, call POST /api/diff, display result
- Modify tab: text input for modification instruction, call POST /api/modify

File: packages/web/backend/app.py
- Fix /api/chat endpoint: thread conversation history from ChatRequest.history
  into the ConversationSession, not just architect.design(req.message)

Done: All CLI features accessible through web UI. Chat maintains context.
Effort: M (3-4 days)

### P1.4: Cost accuracy regression tests

File: packages/core/tests/test_cost.py
- Add TestCostAccuracy class with:
  - test_three_tier_web_app: ALB + 2x EC2 + RDS multi-AZ + S3 -> $800-3000
  - test_kubernetes_cluster: EKS + 3 nodes + RDS + ElastiCache -> $500-2500
  - test_serverless_api: API GW + Lambda + DynamoDB + S3 -> $50-500
  - test_data_pipeline: Kinesis + Lambda + S3 + Redshift -> $400-2000
  - test_multi_az_doubles_db_cost: same spec with/without multi_az,
    multi_az version should be 1.5-2.5x more expensive
- These tests prevent future regressions in cost accuracy

Done: Cost regression tests pass and catch >3x deviations.
Effort: S (1 day)

### P1.5: Pin all dependencies

Files:
- packages/core/pyproject.toml
- packages/cli/pyproject.toml
- packages/web/pyproject.toml
- Change all >= ranges to == pins
- Example: pydantic>=2.6.0,<3 -> pydantic==2.10.4 (or current installed)
- Run: pip freeze | grep <package> to get exact installed versions

Done: All deps use == pinning. No >= or ~> anywhere.
Effort: S (1 hour)

### P1.6: Fix scorer silent failure

File: packages/core/cloudwright/scorer.py
- Find the bare except Exception in the compliance dimension
- Replace with: except (ValueError, KeyError) as e:
- Add: details.append(f"Compliance validation error: {e}")
- Log: log.warning("Compliance scoring failed: %s", e)
- Don't swallow the error — let users see what went wrong

Done: Scorer surfaces compliance validation errors in score notes.
Effort: S (30 min)

### P1.7: Fix policy budget passthrough

File: packages/core/cloudwright/policy.py
- In _check_budget_monthly: when cost_estimate is None, return
  PolicyCheckResult(passed=False, message="No cost estimate available.
  Run cloudwright cost first.", severity=rule.severity)
- Add test in test_policy.py

Done: Budget policy fails explicitly when cost not computed.
Effort: S (30 min)

### P1.8: PDF compliance report export

File: packages/core/cloudwright/exporter/compliance_report.py
- Add render_pdf(spec, validation, output_path) function
- Use markdown2 + weasyprint (or reportlab if simpler)
- Convert existing markdown output to PDF with proper formatting
- Add weasyprint to optional deps: cloudwright[pdf]
- Add CLI flag: cloudwright validate spec.yaml --compliance hipaa --pdf report.pdf
- Update packages/cli/cloudwright_cli/commands/validate.py for --pdf flag

Done: cloudwright validate --pdf produces a professional PDF report.
Effort: M (2 days)

---

## P2 — Next 90 days (builds moat)

### P2.1: Deep compliance validation

Files: packages/core/cloudwright/validator.py
- Add NIST 800-53 control mapping for FedRAMP checks (AC-*, AU-*, CM-*, etc.)
- Add PCI DSS v4.0 sub-requirement mapping (1.1, 1.2, 2.1, etc.)
- Grow from 35 checks to 100+ across 6 frameworks
- Add control_id field to ValidationCheck model (spec.py)
- Add control mapping output in compliance report

Done: Each check maps to specific regulatory control IDs.
Effort: L (2-3 weeks)

### P2.2: Real-time cost estimation with catalog pricing

Files: packages/core/cloudwright/catalog/store.py, catalog/*.json
- Expand managed_services table with RDS instance classes, ElastiCache
  node types, EKS node group pricing
- Add pricing fetcher script: catalog/fetch_pricing.py that queries
  AWS Bulk Pricing API, GCP Cloud Billing Catalog, Azure Retail Prices
- Wire to cloudwright refresh CLI command
- Goal: Tier 1 catalog lookup hits for 80%+ of common services

Done: Cost accuracy >80% for standard architectures.
Effort: L (2-3 weeks)

### P2.3: Infracost integration

File: packages/core/cloudwright/integrations/infracost.py (new)
- After terraform export, optionally shell out to infracost breakdown
- Parse Infracost JSON output
- Display side-by-side: Cloudwright estimate vs Infracost estimate
- Add CLI flag: cloudwright cost spec.yaml --verify-with-infracost
- Graceful degradation when infracost not installed

Done: Users can cross-validate design-time estimates with code-time estimates.
Effort: M (3-4 days)

### P2.4: Visual architecture editor

File: packages/web/frontend/src/ArchitectureDiagram.tsx
- Extend ReactFlow to support drag-and-drop from component palette
- Add component palette sidebar organized by tier and provider
- Bi-directional sync: diagram changes -> ArchSpec YAML -> diagram
- Add connection drawing by dragging between nodes
- Add component config panel (click node -> edit config)

Done: Users can visually design architectures in the browser.
Effort: XL (4-6 weeks)

### P2.5: GitOps / PR integration

File: .github/actions/cloudwright-review/action.yml (new)
- GitHub Action that runs on PRs modifying .tf files
- Runs: cloudwright import -> validate -> lint -> score
- Posts results as PR comment with pass/fail badges
- Compares score to main branch baseline

Done: Cloudwright validates architecture on every PR.
Effort: M (3-4 days)

### P2.6: Live infrastructure import

File: packages/core/cloudwright/importer/live_aws.py (new)
File: packages/core/cloudwright/importer/live_gcp.py (new)
File: packages/core/cloudwright/importer/live_azure.py (new)
- AWS: boto3 describe_instances, describe_db_instances, etc.
- GCP: google-cloud-compute, google-cloud-sql, etc.
- Azure: azure-mgmt-compute, azure-mgmt-sql, etc.
- CLI: cloudwright import --live --provider aws --region us-east-1
- Map live resources to ArchSpec components with real configs

Done: Import running infrastructure without needing state files.
Effort: L (2-3 weeks)

### P2.7: Architecture templates marketplace

Directory: catalog/templates/ (expand existing)
- 20-30 production-ready templates:
  - hipaa-web-app, pci-payment-service, serverless-api, data-lake,
    ml-training-pipeline, multi-region-active-active, event-driven,
    microservices-platform, static-website, real-time-analytics,
    iot-ingestion, multi-tenant-saas, disaster-recovery,
    ci-cd-pipeline, monitoring-stack
- Each template: ArchSpec YAML + pre-computed cost + compliance report
- CLI: cloudwright init --template hipaa-web-app
- Community contribution guide

Done: Users start from battle-tested templates instead of blank prompts.
Effort: L (2 weeks content + M framework)
