# pulse-platform

A small Python service, run like a real production system: deployed, monitored, load-tested, broken on purpose, and documented.

The application itself stays simple on purpose. The point of this repo is everything around it: containers, Kubernetes, CI/CD, observability with SLOs, load and chaos testing, infrastructure as code, and the operational docs (runbooks, postmortems) that go with running a service for real.

## Status

FastAPI service with health/readiness endpoints (checking real Postgres/Redis connectivity), structured JSON logging, Prometheus metrics, and a Jobs API (`POST /jobs`, `GET /jobs/{id}`) backed by Postgres via Alembic-migrated schema. Jobs are enqueued onto Redis via arq but nothing consumes the queue yet -- the worker is next, so a created job stays `queued` forever for now.

## Repo layout

```
app/            FastAPI service (this is the only thing that exists so far)
tests/          Unit tests
k8s/            Kubernetes manifests / Helm chart (kind or k3d locally)      [planned]
terraform/      AWS infrastructure as code (VPC, EKS/ECS, RDS)              [planned]
loadtest/       Locust load tests and chaos experiments                     [planned]
docs/           Architecture diagram, runbooks, postmortems                 [planned]
```

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload
```

Then:

```bash
curl localhost:8000/health    # liveness
curl localhost:8000/ready     # readiness
curl localhost:8000/metrics   # Prometheus exposition format
```

Run the tests:

```bash
pytest
```

Build and run the container:

```bash
docker build -t pulse-platform .
docker run -p 8000:8000 pulse-platform
```

## Running with Docker Compose

Brings up the app alongside Postgres and Redis, networked together:

```bash
docker compose up --build
```

To run the app directly on the host (e.g. `uvicorn --reload` for fast iteration) while still using the Postgres/Redis containers, start just the dependencies and point the app at their published ports:

```bash
docker compose up -d postgres redis
cp .env.example .env
uvicorn app.main:app --reload
```

## Database migrations

Schema changes are managed with Alembic rather than `Base.metadata.create_all()`, matching how this would run in production. With Postgres up (`docker compose up -d postgres`):

```bash
alembic upgrade head
```

To create a new migration after changing a model in `app/models/`:

```bash
alembic revision --autogenerate -m "describe the change"
```

## Design decisions

- **`/health` vs `/ready`** — separate liveness and readiness probes, matching Kubernetes conventions. `/health` says the process is alive; `/ready` says it can serve traffic. They're identical today since there are no external dependencies yet, but `/ready` is where DB/Redis connectivity checks will go so Kubernetes can pull a pod out of rotation without restarting it.
- **JSON logs to stdout** — no log files, no log shipping agent baked into the app. In production, something at the platform layer (Fluent Bit, Vector, CloudWatch agent) is responsible for collecting stdout, not the app itself. Uvicorn's own loggers are rerouted through the same JSON formatter so access logs and app logs share one shape.
- **Prometheus metrics keyed by route template, not raw path** — `/items/{id}` rather than `/items/42`. Keying by the concrete path would let path parameters blow up label cardinality, which is a common way to accidentally overload Prometheus.
- **Settings via `pydantic-settings`, `PULSE_`-prefixed env vars** — one typed source of truth for config, validated at startup instead of failing on first use.
- **Alembic migrations instead of `create_all()`** — every schema change is a reviewable, ordered, revertible file. `create_all()` is fine for a demo script; it has no story for altering a column in a table that already has data in it.
- **`POST /jobs` enqueues to Redis before any worker exists to consume it** — the API and the worker are separate processes that only share a queue contract (a job id, a function name), not a shared codebase state. That's deliberate: it's the same decoupling a real producer/consumer deploy relies on, where the API can ship and start accepting jobs before the worker fleet is scaled up.
