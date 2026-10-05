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

# ingress-nginx, kind's own install variant -- check for a newer release tag
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.3/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller --timeout=120s

docker build -t pulse-platform:dev .
kind load docker-image pulse-platform:dev --name pulse-platform
kubectl apply -f k8s/

curl localhost/health
```

The HPAs need `metrics-server`, which kind doesn't ship by default. Its kubelet certs also aren't signed in a way metrics-server trusts out of the box, so it needs `--kubelet-insecure-tls` -- fine on a local kind cluster, not something to carry into a real one:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl get hpa -n pulse
```

## Running with Helm

Same manifests, packaged as a chart (`k8s/helm/pulse-platform`), parameterized via `values.yaml` instead of hardcoded image tags, replica bounds, and credentials. Needs the same cluster prep above (kind cluster, ingress-nginx, metrics-server):

```bash
helm install pulse k8s/helm/pulse-platform --namespace pulse --create-namespace
```

Override anything in `values.yaml` with `--set` or `-f`, e.g. a different image tag:

```bash
helm upgrade pulse k8s/helm/pulse-platform --namespace pulse --set image.tag=v1.2.3
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push and PR: `ruff check` in its own job, the full `pytest` suite (including the integration tests, against real Postgres/Redis service containers) in another, then builds the Docker image and scans it with Trivy once both pass.

## Observability

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install observability prometheus-community/kube-prometheus-stack \
  --namespace observability --create-namespace \
  -f k8s/observability/kube-prometheus-stack-values.yaml
```

Then wire the app up to it. `k8s/observability/*.yaml` is deliberately separate from `kubectl apply -f k8s/` -- the ServiceMonitor and PrometheusRule need their CRDs from kube-prometheus-stack, so they have to come after, not in the same sweep:

```bash
kubectl apply -f k8s/observability/
```

If you're using the Helm chart instead, its ServiceMonitor and PrometheusRule templates only render when the cluster actually has the matching CRD, so install order doesn't matter there -- `helm upgrade` after installing kube-prometheus-stack is enough to pick them up.

### SLOs

- **Availability**: 99.5% of requests succeed (non-5xx), measured as a rolling 5m error ratio.
- **Latency**: p95 request duration under 300ms, measured as a rolling 5m histogram quantile.

Both are enforced as Prometheus alerts (`k8s/observability/app-prometheusrule.yaml`): `PulseAppHighErrorRate` and `PulseAppHighLatency`, each firing after 5 minutes sustained over threshold.

## Load testing

```bash
pip install locust
locust -f loadtest/locustfile.py --host http://localhost:8000
```

Open `http://localhost:8089` to drive load and watch the Grafana dashboard / HPA respond. Against the Helm-deployed app through Ingress, use `--host http://localhost` instead.

## Design notes

- `/health` and `/ready` are separate: liveness vs. readiness, so Kubernetes can pull a pod out of rotation without restarting it.
- JSON logs to stdout only; log collection is the platform's job, not the app's.
- Prometheus metrics are keyed by route template, not raw path, to bound label cardinality.
- Config is typed via `pydantic-settings`, `PULSE_`-prefixed env vars.
- Schema changes are Alembic migrations, not `create_all()`.
- API and worker share only a queue contract (a job id, a function name), not code -- they're separate processes, deployed and scaled independently.
- `k8s/app-secret.yaml` is plaintext dev credentials checked into git, fine for a local kind cluster. Production would pull from a secret store (Sealed Secrets, External Secrets Operator, cloud KMS), not a committed Secret manifest.
- Postgres and Redis run as raw StatefulSets -- Postgres gets a PVC, Redis doesn't, so a pod restart drops any in-flight queued jobs. That's deliberate: it's exactly the failure the chaos-testing milestone will exercise.
- The ingress-nginx install is pinned to a release tag, not `main` -- a third-party manifest that can change underneath you shouldn't be applied from a moving branch.
- `pulse-app` and `pulse-worker` have no `replicas` field -- once an HPA targets a Deployment, a hardcoded replica count in the Deployment just fights it on every apply.
- The Helm chart doesn't manage the Namespace -- it's created separately with `--create-namespace`, so deleting the release can't take the namespace (and anything else in it) down with it.
- CI runs lint and test as separate jobs -- a lint failure doesn't wait on Postgres/Redis service containers to spin up, and they fail independently in the GitHub UI instead of as one undifferentiated red X.
- `trivy-action` is pinned by commit SHA, not a version tag -- it's third-party, and a tag can be moved to point at different code later. First-party actions (`actions/checkout`, `actions/setup-python`) stay tag-pinned; that distinction is deliberate, not an oversight.
- Trivy's `ignore-unfixed: true` means CI fails only on vulnerabilities that actually have a fix available -- failing a build over something nobody can patch yet is just noise.
- `serviceMonitorSelectorNilUsesHelmValues: false` (and the PodMonitor/Rule equivalents) is load-bearing: without it, Prometheus only scrapes ServiceMonitors created by its own Helm release, and the app's own ServiceMonitor would silently never get scraped.
- The Grafana dashboard JSON is loaded into the Helm chart via `.Files.Get`, not inlined into the template -- the dashboard's own legend formatting uses `{{ }}`, which would otherwise be parsed as Helm templating instead of passed through as text.
- The chart's ServiceMonitor and PrometheusRule templates are both guarded by `.Capabilities.APIVersions.Has` -- they only render if their CRD actually exists in the target cluster, so `helm install` doesn't fail on a cluster without kube-prometheus-stack.
- The error-rate alert divides rate() by rate() with no traffic guard. On zero requests that's 0/0 -> NaN, which Prometheus drops from the result set rather than evaluating `NaN > 0.005` as true -- an idle service doesn't trip the alert, no special-casing needed.
- Redis being unreachable at startup doesn't crash the app -- `/jobs` degrades to a clean 503 and `/health`/`/ready` keep responding. The app previously crash-looped on this (the arq pool's connection check at startup propagated and killed the whole process), which defeated the entire point of having a readiness probe.
