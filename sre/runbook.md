# Runbook — SRE Product Service

**Owner:** SRE Team  
**Severity Levels:** P1 (Critical) · P2 (High) · P3 (Medium)  
**On-call rotation:** PagerDuty → Slack `#sre-oncall`

---

## Быстрый доступ

| Сервис | URL |
|---|---|
| Grafana | `http://<EC2_IP>:3000` |
| Prometheus | `http://<EC2_IP>:9090` |
| Alertmanager | `http://<EC2_IP>:9093` |
| FastAPI | `http://<EC2_IP>:8000` |
| SSH | `ssh -i ~/.ssh/key.pem ec2-user@<EC2_IP>` |

---

## Alert 1: HighErrorRate

**Severity:** P1 (Critical)  
**Condition:** HTTP 5xx error rate > 5% за 5 минут  
**SLO Impact:** Прямое нарушение Error Rate SLO (0.1%)

### Шаги диагностики

**Шаг 1 — Подтверди алерт в Grafana**
```
Grafana → SRE Final → FastAPI Application Dashboard → панель "Error Rate (%)"
```
Убедись, что рост реальный, а не артефакт (спайк без продолжения).

**Шаг 2 — Проверь логи приложения**
```bash
ssh -i ~/.ssh/key.pem ec2-user@<EC2_IP>
docker logs fastapi-app --tail=200 --since=10m
```
Ищи: `Exception`, `Error`, `Traceback`, `500`, `503`.

**Шаг 3 — Проверь состояние контейнеров**
```bash
docker compose ps
docker stats --no-stream
```

**Шаг 4 — Проверь ресурсы хоста**
```bash
top -bn1 | head -20
df -h
free -m
```

**Шаг 5 — Запроси статистику ошибок в Prometheus**
```promql
# Разбивка ошибок по endpoint
sum by (endpoint, status_code)(
  rate(http_requests_errors_total[5m])
)
```

### Шаги восстановления

**Вариант A — Рестарт приложения**
```bash
docker compose restart fastapi-app
# Убедиться, что статус healthy
docker inspect fastapi-app --format='{{.State.Health.Status}}'
```

**Вариант B — Откат на предыдущий образ**
```bash
# Найти предыдущий tag в ECR
aws ecr describe-images --repository-name sre-final-app \
  --query 'sort_by(imageDetails,& imagePushedAt)[-2].imageTags[0]' \
  --output text

# Откатить
ECR_REGISTRY=<registry_url>
PREV_TAG=<previous_tag>
docker compose pull fastapi-app  # с предыдущим тегом
ECR_REGISTRY=$ECR_REGISTRY ECR_REPOSITORY=sre-final-app IMAGE_TAG=$PREV_TAG \
  docker compose up -d fastapi-app
```

**Вариант C — Перезапуск всего стека**
```bash
cd /opt/sre-app
docker compose down
docker compose up -d
```

### Эскалация
- Если не решено за **15 минут** → эскалация на Tech Lead.
- Если не решено за **30 минут** → CTO уведомление + клиентская коммуникация.

---

## Alert 2: HighLatency

**Severity:** P2 (High)  
**Condition:** p99 latency > 500 ms за 5 минут  
**SLO Impact:** Нарушение Latency SLO (p99 < 300 ms)

### Шаги диагностики

**Шаг 1 — Подтверди в Grafana**
```
FastAPI Application Dashboard → панель "Latency p50 / p95 / p99"
```

**Шаг 2 — Определи медленные эндпоинты**
```promql
# p99 latency по каждому endpoint
histogram_quantile(
  0.99,
  sum by (le, endpoint)(rate(http_request_duration_seconds_bucket[5m]))
)
```

**Шаг 3 — Проверь нагрузку на хост**
```bash
ssh -i ~/.ssh/key.pem ec2-user@<EC2_IP>
top -bn1
# Проверь CPU steal (у t3.micro есть CPU credit burst)
cat /proc/stat | head -1
```

**Шаг 4 — Проверь CPU credits (t3.micro/t3.small)**
```bash
# В AWS Console: EC2 → Monitoring → CPU Credit Balance
# Если credits исчерпаны → t3 throttles до baseline CPU
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUCreditBalance \
  --dimensions Name=InstanceId,Value=<INSTANCE_ID> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average
```

**Шаг 5 — Проверь текущий RPS**
```promql
sum(rate(http_requests_total[1m]))
```

### Шаги восстановления

**Вариант A — Горизонтальное масштабирование (если ASG настроен)**
```bash
# Принудительный scale-out
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name sre-final-asg \
  --desired-capacity 2
```

**Вариант B — Upgrade инстанса**
```bash
# Terraform: изменить ec2_instance_type = "t3.small" → "t3.medium"
# затем: terraform apply -target=aws_instance.app
```

**Вариант C — Throttle входящий трафик (временная мера)**
```bash
# Ограничить новые подключения через iptables
iptables -A INPUT -p tcp --dport 8000 -m connlimit \
  --connlimit-above 500 -j REJECT
```

### Эскалация
- Если не решено за **20 минут** → эскалация на Platform Team.

---

## Alert 3: InstanceDown

**Severity:** P1 (Critical)  
**Condition:** Prometheus не может собрать метрики с target'а > 1 минуты  
**SLO Impact:** Прямое нарушение Availability SLO (99.9%)

### Шаги диагностики

**Шаг 1 — Определи, какой target упал**
```
Prometheus UI → Status → Targets
```
или:
```promql
up == 0
```

**Шаг 2 — Если упало fastapi-app**
```bash
ssh -i ~/.ssh/key.pem ec2-user@<EC2_IP>
docker compose ps
docker logs fastapi-app --tail=100
```

**Шаг 3 — Если EC2 недоступен по SSH**
```bash
# Проверь статус в AWS Console / CLI
aws ec2 describe-instance-status --instance-ids <INSTANCE_ID>

# Проверь System Status Check и Instance Status Check
aws ec2 describe-instance-status \
  --instance-ids <INSTANCE_ID> \
  --query 'InstanceStatuses[0].{System:SystemStatus.Status,Instance:InstanceStatus.Status}'
```

**Шаг 4 — Проверь Security Group**
```bash
# Убедись, что порт 8000 открыт
aws ec2 describe-security-groups \
  --group-ids <SG_ID> \
  --query 'SecurityGroups[0].IpPermissions'
```

### Шаги восстановления

**Вариант A — Рестарт контейнера**
```bash
docker compose restart fastapi-app
```

**Вариант B — Рестарт EC2 инстанса**
```bash
aws ec2 reboot-instances --instance-ids <INSTANCE_ID>
# Подождать ~2 минуты
aws ec2 wait instance-running --instance-ids <INSTANCE_ID>
```

**Вариант C — Запустить новый инстанс через ASG**
```bash
# Пометить текущий инстанс как Unhealthy → ASG запустит замену
aws autoscaling set-instance-health \
  --instance-id <INSTANCE_ID> \
  --health-status Unhealthy

# Увеличить desired capacity
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name sre-final-asg \
  --desired-capacity 2
```

**Вариант D — Создать новый инстанс вручную (крайний случай)**
```bash
cd terraform/
terraform apply -target=aws_instance.app
```

### Эскалация
- **Немедленно** → уведомить всю команду SRE.
- Если недоступно более **5 минут** → уведомить CTO.
- Если недоступно более **15 минут** → активировать план аварийного восстановления.

---

## Общие команды диагностики

```bash
# Состояние всего стека
docker compose ps

# Потребление ресурсов контейнерами
docker stats --no-stream

# Логи всех сервисов одновременно
docker compose logs --tail=50 -f

# Проверить health всех контейнеров
docker inspect $(docker ps -q) --format='{{.Name}}: {{.State.Health.Status}}'

# Посмотреть метрики напрямую
curl -s http://localhost:8000/metrics | grep http_requests

# Перезапустить весь стек
cd /opt/sre-app && docker compose down && docker compose up -d
```

---

## Post-Incident Checklist

- [ ] Инцидент закрыт, сервис работает нормально
- [ ] Timeline инцидента задокументирован
- [ ] Root cause определён
- [ ] Метрики SLO проверены (error budget consumption)
- [ ] Blameless postmortem запланирован (в течение 48ч)
- [ ] Action items созданы в Jira/GitHub Issues
- [ ] Runbook обновлён (если нужно)
