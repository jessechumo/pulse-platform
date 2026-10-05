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
