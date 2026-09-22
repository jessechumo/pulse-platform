# pulse-platform

A small Python service, run like a real production system: deployed, monitored, load-tested, broken on purpose, and documented.

The application itself stays simple on purpose. The point of this repo is everything around it: containers, Kubernetes, CI/CD, observability with SLOs, load and chaos testing, infrastructure as code, and the operational docs (runbooks, postmortems) that go with running a service for real.

## Status

Step 1 in progress: FastAPI service skeleton with health/readiness endpoints, structured JSON logging, and Prometheus metrics. No database or background worker yet.

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

## Design decisions

- **`/health` vs `/ready`** — separate liveness and readiness probes, matching Kubernetes conventions. `/health` says the process is alive; `/ready` says it can serve traffic. They're identical today since there are no external dependencies yet, but `/ready` is where DB/Redis connectivity checks will go so Kubernetes can pull a pod out of rotation without restarting it.
- **JSON logs to stdout** — no log files, no log shipping agent baked into the app. In production, something at the platform layer (Fluent Bit, Vector, CloudWatch agent) is responsible for collecting stdout, not the app itself. Uvicorn's own loggers are rerouted through the same JSON formatter so access logs and app logs share one shape.
- **Prometheus metrics keyed by route template, not raw path** — `/items/{id}` rather than `/items/42`. Keying by the concrete path would let path parameters blow up label cardinality, which is a common way to accidentally overload Prometheus.
- **Settings via `pydantic-settings`, `PULSE_`-prefixed env vars** — one typed source of truth for config, validated at startup instead of failing on first use.
