# gentleman

Declarative AI agent server — MCP for tools, A2A for agents, AG-UI for humans.

This chart deploys gentleman on Kubernetes. Agents are declared as YAML in
`values.yaml`, rendered into a ConfigMap, and mounted into the pod.

Source: https://github.com/madebyman/gentleman


## Install

  Install the chart from ghcr:

    helm install gentleman oci://ghcr.io/madebyman/charts/gentleman --version 0.1.0

  Check the deployment:

    kubectl rollout status deploy/gentleman
    helm test gentleman

  Forward a local port to the service:

    kubectl port-forward svc/gentleman 8000:80

  Then the interfaces are available at:

    AG-UI : http://localhost:8000/agui
    A2A   : http://localhost:8000/a2a
    MCP   : http://localhost:8000/mcp

  With no values at all, the chart ships a built-in example agent using
  `gentleman:echo`, so it runs without any credentials.


## Agents

  Each key under `agents` is a file path under `agentsMountPath`, and its value
  is the agent definition written to that file.

    agents:
      assistant/agent.yaml:
        model: gentleman:echo
        description: A helpful assistant.
        routing:
          visibility: public
          delegates: []
        metadata:
          version: 1.0.0
        instructions: |
          You are a helpful assistant.

  The path is kept as-is inside the pod:

    /app/agents/assistant/agent.yaml

  When `agents` is empty, `defaultAgents` is used instead. It holds the
  built-in example, so `helm install gentleman` works out of the box.

  Once you set `agents`, `defaultAgents` is ignored — the example is not mixed
  into your agents.

  Changes to `agents` or `defaultAgents` roll the pods automatically
  (checksum/agents).

  To manage agents outside the chart, point to your own ConfigMap:

    agentsExistingConfigMap: my-agents

  NOTE: ConfigMap keys cannot contain `/`, so an existing ConfigMap is mounted
  flat — one file per key, directly under `agentsMountPath`.

  NOTE: An existing ConfigMap is not watched. Restart the deployment after
  changing it:

    kubectl rollout restart deploy/gentleman

  To bring your own volume (e.g. a PVC), mount no agents from the chart:

    defaultAgents: null
    extraVolumes:
      - name: agents
        persistentVolumeClaim:
          claimName: my-agents
    extraVolumeMounts:
      - name: agents
        mountPath: /app/agents
        readOnly: true


## Secrets

  Model provider credentials are passed to the container as environment
  variables from a Secret.

  Use an existing Secret (recommended):

    kubectl create secret generic gentleman-secrets \
      --from-literal=ANTHROPIC_API_KEY=sk-ant-...

    secrets:
      existingSecret: gentleman-secrets

  Or let the chart create one:

    secrets:
      create: true
      data:
        ANTHROPIC_API_KEY: sk-ant-...

  Every key in the Secret becomes an environment variable (envFrom).

  Setting `secrets.data` without `secrets.create: true` fails the render, so
  credentials are never dropped silently.


## Exposing

  `appOrigin` is the public origin gentleman advertises. When it is empty, it
  is derived from the first ingress host, or falls back to
  `http://localhost:8000`. Set it explicitly behind a proxy or an HTTPRoute.

  Ingress:

    appOrigin: https://agents.example.com
    ingress:
      enabled: true
      className: traefik
      hosts:
        - host: agents.example.com
          paths:
            - path: /
              pathType: Prefix
      tls:
        - secretName: gentleman-tls
          hosts:
            - agents.example.com

  Gateway API (HTTPRoute):

    appOrigin: https://agents.example.com
    httpRoute:
      enabled: true
      parentRefs:
        - name: gateway
          sectionName: https
      hostnames:
        - agents.example.com

  `httpRoute.rules` replaces the generated rule entirely, for when a single
  path prefix is not enough.

  AG-UI streams over SSE. Make sure the proxy in front of it does not buffer
  responses or cut idle connections too early:

    Traefik  — disable response buffering for the route.
    AWS ALB  — alb.ingress.kubernetes.io/load-balancer-attributes:
               idle_timeout.timeout_seconds=300

  Enabling both `ingress` and `httpRoute` is supported for migration, but the
  same hostname may be served twice. Disable one once the cutover is complete.


## Values

  Deployment

  | Key | Description | Default |
  |---|---|---|
  | `replicaCount` | Number of replicas (ignored when autoscaling is enabled) | `1` |
  | `autoscaling.enabled` | Create a HorizontalPodAutoscaler | `false` |
  | `autoscaling.minReplicas` | Minimum replicas | `1` |
  | `autoscaling.maxReplicas` | Maximum replicas | `100` |
  | `autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization | `80` |
  | `image.repository` | Container image | `ghcr.io/madebyman/gentleman` |
  | `image.tag` | Image tag (defaults to the chart appVersion) | `""` |
  | `image.pullPolicy` | Image pull policy | `IfNotPresent` |
  | `nameOverride` | Override the chart name | `""` |
  | `fullnameOverride` | Override the full resource name | `""` |

  Pod

  | Key | Description | Default |
  |---|---|---|
  | `podAnnotations` | Extra pod annotations | `{}` |
  | `podLabels` | Extra pod labels | `{}` |
  | `podSecurityContext` | Pod security context | non-root, uid/gid 1000 |
  | `securityContext` | Container security context | `{}` |
  | `resources` | Container resources | 100m / 256Mi, limit 512Mi |
  | `livenessProbe` / `readinessProbe` | Probes against `/health` | see values |
  | `extraVolumes` / `extraVolumeMounts` | Additional volumes and mounts | `[]` |
  | `nodeSelector` / `affinity` / `tolerations` | Scheduling | empty |

  Environment

  | Key | Description | Default |
  |---|---|---|
  | `appOrigin` | Public origin advertised by gentleman | `""` |
  | `env` | Environment variables (`GENTLEMAN_*`) | see below |
  | `extraEnv` | Additional env entries, as in a container spec | `[]` |
  | `secrets.existingSecret` | Name of an existing Secret to load as env | `""` |
  | `secrets.create` | Create a Secret from `secrets.data` | `false` |
  | `secrets.data` | Key/value pairs for the created Secret | `{}` |

  Agents

  | Key | Description | Default |
  |---|---|---|
  | `agentsMountPath` | Where agent files are mounted | `/app/agents` |
  | `agentsExistingConfigMap` | Use an existing ConfigMap for agents | `""` |
  | `agents` | Your agent definitions, keyed by file path | `{}` |
  | `defaultAgents` | Used only when `agents` is empty; `null` for none | `example/agent.yaml` |

  Networking

  | Key | Description | Default |
  |---|---|---|
  | `service.type` | Service type | `ClusterIP` |
  | `service.port` | Service port | `80` |
  | `service.targetPort` | Container port | `8000` |
  | `ingress.enabled` | Create an Ingress | `false` |
  | `ingress.className` | IngressClass name | `""` |
  | `ingress.annotations` | Ingress annotations | `{}` |
  | `ingress.hosts` | Hosts and paths | `localhost`, `/` |
  | `ingress.tls` | TLS entries | `[]` |
  | `httpRoute.enabled` | Create a Gateway API HTTPRoute | `false` |
  | `httpRoute.annotations` | HTTPRoute annotations | `{}` |
  | `httpRoute.parentRefs` | Gateways to attach to | `gateway` / `http` |
  | `httpRoute.hostnames` | Hostnames (templated) | `[]` |
  | `httpRoute.path` / `httpRoute.pathType` | Match for the generated rule | `/` / `PathPrefix` |
  | `httpRoute.rules` | Replace the generated rule (templated) | `[]` |

  ServiceAccount

  | Key | Description | Default |
  |---|---|---|
  | `serviceAccount.create` | Create a ServiceAccount | `true` |
  | `serviceAccount.name` | ServiceAccount name | `gentleman` |
  | `serviceAccount.automount` | Mount the API token | `true` |
  | `serviceAccount.annotations` | e.g. IRSA role ARN | `{}` |

  Default `env`:

    GENTLEMAN_APP_NAME: Gentleman
    GENTLEMAN_APP_EXPOSE: '["agui","a2a","mcp"]'
    GENTLEMAN_CORS_ALLOW_ORIGINS: '[]'
    GENTLEMAN_REMOTE_MAX_HOP: '8'

  `GENTLEMAN_APP_AGENTS_DIR` and `GENTLEMAN_APP_ORIGIN` are set by the chart
  from `agentsMountPath` and `appOrigin`.


## License

  MIT
