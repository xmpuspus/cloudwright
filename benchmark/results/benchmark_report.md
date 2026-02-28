# Cloudwright Benchmark Report

**Date:** 2026-02-28  
**Use cases:** 54  
**Cloudwright wins:** 6/8 metrics  

---

## Summary

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 79.6% ✓ | 37.0% | +42.6% |
| Cost Accuracy | 13.0% ✗ | 15.9% | -2.8% |
| Service Correctness | 73.1% ✗ | 97.1% | -24.0% |
| Compliance Completeness | 62.9% ✓ | 38.5% | +24.3% |
| Export Quality (IaC) | 55.7% ✓ | 0.3% | +55.5% |
| Diff Capability | 100.0% ✓ | 0.0% | +100.0% |
| Reproducibility | 77.9% ✓ | 35.0% | +42.9% |
| Time to IaC | 82.5% ✓ | 0.0% | +82.5% |
| **Overall** | **68.1%** | **28.0%** | **+40.1%** |

---

## Results by Category

### Greenfield (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 36.0% | +64.0% |
| Cost Accuracy | 18.3% | 40.2% | -21.8% |
| Service Correctness | 96.0% | 100.0% | -4.0% |
| Compliance Completeness | 85.7% | 50.0% | +35.7% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 87.8% | 0.0% | +87.8% |

### Compliance (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 32.0% | +68.0% |
| Cost Accuracy | 6.8% | 20.0% | -13.2% |
| Service Correctness | 100.0% | 90.5% | +9.5% |
| Compliance Completeness | 94.0% | 56.0% | +38.0% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 84.5% | 0.0% | +84.5% |

### Cost (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 80.0% | 44.0% | +36.0% |
| Cost Accuracy | 34.2% | 26.7% | +7.5% |
| Service Correctness | 71.0% | 100.0% | -29.0% |
| Compliance Completeness | 60.0% | 24.0% | +36.0% |
| Export Quality (IaC) | 56.0% | 0.0% | +56.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 78.0% | 35.0% | +43.0% |
| Time to IaC | 82.7% | 0.0% | +82.7% |

### Import (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 20.0% | 68.0% | -48.0% |
| Cost Accuracy | 2.2% | 1.5% | +0.8% |
| Service Correctness | 20.0% | 100.0% | -80.0% |
| Compliance Completeness | 17.1% | 40.0% | -22.9% |
| Export Quality (IaC) | 14.0% | 3.0% | +11.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 57.0% | 35.0% | +22.0% |
| Time to IaC | 79.5% | 0.0% | +79.5% |

### Microservices (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 36.0% | +64.0% |
| Cost Accuracy | 4.7% | 0.0% | +4.7% |
| Service Correctness | 92.0% | 92.0% | +0.0% |
| Compliance Completeness | 82.8% | 22.0% | +60.8% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 85.6% | 0.0% | +85.6% |

### Data (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 32.0% | +68.0% |
| Cost Accuracy | 7.5% | 0.0% | +7.5% |
| Service Correctness | 92.0% | 100.0% | -8.0% |
| Compliance Completeness | 62.8% | 28.0% | +34.8% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 81.8% | 0.0% | +81.8% |

### Industry (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 80.0% | 24.0% | +56.0% |
| Cost Accuracy | 3.6% | 20.0% | -16.4% |
| Service Correctness | 72.0% | 97.1% | -25.1% |
| Compliance Completeness | 70.3% | 36.0% | +34.3% |
| Export Quality (IaC) | 56.0% | 0.0% | +56.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 78.0% | 35.0% | +43.0% |
| Time to IaC | 82.1% | 0.0% | +82.1% |

### Migration (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 60.0% | 36.0% | +24.0% |
| Cost Accuracy | 3.5% | 0.0% | +3.5% |
| Service Correctness | 52.0% | 96.0% | -44.0% |
| Compliance Completeness | 51.4% | 40.0% | +11.4% |
| Export Quality (IaC) | 42.0% | 0.0% | +42.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 71.0% | 35.0% | +36.0% |
| Time to IaC | 81.4% | 0.0% | +81.4% |

### Edge (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 80.0% | 32.0% | +48.0% |
| Cost Accuracy | 35.0% | 25.8% | +9.2% |
| Service Correctness | 65.3% | 96.0% | -30.7% |
| Compliance Completeness | 62.8% | 52.0% | +10.8% |
| Export Quality (IaC) | 56.0% | 0.0% | +56.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 78.0% | 35.0% | +43.0% |
| Time to IaC | 80.8% | 0.0% | +80.8% |

### Comparison (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 60.0% | 40.0% | +20.0% |
| Cost Accuracy | 22.1% | 29.8% | -7.6% |
| Service Correctness | 60.0% | 100.0% | -40.0% |
| Compliance Completeness | 40.0% | 24.0% | +16.0% |
| Export Quality (IaC) | 42.0% | 0.0% | +42.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 71.0% | 35.0% | +36.0% |
| Time to IaC | 78.6% | 0.0% | +78.6% |

---

## Failure Analysis

Cases where Cloudwright scored lower than Claude-raw on any metric:

| Case | Metric | Cloudwright | Claude-raw | Gap |
|------|--------|------------|-----------|-----|
| [15] FinOps Review of Existing Architect | Service Correctness | 0.0% | 100.0% | -100.0% |
| [16] Import Small Terraform State | Service Correctness | 0.0% | 100.0% | -100.0% |
| [17] Import Large Multi-Module Terraform | Service Correctness | 0.0% | 100.0% | -100.0% |
| [18] Import CloudFormation Template | Service Correctness | 0.0% | 100.0% | -100.0% |
| [20] Import Serverless Framework Deploym | Service Correctness | 0.0% | 100.0% | -100.0% |
| [34] Multi-Tenant B2B SaaS on AWS | Cost Accuracy | 0.0% | 100.0% | -100.0% |
| [34] Multi-Tenant B2B SaaS on AWS | Service Correctness | 0.0% | 100.0% | -100.0% |
| [38] Re-architect Monolith to Serverless | Service Correctness | 0.0% | 100.0% | -100.0% |
| [46] Container Orchestration Comparison  | Service Correctness | 0.0% | 100.0% | -100.0% |
| [50] Total Cost of Ownership — AWS vs GC | Service Correctness | 0.0% | 100.0% | -100.0% |
| [10] HIPAA-Compliant Serverless Teleheal | Cost Accuracy | 9.0% | 100.0% | -91.0% |
| [02] Enterprise Web Application on AWS | Cost Accuracy | 10.4% | 100.0% | -89.6% |
| [16] Import Small Terraform State | Structural Validity | 0.0% | 80.0% | -80.0% |
| [17] Import Large Multi-Module Terraform | Structural Validity | 0.0% | 80.0% | -80.0% |
| [20] Import Serverless Framework Deploym | Structural Validity | 0.0% | 80.0% | -80.0% |
| [40] Phased Hybrid Migration with Parall | Structural Validity | 0.0% | 80.0% | -80.0% |
| [40] Phased Hybrid Migration with Parall | Service Correctness | 0.0% | 80.0% | -80.0% |
| [44] Strict Multi-Compliance — HIPAA + P | Service Correctness | 0.0% | 80.0% | -80.0% |
| [41] Contradictory Requirements — CAP Th | Cost Accuracy | 22.2% | 100.0% | -77.8% |
| [18] Import CloudFormation Template | Compliance Completeness | 0.0% | 70.0% | -70.0% |

---

## Methodology

- **Cloudwright pipeline:** design -> cost -> validate -> export (Terraform)
- **Claude raw:** same prompt, generic system prompt, `2026` Claude Sonnet model
- **Cost accuracy:** deviation from stated budget constraint
- **Reproducibility:** estimated from schema constraints (multi-run data not collected)
- **Time to IaC:** Cloudwright = automated elapsed time; Claude raw = API time + 30min manual extraction estimate
