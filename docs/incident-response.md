# Incident Response Plan — SRE Product Service

**Version:** 1.0.0  
**Owner:** SRE Team  
**Review cadence:** After every P1/P2 incident; quarterly otherwise

---

## Severity Levels

| Level | Definition | Response Time | Examples |
|---|---|---|---|
| **P1 — Critical** | Service unavailable or data loss | < 5 min | InstanceDown, Error Rate > 10% |
| **P2 — High** | Significant degradation, SLO at risk | < 15 min | HighLatency, Error Rate 5–10% |
| **P3 — Medium** | Partial degradation, SLO not yet breached | < 1 hour | Elevated latency, single endpoint errors |
| **P4 — Low** | Minor issues, no customer impact | Next business day | Dashboard broken, alert misfiring |

---

## Incident Response Lifecycle

```
Detection → Triage → Contain → Investigate → Resolve → Postmortem
```

---

## Phase 1: Detection

Incidents are detected via:

1. **Automated alerting** — Alertmanager → PagerDuty / Slack `#sre-alerts`
2. **Grafana dashboards** — manual monitoring during business hours
3. **Customer report** — support ticket escalated to SRE
4. **CI/CD failure** — deploy job fails, health check doesn't pass

**Alert to Runbook mapping:**

| Alert | Runbook Section |
|---|---|
| HighErrorRate | [sre/runbook.md#higherrorrate](../sre/runbook.md) |
| HighLatency | [sre/runbook.md#highlatency](../sre/runbook.md) |
| InstanceDown | [sre/runbook.md#instancedown](../sre/runbook.md) |

---

## Phase 2: Triage (< 5 min)

On-call engineer must answer within 5 minutes:

1. **Acknowledge** the alert in PagerDuty.
2. Open Grafana and check:
   - Is the service fully down or degraded?
   - Which endpoints are affected?
   - What is the current error rate and latency?
3. **Declare severity** (P1/P2/P3) and post to `#sre-incident`:
   ```
   🚨 [P1 INCIDENT] InstanceDown — fastapi-app container not responding
   Declared: 2025-01-01 14:32 UTC
   On-call: @your-name
   Status: Investigating
   ```

---

## Phase 3: Contain (minimize blast radius)

**For P1 incidents (service down):**
```bash
# Option 1: Restart the container
docker compose restart fastapi-app

# Option 2: Roll back to last known good image
ECR_REGISTRY=<registry>
IMAGE_TAG=<previous-sha>
ECR_REGISTRY=$ECR_REGISTRY ECR_REPOSITORY=sre-final-app IMAGE_TAG=$IMAGE_TAG \
  docker compose up -d fastapi-app

# Option 3: Scale out ASG (add capacity)
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name sre-final-asg --desired-capacity 2
```

**For P2 incidents (latency/errors):**
```bash
# Reduce load if possible (rate limiting via iptables)
iptables -A INPUT -p tcp --dport 8000 -m connlimit \
  --connlimit-above 200 -j REJECT --connlimit-mask 0
```

---

## Phase 4: Investigate (root cause analysis)

Follow the 5-Why method:

```
Why is the service returning errors?
  → Because the container crashed.
Why did the container crash?
  → Because it ran out of memory.
Why did it run out of memory?
  → Because a recent deploy introduced a memory leak.
Why wasn't this caught?
  → No memory usage alert exists.
Why doesn't the alert exist?
  → Action item: add memory alert.
```

**Diagnostic commands:**
```bash
# Container logs
docker logs fastapi-app --since=30m

# Host metrics
top -bn1; free -m; df -h

# Network
ss -tulnp | grep 8000

# Recent deploys
docker inspect fastapi-app --format='{{.Config.Image}}'
```

---

## Phase 5: Resolve

1. Apply fix (restart / rollback / scale).
2. Verify service health:
   ```bash
   curl -s http://localhost:8000/health | python3 -m json.tool
   ```
3. Confirm metrics normalised in Grafana (error rate back to < 0.1%).
4. Resolve alert in PagerDuty.
5. Post resolution to Slack:
   ```
   ✅ [RESOLVED] P1 Incident — fastapi-app restored
   Duration: 18 minutes
   Impact: ~1,800 failed requests
   Root cause: OOM kill after deploy, rolling back fixed it
   Postmortem: scheduled for 2025-01-03
   ```

---

## Phase 6: Postmortem

**Blameless postmortem** must be completed within **48 hours** for P1/P2.

### Template

```markdown
## Incident Postmortem — YYYY-MM-DD — [Alert Name]

**Incident commander:** @name
**Duration:** HH:MM
**Severity:** P1/P2/P3
**Customer impact:** X requests failed / Y minutes of downtime

### Timeline
| Time (UTC) | Event |
|---|---|
| 14:32 | Alert fired |
| 14:35 | On-call acknowledged |
| 14:40 | Root cause identified |
| 14:50 | Fix applied |
| 14:52 | Service restored |

### Root Cause
[One paragraph describing the root cause]

### Impact
- Error budget consumed: X minutes / Y% of monthly budget
- Requests affected: ~N

### What went well
- Fast detection (alert fired within 60s)
- Rollback was clean

### What went wrong
- No memory limit on container
- Rollback documentation wasn't up to date

### Action Items
| Action | Owner | Due date |
|---|---|---|
| Add container memory limit | @dev | 2025-01-08 |
| Update rollback runbook | @sre | 2025-01-05 |
| Add memory alert | @sre | 2025-01-08 |
```

---

## Communication Plan

| Stakeholder | Channel | When |
|---|---|---|
| SRE team | Slack `#sre-incident` | Immediately |
| Engineering | Slack `#engineering` | P1: immediately; P2: within 15 min |
| Management | Email / Slack DM | P1: within 30 min |
| Customers | Status page + email | P1 > 15 min downtime |

---

## On-Call Responsibilities

- Respond to PagerDuty within **5 minutes**.
- Follow the runbook for the fired alert.
- Escalate if not resolved within the SLA.
- Document the incident timeline in real-time.
- Create postmortem after resolution.
- Ensure action items are tracked in GitHub Issues.
