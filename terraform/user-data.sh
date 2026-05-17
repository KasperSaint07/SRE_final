#!/bin/bash
set -euo pipefail

# ── System update ─────────────────────────────────────────────────────────────
dnf update -y

# ── Docker ────────────────────────────────────────────────────────────────────
dnf install -y docker
systemctl enable --now docker
usermod -aG docker ec2-user

# ── Docker Compose (standalone binary) ────────────────────────────────────────
COMPOSE_VERSION="2.27.0"
curl -SL "https://github.com/docker/compose/releases/download/v${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
    -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# ── AWS CLI (already on AL2023, but ensure latest) ────────────────────────────
dnf install -y aws-cli

# ── Create app directory ──────────────────────────────────────────────────────
APP_DIR="/opt/sre-app"
mkdir -p "${APP_DIR}/monitoring/prometheus"
mkdir -p "${APP_DIR}/monitoring/grafana/provisioning/datasources"
mkdir -p "${APP_DIR}/monitoring/grafana/provisioning/dashboards"
mkdir -p "${APP_DIR}/monitoring/grafana/dashboards"
mkdir -p "${APP_DIR}/monitoring/alertmanager"

chown -R ec2-user:ec2-user "${APP_DIR}"

# ── Signal that user-data completed ──────────────────────────────────────────
touch /var/lib/cloud/instance/user-data-complete
echo "User-data bootstrap complete at $(date)" >> /var/log/user-data.log
