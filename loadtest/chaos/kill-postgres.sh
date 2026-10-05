#!/usr/bin/env bash
# Chaos experiment: kill the Postgres pod to simulate a database outage.
#
# Hypothesis: /ready flips to 503 (database: unreachable) within one probe
# interval, Kubernetes pulls pulse-app out of the Service's endpoints, and
# once the StatefulSet recreates the pod and Postgres finishes recovering
# from its PVC, /ready goes back to 200 on its own -- no manual intervention.
# Watch with:
#   watch -n2 curl -s localhost/ready
#   kubectl get pods -n pulse -l app.kubernetes.io/name=postgres -w
set -euo pipefail

NAMESPACE="${NAMESPACE:-pulse}"

POD=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=postgres \
  -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD" ]; then
  echo "no postgres pod found in namespace $NAMESPACE" >&2
  exit 1
fi

echo "killing pod $POD"
kubectl delete pod "$POD" -n "$NAMESPACE"

echo "watching statefulset recover..."
kubectl rollout status statefulset/postgres -n "$NAMESPACE" --timeout=120s
