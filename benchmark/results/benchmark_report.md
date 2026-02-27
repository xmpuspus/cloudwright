# Cloudwright Benchmark Report

**Date:** 2026-02-28  
**Use cases:** 5  
**Cloudwright wins:** 6/8 metrics  

---

## Summary

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% ✓ | 64.0% | +36.0% |
| Cost Accuracy | 60.0% ✗ | 74.3% | -14.3% |
| Service Correctness | 90.0% ✗ | 93.3% | -3.3% |
| Compliance Completeness | 61.7% ✓ | 40.0% | +21.7% |
| Export Quality (IaC) | 70.0% ✓ | 0.0% | +70.0% |
| Diff Capability | 100.0% ✓ | 0.0% | +100.0% |
| Reproducibility | 85.0% ✓ | 35.0% | +50.0% |
| Time to IaC | 93.8% ✓ | 0.0% | +93.8% |
| **Overall** | **82.6%** | **38.3%** | **+44.2%** |

---

## Results by Category

### Greenfield (1 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 80.0% | +20.0% |
| Cost Accuracy | 100.0% | 100.0% | +0.0% |
| Service Correctness | 100.0% | 100.0% | +0.0% |
| Compliance Completeness | 42.9% | 60.0% | -17.1% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 95.5% | 0.0% | +95.5% |

### Compliance (1 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 80.0% | +20.0% |
| Cost Accuracy | 50.0% | 2.0% | +48.0% |
| Service Correctness | 83.3% | 100.0% | -16.7% |
| Compliance Completeness | 80.0% | 90.0% | -10.0% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 92.7% | 0.0% | +92.7% |

### Cost (1 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 40.0% | +60.0% |
| Cost Accuracy | 50.0% | 94.8% | -44.8% |
| Service Correctness | 100.0% | 100.0% | +0.0% |
| Compliance Completeness | 57.1% | 10.0% | +47.1% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 91.5% | 0.0% | +91.5% |

### Microservices (1 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 40.0% | +60.0% |
| Cost Accuracy | 50.0% | 74.7% | -24.7% |
| Service Correctness | 100.0% | 100.0% | +0.0% |
| Compliance Completeness | 71.4% | 20.0% | +51.4% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 94.6% | 0.0% | +94.6% |

### Edge (1 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 80.0% | +20.0% |
| Cost Accuracy | 50.0% | 100.0% | -50.0% |
| Service Correctness | 66.7% | 66.7% | +0.0% |
| Compliance Completeness | 57.1% | 20.0% | +37.1% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 94.6% | 0.0% | +94.6% |

---

## Failure Analysis

Cases where Cloudwright scored lower than Claude-raw on any metric:

| Case | Metric | Cloudwright | Claude-raw | Gap |
|------|--------|------------|-----------|-----|
| [41] Contradictory Requirements — CAP Th | Cost Accuracy | 50.0% | 100.0% | -50.0% |
| [13] Cross-Cloud Cost Comparison — 3-Tie | Cost Accuracy | 50.0% | 94.8% | -44.8% |
| [21] EKS Microservices Platform on AWS | Cost Accuracy | 50.0% | 74.7% | -24.7% |
| [01] Startup MVP on AWS | Compliance Completeness | 42.9% | 60.0% | -17.1% |
| [06] HIPAA-Compliant Healthcare Patient  | Service Correctness | 83.3% | 100.0% | -16.7% |
| [06] HIPAA-Compliant Healthcare Patient  | Compliance Completeness | 80.0% | 90.0% | -10.0% |

---

## Methodology

- **Cloudwright pipeline:** design -> cost -> validate -> export (Terraform)
- **Claude raw:** same prompt, generic system prompt, `2026` Claude Sonnet model
- **Cost accuracy:** deviation from stated budget constraint
- **Reproducibility:** estimated from schema constraints (multi-run data not collected)
- **Time to IaC:** Cloudwright = automated elapsed time; Claude raw = API time + 30min manual extraction estimate
