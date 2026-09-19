{{/* Expand the name of the chart.  */}}

{{- define "gentleman.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}


{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}

{{- define "gentleman.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}


{{/* Create chart name and version as used by the chart label.  */}}

{{- define "gentleman.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}


{{/* Common labels */}}

{{- define "gentleman.labels" -}}
helm.sh/chart: {{ include "gentleman.chart" . }}
{{ include "gentleman.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}


{{/* Selector labels */}}

{{- define "gentleman.selectorLabels" -}}
app.kubernetes.io/name: {{ include "gentleman.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}


{{/* secretName */}}

{{- define "gentleman.secretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{- .Values.secrets.existingSecret -}}
{{- else -}}
{{- printf "%s-secrets" (include "gentleman.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/* appOrigin */}}

{{- define "gentleman.appOrigin" -}}
{{- if .Values.appOrigin -}}
{{- .Values.appOrigin -}}
{{- else if and .Values.ingress.enabled .Values.ingress.hosts -}}
{{- $host := (first .Values.ingress.hosts).host -}}
{{- if .Values.ingress.tls -}}
{{- printf "https://%s" $host -}}
{{- else -}}
{{- printf "http://%s" $host -}}
{{- end -}}
{{- else -}}
http://localhost:8080
{{- end -}}
{{- end -}}


{{/* path -> ConfigMap key */}}

{{- define "gentleman.agentKey" -}}
{{- . | replace "/" "__" -}}
{{- end -}}

{{/* agentsConfigMapName */}}

{{- define "gentleman.agentsConfigMapName" -}}
{{- .Values.agentsExistingConfigMap | default (printf "%s-agents" (include "gentleman.fullname" .)) -}}
{{- end -}}

{{/* serviceAccountName */}}

{{- define "gentleman.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "gentleman.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
