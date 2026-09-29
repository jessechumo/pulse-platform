# pulse-platform

A small Python service run like a real production system: deployed, monitored, load-tested, broken on purpose, and documented. The app stays simple; the infrastructure and operations around it are the point.

## Status

FastAPI service with health/readiness checks against real Postgres/Redis, structured JSON logging, Prometheus metrics, and a Jobs API (`POST /jobs`, `GET /jobs/{id}`) backed by an Alembic-migrated Postgres schema. An arq worker processes queued jobs against Redis.

## Repo layout

```
app/          FastAPI service
tests/        Unit tests
k8s/          Kubernetes manifests / Helm chart
terraform/    AWS infrastructure as code (VPC, EKS/ECS, RDS)
loadtest/     Locust load tests and chaos experiments
docs/         Architecture diagram, runbooks, postmortems
```

`terraform/`, `loadtest/`, and `docs/` come as the roadmap progresses.

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload
```

```bash
curl localhost:8000/health
curl localhost:8000/ready
curl localhost:8000/metrics
```

```bash
pytest -m "not integration"   # fast, no external services
pytest                         # full suite, needs postgres/redis up
```

```bash
docker build -t pulse-platform .
docker run -p 8000:8000 pulse-platform
```

## Running with Docker Compose

```bash
docker compose up --build
```

To run the app on the host against the containers' Postgres/Redis:

```bash
docker compose up -d postgres redis
cp .env.example .env
uvicorn app.main:app --reload
```

## Database migrations

Schema changes go through Alembic, not `create_all()`. With Postgres up:

```bash
alembic upgrade head
```

New migration after changing a model:

```bash
alembic revision --autogenerate -m "describe the change"
```

## Running on Kubernetes (kind)

```bash
kind create cluster --config k8s/kind/kind-config.yaml
docker build -t pulse-platform:dev .
kind load docker-image pulse-platform:dev --name pulse-platform
kubectl apply -f k8s/
```

Ingress and HPA follow.

## Design notes

- `/health` and `/ready` are separate: liveness vs. readiness, so Kubernetes can pull a pod out of rotation without restarting it.
- JSON logs to stdout only; log collection is the platform's job, not the app's.
- Prometheus metrics are keyed by route template, not raw path, to bound label cardinality.
- Config is typed via `pydantic-settings`, `PULSE_`-prefixed env vars.
- Schema changes are Alembic migrations, not `create_all()`.
- API and worker share only a queue contract (a job id, a function name), not code -- they're separate processes, deployed and scaled independently.
