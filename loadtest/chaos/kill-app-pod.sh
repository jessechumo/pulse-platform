#!/usr/bin/env bash
# Chaos experiment: kill a random pulse-app pod while it's serving traffic.
#
# Hypothesis: the Deployment replaces the pod within seconds, the Service
# stops routing to it as soon as its endpoint is removed, and in-flight
# requests to the OTHER pods are unaffected. Run loadtest/locustfile.py (or
# any traffic) against the cluster while this runs, and watch:
#   kubectl get pods -n pulse -l app.kubernetes.io/name=pulse-app -w
# plus the Grafana dashboard's error rate panel.
set -euo pipefail

NAMESPACE="${NAMESPACE:-pulse}"

mapfile -t PODS < <(
  kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=pulse-app \
    -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n'
)

if [ "${#PODS[@]}" -eq 0 ]; then
  echo "no pulse-app pods found in namespace $NAMESPACE" >&2
  exit 1
fi

POD="${PODS[RANDOM % ${#PODS[@]}]}"
echo "killing pod $POD"
kubectl delete pod "$POD" -n "$NAMESPACE"

echo "watching deployment recover..."
kubectl rollout status deployment/pulse-app -n "$NAMESPACE" --timeout=60s
