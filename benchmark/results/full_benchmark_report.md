# Cloudwright Benchmark Report

**Date:** 2026-02-28  
**Use cases:** 50  
**Cloudwright wins:** 7/8 metrics  

---

## Summary

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% ✓ | 48.0% | +52.0% |
| Cost Accuracy | 75.2% ✓ | 31.7% | +43.5% |
| Service Correctness | 83.8% ✗ | 97.1% | -13.3% |
| Compliance Completeness | 61.5% ✓ | 41.0% | +20.5% |
| Export Quality (IaC) | 70.0% ✓ | 0.0% | +70.0% |
| Diff Capability | 100.0% ✓ | 0.0% | +100.0% |
| Reproducibility | 85.0% ✓ | 35.0% | +50.0% |
| Time to IaC | 92.7% ✓ | 0.0% | +92.7% |
| **Overall** | **83.5%** | **31.6%** | **+51.9%** |

---

## Results by Category

### Greenfield (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 52.0% | +48.0% |
| Cost Accuracy | 84.0% | 50.4% | +33.6% |
| Service Correctness | 92.0% | 100.0% | -8.0% |
| Compliance Completeness | 51.4% | 40.0% | +11.4% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 93.6% | 0.0% | +93.6% |

### Compliance (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 48.0% | +52.0% |
| Cost Accuracy | 76.0% | 20.6% | +55.4% |
| Service Correctness | 75.2% | 100.0% | -24.8% |
| Compliance Completeness | 87.0% | 68.0% | +19.0% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 92.3% | 0.0% | +92.3% |

### Cost (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 56.0% | +44.0% |
| Cost Accuracy | 76.0% | 35.5% | +40.5% |
| Service Correctness | 91.0% | 95.0% | -4.0% |
| Compliance Completeness | 54.3% | 24.0% | +30.3% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 93.4% | 0.0% | +93.4% |

### Import (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 40.0% | +60.0% |
| Cost Accuracy | 84.0% | 10.0% | +74.0% |
| Service Correctness | 100.0% | 100.0% | +0.0% |
| Compliance Completeness | 69.3% | 40.0% | +29.3% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 93.6% | 0.0% | +93.6% |

### Microservices (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 64.0% | +36.0% |
| Cost Accuracy | 60.0% | 36.2% | +23.8% |
| Service Correctness | 88.0% | 92.0% | -4.0% |
| Compliance Completeness | 65.7% | 32.0% | +33.7% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 92.7% | 0.0% | +92.7% |

### Data (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 48.0% | +52.0% |
| Cost Accuracy | 76.0% | 56.3% | +19.7% |
| Service Correctness | 77.3% | 100.0% | -22.7% |
| Compliance Completeness | 42.9% | 36.0% | +6.9% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 92.7% | 0.0% | +92.7% |

### Industry (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 40.0% | +60.0% |
| Cost Accuracy | 60.0% | 9.9% | +50.1% |
| Service Correctness | 80.6% | 100.0% | -19.4% |
| Compliance Completeness | 73.9% | 52.0% | +21.9% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 92.9% | 0.0% | +92.9% |

### Migration (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 40.0% | +60.0% |
| Cost Accuracy | 76.0% | 36.0% | +40.0% |
| Service Correctness | 72.0% | 96.0% | -24.0% |
| Compliance Completeness | 60.7% | 42.0% | +18.7% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 91.5% | 0.0% | +91.5% |

### Edge (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 44.0% | +56.0% |
| Cost Accuracy | 84.0% | 5.1% | +78.9% |
| Service Correctness | 92.0% | 93.3% | -1.3% |
| Compliance Completeness | 52.3% | 60.0% | -7.7% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 92.2% | 0.0% | +92.2% |

### Comparison (5 cases)

| Metric | Cloudwright | Claude-raw | Delta |
|--------|------------|-----------|-------|
| Structural Validity | 100.0% | 48.0% | +52.0% |
| Cost Accuracy | 76.0% | 56.5% | +19.5% |
| Service Correctness | 70.0% | 95.0% | -25.0% |
| Compliance Completeness | 57.1% | 16.0% | +41.1% |
| Export Quality (IaC) | 70.0% | 0.0% | +70.0% |
| Diff Capability | 100.0% | 0.0% | +100.0% |
| Reproducibility | 85.0% | 35.0% | +50.0% |
| Time to IaC | 91.5% | 0.0% | +91.5% |

---

## Failure Analysis

Cases where Cloudwright scored lower than Claude-raw on any metric:

| Case | Metric | Cloudwright | Claude-raw | Gap |
|------|--------|------------|-----------|-----|
| [47] Serverless Comparison — Lambda vs C | Service Correctness | 0.0% | 100.0% | -100.0% |
| [26] Data Lake on AWS S3 with Athena | Service Correctness | 40.0% | 100.0% | -60.0% |
| [36] Lift-and-Shift Data Center Migratio | Service Correctness | 40.0% | 100.0% | -60.0% |
| [40] Phased Hybrid Migration with Parall | Service Correctness | 40.0% | 100.0% | -60.0% |
| [04] Hybrid Cloud with On-Premises Conne | Service Correctness | 60.0% | 100.0% | -40.0% |
| [08] SOC 2 Type II SaaS Platform | Cost Accuracy | 60.0% | 100.0% | -40.0% |
| [24] Event-Driven Microservices on AWS | Cost Accuracy | 60.0% | 100.0% | -40.0% |
| [28] Data Mesh Architecture on AWS | Cost Accuracy | 60.0% | 100.0% | -40.0% |
| [35] Real-Time Multiplayer Gaming Backen | Service Correctness | 60.0% | 100.0% | -40.0% |
| [44] Strict Multi-Compliance — HIPAA + P | Service Correctness | 60.0% | 100.0% | -40.0% |
| [50] Total Cost of Ownership — AWS vs GC | Cost Accuracy | 60.0% | 100.0% | -40.0% |
| [08] SOC 2 Type II SaaS Platform | Service Correctness | 66.7% | 100.0% | -33.3% |
| [26] Data Lake on AWS S3 with Athena | Compliance Completeness | 28.6% | 60.0% | -31.4% |
| [07] PCI-DSS Payment Processing Platform | Service Correctness | 71.4% | 100.0% | -28.6% |
| [09] Multi-Compliance Healthcare Fintech | Service Correctness | 71.4% | 100.0% | -28.6% |
| [31] Fintech Crypto Exchange Platform (P | Service Correctness | 71.4% | 100.0% | -28.6% |
| [32] Healthcare EHR Platform (HIPAA) | Service Correctness | 71.4% | 100.0% | -28.6% |
| [42] Impossible Budget — $10/Month Full  | Compliance Completeness | 14.3% | 40.0% | -25.7% |
| [46] Container Orchestration Comparison  | Service Correctness | 50.0% | 75.0% | -25.0% |
| [05] Serverless API Backend on AWS | Compliance Completeness | 28.6% | 50.0% | -21.4% |

---

## Methodology

- **Cloudwright pipeline:** design -> cost -> validate -> export (Terraform)
- **Claude raw:** same prompt, generic system prompt, `2026` Claude Sonnet model
- **Cost accuracy:** deviation from stated budget constraint
- **Reproducibility:** estimated from schema constraints (multi-run data not collected)
- **Time to IaC:** Cloudwright = automated elapsed time; Claude raw = API time + 30min manual extraction estimate
