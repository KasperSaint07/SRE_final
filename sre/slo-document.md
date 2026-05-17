# Service Level Objectives — SRE Product Service

**Version:** 1.0.0  
**Owner:** SRE Team  
**Last updated:** 2025-01-01  
**Review cadence:** Quarterly

---

## 1. Service Overview

The **SRE Product Service** is the e-commerce product catalog microservice that powers product listing, creation, and retrieval. It is a critical revenue-path service — any unavailability or latency degradation directly impacts the customer experience and business metrics.

---

## 2. SLIs — Service Level Indicators

SLIs are quantitative measures of the service health. We measure them from the **server side** using Prometheus metrics.

### 2.1 Availability SLI

> **Definition:** The fraction of well-formed HTTP requests that return a successful response (non-5xx).

```
Availability = (total_requests - 5xx_errors) / total_requests
```

**Prometheus expression:**
```promql
(
  sum(rate(http_requests_total[5m]))
  -
  sum(rate(http_requests_errors_total{status_code=~"5.."}[5m]))
)
/
sum(rate(http_requests_total[5m]))
```

**Exclusions:** Requests returning 4xx are **not** counted as errors for the availability SLI (they represent client errors, not service failures).

---

### 2.2 Latency SLI

> **Definition:** The proportion of requests that are served within the latency threshold.

| Percentile | Threshold |
|-----------|-----------|
| p50        | < 100 ms  |
| p95        | < 200 ms  |
| p99        | < 300 ms  |

**Prometheus expression (p99):**
```promql
histogram_quantile(
  0.99,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)
```

---

### 2.3 Error Rate SLI

> **Definition:** The ratio of 5xx responses to total requests over a rolling window.

```
Error Rate = 5xx_responses / total_responses
```

**Prometheus expression:**
```promql
sum(rate(http_requests_errors_total{status_code=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
```

---

## 3. SLOs — Service Level Objectives

| SLI            | Target         | Measurement Window |
|---------------|----------------|--------------------|
| Availability   | **≥ 99.9 %**   | Rolling 30 days    |
| Latency p99    | **< 300 ms**   | Rolling 30 days    |
| Error Rate     | **< 0.1 %**    | Rolling 30 days    |

These SLOs represent a balance between business needs and engineering cost. They are deliberately set below 100% to leave room for planned maintenance and routine deployments.

---

## 4. Error Budget

### 4.1 Calculation

The **error budget** is the allowed amount of unreliability within the SLO window.

| SLO          | Allowed failures per 30 days |
|-------------|------------------------------|
| Availability 99.9% | **0.1% ≈ 43.8 minutes** of downtime |
| Error Rate 0.1%    | **0.1%** of all requests may be 5xx |

```
Monthly error budget (minutes) = 30d × 24h × 60min × (1 - 0.999) = 43.2 min
```

### 4.2 Error Budget Tracking

The remaining budget is calculated as:

```promql
# Remaining error budget (%)
(
  1 - (
    sum(increase(http_requests_errors_total{status_code=~"5.."}[30d]))
    /
    sum(increase(http_requests_total[30d]))
  ) / 0.001
) * 100
```

---

## 5. Error Budget Policy

### 5.1 Normal (budget > 50% remaining)

- Deployments proceed at normal cadence.
- Feature development continues unimpeded.
- SRE focuses on reliability improvements and automation.

### 5.2 Caution (budget 10–50% remaining)

- All non-critical deployments require **SRE sign-off**.
- Feature work that introduces risk is paused.
- A postmortem is required for any new incident.
- Weekly reliability reviews start.

### 5.3 Critical (budget < 10% remaining)

- **Feature freeze** — only bug-fixes and reliability patches.
- Every deployment requires full rollback plan + SRE approval.
- Daily SRE stand-up with engineering leadership.
- Architecture review for problematic components.
- Customer communication plan activated if SLO is breached.

### 5.4 SLO Breach (budget exhausted)

- Incident automatically created and assigned to on-call.
- `HighErrorRate` or `InstanceDown` alert fires (see alert-rules.yml).
- Executive escalation within 30 minutes of breach.
- Mandatory retrospective within 48 hours.
- SLO targets reviewed and potentially renegotiated.

---

## 6. Review Process

- **Weekly:** Check error budget burn rate in Grafana.
- **Monthly:** Compare actual SLI vs SLO; update the error budget ledger.
- **Quarterly:** Full SLO review with engineering and product; adjust targets if needed.
- **Post-incident:** Assess impact on error budget; adjust policies accordingly.
