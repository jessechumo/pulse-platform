{{- define "pulse-platform.labels" -}}
app.kubernetes.io/part-of: pulse-platform
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
