# Architecture — SRE Product Service

## Overview

The system follows a **single-host containerised monolith** pattern for the course project, while the infrastructure layer is designed to scale horizontally via AWS Auto Scaling Group when load demands it.

---

## Components

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Cloud (us-east-1)                │
│                                                             │
│  ┌──── VPC (10.0.0.0/16) ──────────────────────────────┐   │
│  │                                                      │   │
│  │  AZ-1 (us-east-1a)        AZ-2 (us-east-1b)        │   │
│  │  ┌────────────────┐       ┌────────────────┐        │   │
│  │  │ Public Subnet  │       │ Public Subnet  │        │   │
│  │  │ 10.0.1.0/24   │       │ 10.0.2.0/24   │        │   │
│  │  │                │       │                │        │   │
│  │  │  ┌──────────┐  │       │  ASG instance  │        │   │
│  │  │  │  EC2     │  │       │  (scale-out)   │        │   │
│  │  │  │ t3.micro │  │       │                │        │   │
│  │  │  │          │  │       └────────────────┘        │   │
│  │  │  │ Docker   │  │                                  │   │
│  │  │  │ Compose  │  │                                  │   │
│  │  │  └──────────┘  │                                  │   │
│  │  └────────────────┘                                  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  Auto Scaling Group (min=1, max=3, desired=1)│   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │    ECR     │   │  CloudWatch  │   │  S3 (TF state)   │  │
│  │ (images)   │   │  (alarms)    │   │  DynamoDB (lock) │  │
│  └────────────┘   └──────────────┘   └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Container Stack (inside EC2)

```
EC2 Host (Docker)
│
├── fastapi-app:8000
│   ├── GET /health
│   ├── GET /products
│   ├── POST /products
│   ├── GET /products/{id}
│   └── GET /metrics  ←── Prometheus scrapes here
│
├── prometheus:9090
│   ├── scrapes fastapi-app:8000/metrics every 15s
│   ├── evaluates alert-rules.yml
│   └── sends alerts → alertmanager:9093
│
├── grafana:3000
│   ├── datasource: prometheus:9090 (auto-provisioned)
│   ├── app-dashboard.json (auto-provisioned)
│   └── infra-dashboard.json (auto-provisioned)
│
└── alertmanager:9093
    └── routes alerts → webhook / email
```

---

## Data Flow

### 1. Request Path
```
Internet → Security Group → EC2:8000 → FastAPI (uvicorn)
                                          │
                                    In-memory dict
                                    (products store)
```

### 2. Metrics Path
```
FastAPI /metrics ──(scrape every 15s)──► Prometheus
                                              │
                                    evaluate alert rules
                                              │
                                     ┌────────┴────────┐
                                     │                 │
                                Grafana           Alertmanager
                              (visualise)       (notify team)
```

### 3. CI/CD Path
```
git push main
     │
     ▼
GitHub Actions
     │
     ├── Job 1: pytest (test)
     ├── Job 2: docker build + push → ECR
     └── Job 3: SSH → EC2 → docker compose pull + up
```

### 4. Auto-scaling Path
```
CPU > 70% for 2 minutes
     │
     ▼
CloudWatch Alarm (cpu_high)
     │
     ▼
ASG Scale-Out Policy → Launch Template → New EC2 instance
     │
     ▼
user-data.sh: install Docker + Docker Compose
     │
     ▼
Manual or CI trigger: docker compose up on new instance
```

---

## Security Design

| Control | Implementation |
|---|---|
| Network isolation | VPC with Security Groups (principle of least privilege) |
| SSH access | Key-pair authentication; restrict `allowed_ssh_cidr` in prod |
| Container user | Non-root (`app` user in Dockerfile) |
| Image scanning | ECR scan-on-push + Trivy in CI |
| Secrets | GitHub Secrets (CI) + environment variables (runtime) |
| State encryption | S3 backend with AES256 encryption |
| TF state locking | DynamoDB prevents concurrent apply |
| IAM | EC2 role with minimum permissions (ECR read-only + CloudWatch) |

---

## Reliability Design

| Mechanism | Details |
|---|---|
| Health checks | Docker HEALTHCHECK + `/health` endpoint |
| Restart policy | `restart: always` for all containers |
| Auto-recovery | ASG replaces failed instances automatically |
| Observability | Prometheus + Grafana + Alertmanager |
| Alerting | 3 alerts: HighErrorRate, HighLatency, InstanceDown |
| Error budget | 99.9% availability SLO = 43 min/month budget |
| Runbook | Documented for every alert |
