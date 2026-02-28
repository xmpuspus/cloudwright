# Cloudwright Competitor Landscape Analysis

Date: 2026-02-28

## Cloudwright Capability Summary

Cloudwright is an AI-powered architecture intelligence tool. Its capabilities:

- Natural language to architecture design (LLM-powered, multi-turn conversation)
- Cost estimation from catalog data (AWS, GCP, Azure pricing)
- Compliance validation (HIPAA, PCI-DSS, SOC 2, FedRAMP, GDPR, Well-Architected)
- IaC export (Terraform, CloudFormation)
- Architecture diffing (structured diff between two ArchSpecs)
- Diagram generation (Mermaid, D2)
- SBOM/AIBOM generation (CycloneDX, OWASP)
- Multi-cloud support (AWS, GCP, Azure)
- Cross-cloud service equivalence mapping
- Open source (Python, local-first, no external DB dependencies)


---

## Capability Matrix

| Tool | NL-to-Arch | Produces IaC | Cost Est. | Compliance | Arch Diff | Diagrams | Multi-Cloud | Open Source |
|------|:----------:|:------------:|:---------:|:----------:|:---------:|:--------:|:-----------:|:----------:|
| **Cloudwright** | Y | Y (TF, CFN) | Y | Y | Y | Y | Y (AWS/GCP/Azure) | Y |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **IaC / Provisioning** | | | | | | | | |
| Terraform / OpenTofu | N | Y (HCL) | N | N | Y (plan diff) | N | Y (all) | Y (OpenTofu MPL 2.0, TF BSL) |
| Pulumi | Y (via Neo) | Y (code) | N (native) | Y (OPA policies) | Y (preview diff) | N | Y (all) | Y (engine), N (cloud) |
| AWS CDK / CloudFormation | N | Y (TS/Py/CFN) | N | N | Y (cdk diff) | N | N (AWS only) | Y (CDK), N (CFN service) |
| Crossplane | N | Y (YAML CRDs) | N | N | Y (K8s diff) | N | Y (all) | Y (Apache 2.0) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **AI Architecture Tools** | | | | | | | | |
| AWS Well-Architected Tool | N | N | N | Y (AWS frameworks) | N | N | N (AWS only) | N |
| DuploCloud | N | Y (generated) | N | Y (built-in) | N | N | Y (AWS/GCP/Azure) | N |
| Firefly.ai | N | Y (codification) | N | Y (600+ policies) | Y (drift) | N | Y (all) | N |
| env0 | N | N (orchestration) | Y (cost est.) | Y (policies) | Y (drift) | N | Y (all) | N |
| Spacelift | N | N (orchestration) | Y (Infracost integ.) | Y (OPA policies) | Y (drift) | N | Y (all) | N |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Cost Management** | | | | | | | | |
| Infracost | N | N | Y | N | Y (cost diff) | N | Y (AWS/GCP/Azure) | Y (CLI) |
| Komiser (Tailwarden) | N | N | Y | Y (basic) | N | N | Y (AWS/GCP/Azure+) | Y (Komiser) |
| AWS Cost Explorer | N | N | Y | N | N | N | N (AWS only) | N |
| Finout | N | N | Y | N | N | N | Y (all + SaaS) | N |
| Vantage | N | N | Y | N | N | N | Y (all + SaaS) | N |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Security / Compliance** | | | | | | | | |
| Checkov (Bridgecrew) | N | N | N | Y (2500+ policies) | N | N | Y (AWS/GCP/Azure/K8s) | Y |
| tfsec / Trivy | N | N | N | Y | N | N | Y (AWS/GCP/Azure/K8s) | Y |
| Prowler | N | N | N | Y (1000+ controls) | N | N | Y (AWS/GCP/Azure/K8s) | Y |
| AWS Config Rules | N | N | N | Y | N | N | N (AWS only) | N |
| OPA / Rego | N | N | N | Y (policy engine) | N | N | Y (agnostic) | Y |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Diagramming** | | | | | | | | |
| Diagrams (Python) | N | N | N | N | N | Y | Y (AWS/GCP/Azure/K8s) | Y |
| Mermaid | N | N | N | N | N | Y | N (generic) | Y |
| Lucidchart | Y (AI diagrams) | N | N | N | N | Y | Y (shape libs) | N |
| draw.io | Y (AI diagrams) | N | N | N | N | Y | Y (shape libs) | Y (core) |
| Brainboard | Y | Y (Terraform) | Y (budget view) | N | Y (drift) | Y | Y (AWS/GCP/Azure/OCI) | N |
| Cloudcraft | N | N | Y (budget view) | N | N | Y | Y (AWS/Azure) | N |


---

## Detailed Tool Profiles

---

### IaC / Provisioning

#### Terraform / OpenTofu

**What it does:**
Declarative IaC using HCL. State management, plan/apply workflow, 3900+ providers. OpenTofu is the open-source fork (MPL 2.0) after HashiCorp moved to BSL. OpenTofu adds native client-side state encryption. Largest IaC ecosystem.

**What it does NOT do:**
- No natural language interface
- No cost estimation (requires Infracost integration)
- No compliance validation (requires Checkov/tfsec/OPA add-ons)
- No architecture design intelligence
- No diagram generation
- No architecture-level diffing (plan diff is resource-level, not architectural)

**Pricing:** Terraform CLI is free (BSL). Terraform Cloud: free tier, Team $20/user/mo, Business custom. OpenTofu is fully free and open source.

**Cloudwright comparison:** Cloudwright generates Terraform as an export format. Terraform is a deployment engine; Cloudwright is the design intelligence layer that sits before Terraform in the workflow. They are complementary, not competitive, though Cloudwright reduces the need for hand-written HCL.

Sources: [Terraform vs OpenTofu](https://platformengineering.org/blog/terraform-vs-opentofu-iac-tool), [OpenTofu vs Terraform](https://spacelift.io/blog/opentofu-vs-terraform)

---

#### Pulumi

**What it does:**
IaC using real programming languages (Python, TypeScript, Go, C#, Java). Pulumi Neo (launched 2025) is an AI agent that translates natural language into infrastructure code, handles full stack operations, and can auto-remediate policy violations. Code-native architecture gives LLMs a natural advantage since they're trained on these languages.

**What it does NOT do:**
- Neo is an IaC copilot, not an architecture designer -- it provisions what you ask for but doesn't reason about architecture patterns, trade-offs, or alternatives
- No cost estimation built-in (relies on third-party tools)
- No compliance frameworks out of the box (uses OPA-based policies, requires writing them)
- No architecture diffing at the design level
- No diagram generation
- No cross-cloud equivalence mapping

**Pricing:** Free for individuals. Team: 150k free credits/mo then $0.0005/credit. Enterprise: avg ~$34k/yr, up to $250k.

**Cloudwright comparison:** Pulumi Neo is the closest competitor in the "NL-to-infrastructure" space, but operates at a different abstraction level. Pulumi Neo generates deployment code; Cloudwright generates architecture specifications that can then be exported to Pulumi, Terraform, or CloudFormation. Cloudwright reasons about design trade-offs, compliance, and cost before any code is written. Werner Enterprises reported reducing provisioning from 3 days to 4 hours with Neo.

Sources: [Pulumi Neo](https://www.infoq.com/news/2025/09/pulumi-neo/), [Pulumi AI Agents](https://devops.com/pulumi-previews-ai-agents-trained-to-automate-infrastructure-management/), [Pulumi Pricing](https://spacelift.io/blog/pulumi-pricing)

---

#### AWS CDK / CloudFormation

**What it does:**
AWS CDK defines cloud infrastructure using TypeScript, Python, Java, C#, Go and synthesizes to CloudFormation templates. Higher-level constructs (L2/L3) encode AWS best practices. 2025 additions: stack refactoring (reorganize without disrupting resources), IaC MCP Server for AI assistant integration, CDK Mixins. CloudFormation is the underlying deployment engine for all AWS IaC.

**What it does NOT do:**
- AWS only -- no multi-cloud
- No natural language interface (though MCP Server enables AI assistants to help)
- No cost estimation
- No compliance validation
- No diagram generation
- No architecture design intelligence

**Pricing:** CDK is open source (Apache 2.0). CloudFormation is free (pay only for provisioned resources). No per-user or per-deployment fees.

**Cloudwright comparison:** Cloudwright exports to CloudFormation as an output format. CDK/CFN is AWS-locked; Cloudwright is multi-cloud. Cloudwright provides the design layer that CDK lacks -- compliance, cost, trade-off analysis -- then hands off to CDK/CFN for deployment.

Sources: [AWS CDK Features](https://aws.amazon.com/cdk/features/), [CloudFormation 2025 Review](https://aws.amazon.com/blogs/devops/aws-cloudformation-2025-year-in-review/)

---

#### Crossplane

**What it does:**
Kubernetes-native infrastructure provisioning using CRDs and YAML. Treats infrastructure as Kubernetes resources with reconciliation loops, RBAC, and GitOps integration. Crossplane 2.0 (Aug 2025) expanded to full application orchestration, unified abstractions, and namespace-first approach. Platform engineers define composite resources that developers consume.

**What it does NOT do:**
- No natural language interface
- No cost estimation
- No compliance validation
- No architecture design intelligence
- No diagram generation
- Requires Kubernetes expertise and a running cluster
- No cost analysis

**Pricing:** Fully open source (Apache 2.0). Upbound (the commercial company) offers managed Crossplane.

**Cloudwright comparison:** Crossplane is a deployment mechanism, not a design tool. Cloudwright could potentially export to Crossplane CRDs in the future. Crossplane targets platform engineering teams already running Kubernetes; Cloudwright targets architects making design decisions before the Kubernetes cluster exists.

Sources: [Crossplane 2.0](https://www.infoq.com/news/2025/08/crossplane-applications-v2/), [Crossplane AI](https://blog.crossplane.io/crossplane-ai-the-case-for-api-first-infrastructure/)

---

### AI Architecture Tools

#### AWS Well-Architected Tool

**What it does:**
Questionnaire-based review of workloads against AWS Well-Architected Framework pillars (operational excellence, security, reliability, performance, cost optimization, sustainability). New in 2025: Responsible AI Lens, updated ML Lens, updated GenAI Lens. AI-powered acceleration of reviews using Bedrock. Free in the AWS Console.

**What it does NOT do:**
- AWS only -- no multi-cloud
- No architecture generation -- it reviews existing architectures via questionnaires
- No IaC generation
- No cost estimation
- No diagram generation
- No architecture diffing
- Manual, questionnaire-driven process (even with AI acceleration)
- No design intelligence or natural language input

**Pricing:** Free (included with AWS account).

**Cloudwright comparison:** AWS WAT is a review tool; Cloudwright is a design tool. Cloudwright incorporates Well-Architected Framework checks as part of its validator, but also generates architectures that are compliant by default. WAT requires you to already have an architecture; Cloudwright creates one from scratch. WAT is AWS-only; Cloudwright is multi-cloud.

Sources: [AWS Well-Architected Lenses 2025](https://aws.amazon.com/blogs/architecture/architecting-for-ai-excellence-aws-launches-three-well-architected-lenses-at-reinvent-2025/)

---

#### DuploCloud

**What it does:**
Low-code/no-code platform for DevOps automation. Visual interface to provision cloud resources across AWS, Azure, GCP. Built-in compliance (SOC 2, HIPAA, PCI-DSS, HITRUST). Generates Terraform under the hood. Handles backups, disaster recovery, SSO, JIT access.

**What it does NOT do:**
- No natural language architecture design
- No architecture intelligence or trade-off analysis
- No cost estimation
- No architecture diffing
- No diagram generation
- No open source option
- Abstracts away IaC rather than teaching it

**Pricing:** $2,000-$6,500/mo depending on tier and user count.

**Cloudwright comparison:** DuploCloud targets teams that want to avoid writing IaC entirely -- it's an abstraction layer. Cloudwright targets architects who want AI-assisted design with full IaC output they control. DuploCloud's compliance is stronger (HITRUST, automated controls), but it locks you into their platform. Cloudwright produces portable artifacts.

Sources: [DuploCloud Pricing](https://duplocloud.com/pricing/), [DuploCloud Reviews](https://www.g2.com/products/duplocloud/reviews)

---

#### Firefly.ai

**What it does:**
Cloud asset management + IaC management. Auto-generates IaC from existing infrastructure (reverse codification). Drift detection and remediation. 600+ compliance policies. AI Disaster Recovery Agent (2025) that autonomously backs up and restores cloud configurations. Unified view across multi-cloud, K8s, and SaaS.

**What it does NOT do:**
- No natural language architecture design
- No architecture generation from scratch
- No cost estimation (focuses on governance, not pricing)
- No diagram generation
- No architecture-level diffing (drift detection is resource-level)
- Operates on existing infrastructure, not greenfield design

**Pricing:** Enterprise SaaS, custom pricing. No public pricing available.

**Cloudwright comparison:** Firefly operates on existing infrastructure (Day 2); Cloudwright operates on architecture design (Day 0). Firefly codifies what you already have; Cloudwright designs what you should build. Complementary tools. Firefly's DR Agent is unique -- Cloudwright doesn't cover disaster recovery automation.

Sources: [Firefly Product](https://www.firefly.ai/product), [Firefly DR](https://siliconangle.com/2025/11/25/firefly-ai-says-can-make-apps-almost-invulnerable-cloud-outages/)

---

#### env0

**What it does:**
IaC orchestration and governance platform. Supports Terraform, OpenTofu, Terragrunt, Pulumi, CloudFormation, Ansible, K8s, Helm. 2025 additions: Cloud Analyst (AI), AI PR Summaries, MCP Server for IDE integration, instant drift detection, ready-to-use policies. Cost estimation for Terraform plans.

**What it does NOT do:**
- No natural language architecture design
- No architecture generation
- No diagram generation
- No architecture diffing (only drift detection)
- Orchestration layer, not a design tool

**Pricing:** Free tier available. Paid from $349/mo. Enterprise custom.

**Cloudwright comparison:** env0 manages the IaC lifecycle (plan, apply, approve, drift); Cloudwright generates the IaC in the first place. env0 could be downstream of Cloudwright -- Cloudwright designs and exports Terraform, env0 deploys it. env0's cost estimation is for existing Terraform, not for architectural exploration.

Sources: [env0 Platform](https://www.env0.com/), [env0 Cost Estimation](https://www.devprojournal.com/news/env0-unveils-intelligent-cost-estimation-to-predict-and-better-manage-cloud-costs/)

---

#### Spacelift

**What it does:**
IaC orchestration platform. Supports Terraform, OpenTofu, Terragrunt, Ansible, Pulumi, CloudFormation, Kubernetes. OPA-based policy enforcement, drift detection, blueprints for self-service infrastructure, audit trails, credentialless cloud integrations. Infracost integration for cost visibility.

**What it does NOT do:**
- No natural language architecture design
- No architecture generation
- No native cost estimation (relies on Infracost integration)
- No diagram generation
- No architecture-level diffing
- Orchestration, not design

**Pricing:** Free (2 users, 1 concurrency). Cloud from $250/mo. Starter from $399/mo. Enterprise custom. Priced on concurrency, not resources.

**Cloudwright comparison:** Same relationship as env0 -- Spacelift is a deployment orchestrator, Cloudwright is a design intelligence tool. They serve different phases of the infrastructure lifecycle. Spacelift's Blueprints are the closest feature to Cloudwright's design capability, but blueprints are pre-built templates, not AI-generated custom architectures.

Sources: [Spacelift Platform](https://spacelift.io/), [Spacelift Features](https://medium.com/spacelift/what-is-spacelift-key-features-benefits-use-cases-d5d3e27477aa)

---

### Cost Management

#### Infracost

**What it does:**
Parses Terraform plans and calculates monthly cost estimates using cloud provider pricing APIs. Shows cost diffs in pull requests. Supports 1000+ Terraform resources across AWS, Azure, GCP. Enterprise features: dashboard, AutoFix (auto-generates remediation PRs), budget guardrails, custom price books.

**What it does NOT do:**
- No architecture design
- No natural language interface
- No compliance validation
- No diagram generation
- Terraform-only (no CloudFormation, Pulumi, etc.)
- Post-code cost estimation only -- cannot estimate costs during design phase

**Pricing:** Open source CLI (free). Cloud: includes 10 seats, additional at $100/seat/mo.

**Cloudwright comparison:** Infracost estimates costs after Terraform code exists; Cloudwright estimates costs during architecture design before any code is written. Cloudwright's cost engine uses its own catalog and pricing data, not Terraform plans. Different phases: Cloudwright = design-time cost, Infracost = code-time cost. Complementary.

Sources: [Infracost](https://www.infracost.io/), [Infracost GitHub](https://github.com/infracost/infracost)

---

#### Komiser (Tailwarden)

**What it does:**
Open-source cloud resource manager. Builds inventory of cloud assets, analyzes costs, detects anomalies. Tailwarden (commercial) adds dashboards, policy enforcement, Slack alerts, budget tracking. Supports AWS, Azure, GCP, DigitalOcean, OCI, Linode, Scaleway, and more.

**What it does NOT do:**
- No architecture design
- No IaC generation
- No architecture diffing
- No diagram generation
- No natural language interface
- Focused on existing spend analysis, not design-time estimation

**Pricing:** Komiser is open source. Tailwarden: custom enterprise pricing.

**Cloudwright comparison:** Komiser/Tailwarden is a Day 2 cost analysis tool; Cloudwright is a Day 0 design tool with cost estimation. No overlap -- they serve completely different phases.

Sources: [Komiser GitHub](https://github.com/tailwarden/komiser), [Tailwarden](https://www.tailwarden.com/)

---

#### AWS Cost Explorer

**What it does:**
AWS-native cost analysis. 36 months historical data, 18-month AI-powered forecasting (enhanced in 2025). Filter and group by service, account, tag. Savings Plans recommendations. Free in Console, $0.01/API request.

**What it does NOT do:**
- AWS only
- No architecture design
- No IaC generation
- No compliance validation
- No diagram generation
- No design-time estimation -- only analyzes past/current spend
- No multi-cloud

**Pricing:** Free (Console). API: $0.01/request.

**Cloudwright comparison:** AWS Cost Explorer analyzes past spend; Cloudwright estimates future spend for architectures not yet deployed. Completely different use case. Cost Explorer requires deployed resources; Cloudwright estimates from specifications alone.

Sources: [AWS Cost Explorer Guide](https://sedai.io/blog/aws-cost-explorer-guide-understand-reduce-expenses), [AWS re:Invent 2025 Cost Management](https://dev.to/kazuya_dev/aws-reinvent-2025-whats-new-with-aws-cost-management-cop203-3ofd)

---

#### Finout

**What it does:**
Enterprise FinOps platform. MegaBill unifies all cloud + SaaS spend into one model. Virtual Tagging (assigns labels without upstream tag changes). Anomaly detection, budgeting, forecasting. Supports AWS, Azure, GCP, K8s, Snowflake, Datadog, and many SaaS. No agents or code changes required.

**What it does NOT do:**
- No architecture design
- No IaC generation
- No compliance validation
- No diagram generation
- No design-time estimation
- Expensive for small teams

**Pricing:** ~1% of cloud spend tracked. Three subscription tiers. Enterprise custom.

**Cloudwright comparison:** Finout is a FinOps platform for spend management; Cloudwright is an architecture tool with cost estimation. No overlap. Finout optimizes existing spend; Cloudwright prevents wasteful architecture before deployment.

Sources: [Finout Platform](https://www.finout.io), [Finout Pricing](https://www.cloudzero.com/blog/finout-pricing/)

---

#### Vantage

**What it does:**
Multi-cloud cost management. 12+ native billing integrations (AWS, Azure, GCP, K8s, Datadog, Snowflake, Databricks). Cost reports, dashboards, budgets, forecasting. Autopilot auto-purchases AWS Savings Plans. Unlimited users at every tier.

**What it does NOT do:**
- No architecture design
- No IaC generation
- No compliance validation
- No diagram generation
- No design-time estimation

**Pricing:** Free starter (up to $2,500 tracked spend). Paid tiers start at 1% of tracked spend with graduated discounts. Autopilot: 5% of generated savings.

**Cloudwright comparison:** Same as Finout -- Day 2 cost optimization, not Day 0 architecture design. Vantage Autopilot (auto-purchasing Savings Plans) is unique and outside Cloudwright's scope.

Sources: [Vantage](https://www.vantage.sh/), [Vantage Pricing](https://www.nops.io/blog/vantage-pricing-explained/)

---

### Security / Compliance

#### Checkov (Bridgecrew / Palo Alto)

**What it does:**
Static analysis for IaC. 2500+ built-in policies. Scans Terraform, CloudFormation, Kubernetes, Helm, Dockerfile, ARM, Bicep, OpenTofu, and more. Graph-based analysis evaluates resource relationships. SCA scanning for CVEs. Enterprise version is Prisma Cloud Application Security.

**What it does NOT do:**
- No architecture design
- No IaC generation
- No cost estimation
- No diagram generation
- No architecture diffing
- Scans existing code, doesn't generate compliant code
- No natural language interface

**Pricing:** Open source (free). Enterprise via Prisma Cloud (custom pricing).

**Cloudwright comparison:** Checkov validates IaC code after it's written; Cloudwright's validator checks architecture designs before code exists and generates designs that are compliant from the start. Checkov has deeper policy coverage (2500+ vs Cloudwright's framework-level checks). Ideal to run Checkov on Cloudwright's Terraform output as a defense-in-depth measure.

Sources: [Checkov](https://www.checkov.io/), [Checkov GitHub](https://github.com/bridgecrewio/checkov)

---

#### tfsec / Trivy

**What it does:**
tfsec is now part of Trivy (Aqua Security). Unified scanner for IaC misconfigurations, container image vulnerabilities, secrets, licenses. Supports Terraform, CloudFormation, ARM, Helm, Kubernetes. Auto-detects file types. "Next-Gen Trivy" arriving in 2026.

**What it does NOT do:**
- No architecture design
- No IaC generation
- No cost estimation
- No diagram generation
- No architecture diffing
- No natural language interface
- Scans code, doesn't generate it

**Pricing:** Open source (Apache 2.0). Aqua Platform (commercial) for enterprise.

**Cloudwright comparison:** Same relationship as Checkov -- post-code scanning vs. pre-code design intelligence. Trivy is broader (containers, SBOMs, secrets) but operates at a different phase. Cloudwright's SBOM/AIBOM export could feed into Trivy's vulnerability scanning.

Sources: [tfsec to Trivy](https://github.com/aquasecurity/tfsec), [Trivy](https://trivy.dev/)

---

#### Prowler

**What it does:**
Cloud security platform. 1000+ security controls. Supports AWS, Azure, GCP, K8s, GitHub, Microsoft 365, Cloudflare. Frameworks: CIS, PCI-DSS, ISO27001, GDPR, HIPAA, SOC 2, NIST. AI-driven detection check generation. Autonomous Fixer for guided remediation. Attack path analysis via Neo4j graph.

**What it does NOT do:**
- No architecture design
- No IaC generation
- No cost estimation
- No diagram generation
- No architecture diffing
- Scans live cloud environments, not architecture specifications
- No natural language interface

**Pricing:** Open source CLI (free). Prowler SaaS (commercial, custom pricing).

**Cloudwright comparison:** Prowler scans deployed infrastructure; Cloudwright validates architecture designs. Prowler has broader compliance framework coverage and runtime security (attack paths). Cloudwright catches compliance issues at design time; Prowler catches them at runtime. Complementary layers in a defense-in-depth strategy.

Sources: [Prowler](https://prowler.com/), [Prowler GitHub](https://github.com/prowler-cloud/prowler)

---

#### AWS Config Rules

**What it does:**
AWS-native configuration compliance. Pre-built and custom rules evaluate resource configurations. Conformance packs bundle rules for framework compliance. Compliance scoring. Multi-account aggregators. 2025: 279 additional rules, 7 new compliance frameworks via Control Tower integration.

**What it does NOT do:**
- AWS only
- No architecture design
- No IaC generation
- No cost estimation
- No diagram generation
- No architecture diffing
- No natural language interface
- Runtime detection only, not design-time

**Pricing:** $0.003 per rule evaluation per region. Conformance pack evaluations included.

**Cloudwright comparison:** AWS Config is runtime compliance for deployed AWS resources; Cloudwright is design-time compliance for architecture specifications. AWS Config is deeper for AWS-specific controls but single-cloud. Cloudwright catches issues before deployment across multiple clouds.

Sources: [AWS Config Features](https://aws.amazon.com/config/features/), [AWS Control Tower Update](https://aws.amazon.com/about-aws/whats-new/2025/11/aws-control-tower-new-compliance-frameworks-additional-aws-config-rules/)

---

#### OPA / Rego

**What it does:**
General-purpose policy engine. Rego is a declarative policy language. Used across the stack: Kubernetes admission control, API authorization, IaC policy, CI/CD gates. CNCF graduated project. In-memory evaluation for low-latency decisions. Comprehensive audit trails.

**What it does NOT do:**
- No architecture design
- No IaC generation
- No cost estimation
- No diagram generation
- No architecture diffing
- No natural language interface
- Policy engine only -- requires writing policies in Rego
- No built-in compliance frameworks (you build your own)

**Pricing:** Fully open source (Apache 2.0). Styra (commercial) offers OPA management.

**Cloudwright comparison:** OPA is a policy evaluation engine; Cloudwright has compliance checks built into its validator. OPA is far more flexible and general-purpose. Cloudwright could use OPA as a policy backend in the future. OPA requires policy authoring expertise; Cloudwright's compliance checks are built-in and require no policy code.

Sources: [OPA](https://www.openpolicyagent.org/), [OPA GitHub](https://github.com/open-policy-agent/opa)

---

### Diagramming

#### Diagrams (Python)

**What it does:**
Python library for drawing cloud architecture diagrams as code. Supports AWS, Azure, GCP, K8s, Alibaba, Oracle, on-premises. Clustering for logical groupings. Version-controllable. Renders via Graphviz.

**What it does NOT do:**
- No architecture design
- No IaC generation
- No cost estimation
- No compliance validation
- No architecture diffing
- No natural language interface
- Output only -- renders images, no interactivity
- Requires Python coding to create diagrams

**Pricing:** Open source (MIT).

**Cloudwright comparison:** Cloudwright uses Mermaid and D2 for diagram output, not the Diagrams library, but they serve a similar purpose. Diagrams requires manual Python code; Cloudwright auto-generates diagrams from ArchSpec. Diagrams produces nicer visual output (PNG/SVG) vs. Cloudwright's text-based formats.

Sources: [Diagrams](https://diagrams.mingrammer.com/), [Diagrams GitHub](https://github.com/mingrammer/diagrams)

---

#### Mermaid

**What it does:**
JavaScript-based text-to-diagram tool. Markdown-inspired syntax. Supports flowcharts, sequence diagrams, ER diagrams, C4, architecture, Gantt, state, and many more. Mermaid Chart (commercial) adds real-time collaboration. AI-assisted diagram generation. Embedded in GitHub, GitLab, Notion, and many tools natively.

**What it does NOT do:**
- No architecture design intelligence
- No IaC generation
- No cost estimation
- No compliance validation
- No architecture diffing
- Generic diagramming, not cloud-architecture specific

**Pricing:** Open source (MIT). Mermaid Chart: free tier, paid plans for teams.

**Cloudwright comparison:** Cloudwright uses Mermaid as one of its diagram export formats. Mermaid is a rendering engine; Cloudwright is the intelligence that decides what to render. Mermaid's ubiquitous integration (GitHub, GitLab) makes it a good output format choice.

Sources: [Mermaid](https://mermaid.js.org/), [Mermaid GitHub](https://github.com/mermaid-js/mermaid)

---

#### Lucidchart

**What it does:**
SaaS diagramming platform. Cloud shape libraries (AWS, Azure, GCP). Real-time collaboration. AI diagram generation from natural language prompts. Data linking (bi-directional with external data). Deep integrations (Google Workspace, Microsoft Office, Jira, Confluence, Slack).

**What it does NOT do:**
- AI generates starter diagrams, not production architectures
- No IaC generation
- No cost estimation
- No compliance validation
- No architecture diffing
- Diagrams are visual artifacts, not actionable specifications

**Pricing:** Free (limited). Individual $9.95/user/mo. Team $20/user/mo. Enterprise custom (~$120/user/yr negotiated for large orgs).

**Cloudwright comparison:** Lucidchart is a visual tool; Cloudwright is an intelligence tool. Lucidchart's AI generates diagram layouts; Cloudwright's AI generates architecture designs with IaC, cost, and compliance analysis. Lucidchart diagrams are pictures; Cloudwright's ArchSpec is a machine-readable specification that can be deployed.

Sources: [Lucidchart Pricing](https://www.spendflo.com/blog/lucidchart-pricing-guide)

---

#### draw.io (diagrams.net)

**What it does:**
Free diagramming tool. Cloud shape libraries (AWS, Azure, K8s, Cisco). Storage on Google Drive, OneDrive, GitHub, GitLab. AI diagram generation (2026). MCP Server for AI agent integration (Feb 2026). Confluence/Jira integration. Fully client-side (Forge) for data residency.

**What it does NOT do:**
- AI generates layouts, not architectures
- No IaC generation
- No cost estimation
- No compliance validation
- No architecture diffing
- Diagrams are not machine-readable specifications

**Pricing:** Free (core). Paid Atlassian marketplace apps.

**Cloudwright comparison:** draw.io is a drawing tool; Cloudwright is an architecture tool. draw.io's new MCP Server integration is interesting -- it could potentially consume Cloudwright output for visualization. But draw.io diagrams can't be deployed, priced, or validated. Cloudwright's output is actionable.

Sources: [draw.io](https://www.drawio.com/blog/features), [draw.io MCP](https://medium.com/google-cloud/automating-mastering-infrastructure-diagrams-with-draw-io-mcp-and-antigravity-2839b78df143)

---

#### Brainboard

**What it does:**
Visual cloud architecture designer with instant Terraform code generation. AI (Bob) generates diagrams and Terraform from natural language prompts. Supports AWS, Azure, GCP, OCI, Scaleway. Drift detection. Module catalog. OpenTofu 1.6+ compatibility. Collaborative workspace.

**What it does NOT do:**
- No cost estimation beyond basic budget view
- No compliance validation (HIPAA, PCI-DSS, etc.)
- No architecture diffing (drift detection is resource-level)
- No SBOM/AIBOM generation
- No CloudFormation export
- No cross-cloud equivalence mapping
- No multi-turn architectural conversation

**Pricing:** Free tier available. Paid tiers not publicly listed (contact sales).

**Cloudwright comparison:** Brainboard is the closest direct competitor. Both do NL-to-architecture and Terraform generation. Key Cloudwright advantages: compliance validation, cost estimation from catalog, architecture diffing, multi-format export (TF + CFN + Mermaid + D2 + SBOM), open source, local-first. Key Brainboard advantages: visual drag-and-drop designer, real-time collaboration UI, production-grade deployment pipeline, OCI/Scaleway support.

Sources: [Brainboard](https://www.brainboard.co), [Brainboard AI](https://dev.to/brainboard/ai-enhanced-architecture-design-with-bob-38dm), [Brainboard AI Terraform](https://blog.brainboard.co/ai-terraform-diagrammer/)

---

#### Cloudcraft

**What it does:**
AWS/Azure architecture diagram tool. Live infrastructure scanning (auto-generates diagrams from AWS/Azure accounts). 2D and 3D views. Budget auto-generated as you design. API for CI/CD snapshot automation. Owned by Datadog.

**What it does NOT do:**
- No natural language architecture design
- No IaC generation
- No compliance validation
- No architecture diffing
- AWS and Azure only (no GCP)
- Cost view is read-only budget, not estimation for new designs
- Diagrams are visual only, not deployable

**Pricing:** Free (basic). Pro $49/user/mo (annual) or $99/mo. Enterprise $120/user/mo.

**Cloudwright comparison:** Cloudcraft is a visualization tool with basic cost budgeting; Cloudwright is a design tool with full cost estimation, compliance, and IaC export. Cloudcraft's live scanning is unique -- Cloudwright doesn't scan existing infrastructure. Cloudcraft is stronger at "document what exists"; Cloudwright is stronger at "design what should exist."

Sources: [Cloudcraft](https://www.cloudcraft.co/), [Cloudcraft Pricing](https://www.cloudcraft.co/pricing)


---

## Competitive Positioning Summary

### Where Cloudwright is Unique

No single tool in the market combines all of these capabilities:

1. **NL-to-architecture with compliance awareness** -- Pulumi Neo generates code, Brainboard generates diagrams + TF, but neither validates against HIPAA/PCI-DSS/FedRAMP/GDPR during the design phase
2. **Design-time cost estimation** -- Infracost requires Terraform code, AWS Cost Explorer requires deployed resources, Cloudwright estimates from architecture specifications alone
3. **Architecture diffing** -- Terraform plan diff is resource-level; Cloudwright's differ understands architectural-level changes (security implications, compliance impact)
4. **Multi-format IaC export from a single spec** -- Terraform AND CloudFormation from the same ArchSpec, plus Mermaid/D2 diagrams and CycloneDX SBOM
5. **Open source + local-first** -- No SaaS dependency, no cloud account required, runs entirely on the user's machine

### Closest Competitors by Overlap

1. **Brainboard** -- highest feature overlap (NL-to-arch, Terraform, diagrams, multi-cloud). Brainboard is SaaS, visual-first, no compliance/cost. Cloudwright is open source, spec-first, with compliance + cost.
2. **Pulumi Neo** -- overlaps on NL-to-infrastructure and multi-cloud. Neo is deeper on deployment; Cloudwright is deeper on design intelligence.
3. **DuploCloud** -- overlaps on compliance + multi-cloud + IaC. DuploCloud is a managed platform; Cloudwright is a tool that produces portable artifacts.

### Where Competitors are Stronger

- **Deployment orchestration:** Spacelift, env0, Terraform Cloud -- Cloudwright doesn't deploy
- **Runtime security:** Prowler, Checkov, Trivy -- Cloudwright only validates at design time
- **Spend management:** Finout, Vantage, AWS Cost Explorer -- Cloudwright estimates, doesn't track actuals
- **Visual collaboration:** Lucidchart, Brainboard, draw.io -- Cloudwright's web UI is basic compared to mature SaaS diagramming
- **Live infrastructure scanning:** Cloudcraft, Firefly -- Cloudwright doesn't scan existing infrastructure


### Market Gap Cloudwright Fills

The architecture intelligence layer between "I need a 3-tier HIPAA-compliant app on AWS" and "here's the Terraform code, here's what it'll cost, here's the compliance report." Every other tool requires the user to already know what they want to build (IaC tools) or already have it deployed (cost/security tools). Cloudwright operates in the design phase that currently relies on architects' tribal knowledge, manual spreadsheets, and ad-hoc Confluence pages.
