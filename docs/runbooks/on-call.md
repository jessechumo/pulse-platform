# On-call runbook

## Alert: PulseAppHighErrorRate

5xx ratio has been above 0.5% for 5 minutes (the availability SLO's error budget).

1. Open the Grafana dashboard's **Error rate (5xx)** panel to see which path is failing and whether it's rising, flat, or already recovering.
2. Check `/ready`:
   ```bash
   curl -s localhost/ready
   ```
   A `database` or `redis` entry showing `unreachable` means this is a dependency outage, not an app bug -- jump to the dependency sections below.
3. If both dependencies show `ok`, check the app's own logs for the failing path:
   ```bash
   kubectl logs -n pulse -l app.kubernetes.io/name=pulse-app --tail=200 | grep '"level": "ERROR"'
   ```
4. Check whether this started right after a deploy:
   ```bash
   kubectl rollout history deployment/pulse-app -n pulse
   ```
   If so, see **Rolling back a bad deploy** below.

## Alert: PulseAppHighLatency

p95 request duration has been above 300ms for 5 minutes.

1. Grafana's **p95 latency** panel -- is it one path or across the board?
2. Across the board usually means a dependency is slow, not the app: check Postgres (`kubectl top pod -n pulse -l app.kubernetes.io/name=postgres`) and Redis similarly.
3. One path (typically `/jobs`) under load is often just the HPA not having scaled yet:
   ```bash
   kubectl get hpa -n pulse
   ```
   Check `REPLICAS` against `MAXPODS` -- if it's pinned at max and still struggling, that's a capacity problem, not an incident; consider raising `maxReplicas` in `k8s/app-hpa.yaml` (or `values.yaml` for the Helm chart).

## `/ready` failing / pod not receiving traffic

```bash
curl -s localhost/ready
```

The response names which dependency is down:

- **`database: unreachable`** -- check the Postgres pod:
  ```bash
  kubectl get pods -n pulse -l app.kubernetes.io/name=postgres
  kubectl logs -n pulse -l app.kubernetes.io/name=postgres --tail=100
  ```
  If the pod is `CrashLoopBackOff`, check its PVC is still bound (`kubectl get pvc -n pulse`) before assuming it's an app-level issue.

- **`redis: unreachable`** -- check the Redis pod the same way. The app itself stays up and serving `/health` either way (see the design note on this in the main README); `POST /jobs` degrades to a clean 503 instead of hanging or crashing, so this is lower urgency than a database outage unless job throughput actually matters right now.

If both show `ok` but the pod still isn't getting traffic, check it actually passed its readiness probe and has an endpoint:

```bash
kubectl get endpoints pulse-app -n pulse
kubectl describe pod -n pulse <pod-name>
```

## Rolling back a bad deploy

Raw manifests / `kubectl apply -f k8s/` workflow:

```bash
kubectl rollout undo deployment/pulse-app -n pulse
kubectl rollout status deployment/pulse-app -n pulse
```

Helm workflow:

```bash
helm history pulse -n pulse
helm rollback pulse <revision> -n pulse
```

Either way, watch `/ready` and the Grafana error-rate panel for a few minutes after to confirm the rollback actually fixed it before closing out.

## Useful commands

```bash
kubectl get pods -n pulse
kubectl logs -n pulse -l app.kubernetes.io/name=pulse-app --tail=200
kubectl describe pod -n pulse <pod-name>
kubectl top pods -n pulse          # needs metrics-server
kubectl get hpa -n pulse
```
