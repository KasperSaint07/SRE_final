# Scaling Strategy — SRE Product Service

## Philosophy

We follow the **scale-out first** principle: add more instances before scaling up (vertical scaling). This keeps individual instance cost low and aligns with AWS pricing models for burstable `t3` instances.

---

## Current Setup

| Parameter | Value |
|---|---|
| Instance type | t3.micro (2 vCPU, 1 GB RAM) |
| ASG min | 1 |
| ASG max | 3 |
| ASG desired | 1 |
| Scale-out trigger | CPU > 70% for 2 min |
| Scale-in trigger | CPU < 30% for 5 min |

---

## Scaling Triggers

### Horizontal Scale-Out (ASG)

**When:** `CPUUtilization > 70%` for 2 consecutive 1-minute periods.

**Why CPU?** For this FastAPI service, CPU is the primary bottleneck. The in-memory data store means there's no database latency, so CPU consumption directly reflects request processing load.

**Process:**
1. CloudWatch alarm `sre-final-cpu-high` fires.
2. ASG Scale-Out policy adds 1 instance (cooldown: 120s).
3. Launch Template provisions new EC2 with `user-data.sh`.
4. New instance starts Docker stack (requires CI/CD re-deploy or manual trigger).

**Cool-down:** 120 seconds — prevents oscillation during rapid traffic spikes.

### Horizontal Scale-In

**When:** `CPUUtilization < 30%` for 5 consecutive 1-minute periods.

**Why 5 periods?** Scale-in is conservative (5 min vs 2 min for scale-out) to avoid thrashing — rapidly removing then re-adding instances during bursty traffic.

**Cool-down:** 300 seconds — longer to ensure the metric is stable.

---

## Scaling Thresholds Rationale

| Metric | Threshold | Rationale |
|---|---|---|
| CPU scale-out | 70% | Leaves 30% headroom for a traffic spike before adding capacity |
| CPU scale-in | 30% | Well below steady-state (≈50%); ensures we don't scale in too eagerly |
| Scale-in periods | 5 × 1 min | Conservative — prevents thrash during bursty but short-lived traffic |

---

## Vertical Scaling (when to upgrade instance type)

Move to a larger instance when:
- p99 latency exceeds SLO **even at low RPS** (< 50 req/s).
- Memory usage consistently > 80% (`process_resident_memory_bytes`).
- CPU credits exhausted on t3.micro (check `CPUCreditBalance` metric).

**Upgrade path:**  
`t3.micro` → `t3.small` → `t3.medium` → `t3.large`

To apply: update `ec2_instance_type` in `terraform.tfvars` and run `terraform apply`.

---

## Future Scaling Improvements

| Improvement | When to implement |
|---|---|
| Application Load Balancer | When running > 1 instance concurrently |
| Target Tracking Scaling (ALBRequestCountPerTarget) | When ALB is added — more accurate than CPU |
| Predictive Scaling | When traffic patterns are predictable (e.g., business hours) |
| Multi-region active-passive | When SLO requires > 99.95% availability |
| Read replicas / caching (Redis) | When adding a real database |

---

## Capacity Planning

At **t3.micro** with 2 uvicorn workers:

| Scenario | Estimated RPS | CPU% | Action |
|---|---|---|---|
| Normal traffic | 0–30 | 10–30% | Scale-in possible |
| Moderate load | 30–80 | 30–60% | Steady state |
| High load | 80–150 | 60–80% | Scale-out triggered |
| Overload | > 150 | > 80% | Max ASG capacity reached |

These numbers are estimates — validate with load tests (`sre/load-test/locustfile.py`).
