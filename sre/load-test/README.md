# Load Testing — SRE Product Service

Нагрузочное тестирование выполняется с помощью [Locust](https://locust.io/).

---

## Prerequisites

```bash
pip install locust
```

---

## Запуск

### 1. Интерактивный режим (Web UI)

```bash
locust -f locustfile.py --host http://<EC2_PUBLIC_IP>:8000
```

Открой браузер: **http://localhost:8089**  
Задай параметры:
- **Number of users:** 200  
- **Spawn rate:** 10 users/sec  
- **Host:** уже заполнен из флага `--host`

---

### 2. Headless режим (CI / автоматика)

```bash
# Рамп-ап 10 → 200 пользователей, скорость 10/сек, длительность 5 мин
locust -f locustfile.py \
       --host http://<EC2_PUBLIC_IP>:8000 \
       --headless \
       -u 200 \
       -r 10 \
       --run-time 5m \
       --html report.html \
       --csv results
```

Результаты:
| Файл | Описание |
|---|---|
| `report.html` | HTML-отчёт с графиками |
| `results_stats.csv` | Агрегированная статистика |
| `results_failures.csv` | Ошибки |
| `results_history.csv` | Временной ряд по RPS / latency |

---

### 3. Распределённый режим (master + workers)

```bash
# На мастер-машине
locust -f locustfile.py --master --host http://<EC2_PUBLIC_IP>:8000

# На каждой worker-машине
locust -f locustfile.py --worker --master-host <MASTER_IP>
```

---

## Сценарии нагрузки

| Task | Weight | Описание |
|---|---|---|
| `GET /health` | 1 | Liveness probe |
| `GET /products` | 5 | Просмотр каталога |
| `POST /products` | 2 | Создание продукта |
| `GET /products/:id` | 3 | Карточка продукта |
| `GET /products/bad-id` | 1 | 404 путь |

**Итого:** ~9 единиц → `/products` ≈ 55% трафика, `/products/:id` ≈ 33%.

---

## Целевые показатели (согласно SLO)

| Метрика | Цель |
|---|---|
| p99 latency | < 300 ms |
| Error rate | < 0.1 % |
| Availability | ≥ 99.9 % |

---

## Интерпретация результатов

1. **RPS ≥ 100** при 200 пользователях — нормальная производительность.
2. **p99 > 300 ms** — превышение SLO по latency, нужна оптимизация.
3. **Failures > 0.1%** — нарушение SLO по ошибкам, немедленная диагностика.
4. **ASG scale-out** — должен сработать при CPU > 70% (проверь CloudWatch).
