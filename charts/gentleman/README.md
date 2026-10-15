# gentleman

Declarative AI agent server — MCP for tools, A2A for agents, AG-UI for humans.

This chart deploys gentleman on Kubernetes. Agents are declared as YAML in
`values.yaml`, rendered into one ConfigMap per agent, and mounted into the pod
as one directory per agent.

Source: https://github.com/madebyman/gentleman


## Install

  Install the chart from ghcr:

    helm install gentleman oci://ghcr.io/madebyman/charts/gentleman

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

  gentleman reads one directory per agent: `<name>/agent.yaml` (or
  `<name>/a2a.yaml` for a remote agent), with an optional
  `<name>/mcp_config.json`. The chart keeps that layout.

  Each key under `agents` is an agent name, and holds that agent's files:

    agents:
      concierge:
        agent.yaml:
          model: gentleman:echo
          description: Front desk.
          routing:
            visibility: public
            delegates: [writer]
        mcp_config.json:
          mcpServers:
            time:
              command: uvx
              args: [mcp-server-time]
      writer:
        agent.yaml:
          model: gentleman:echo
      far:
        a2a.yaml:
          url: https://far.example.com/a2a/far

  Inside the pod:

    /app/agents/concierge/agent.yaml
    /app/agents/concierge/mcp_config.json
    /app/agents/writer/agent.yaml
    /app/agents/far/a2a.yaml

  `agent.yaml` and `a2a.yaml` are written as YAML, `mcp_config.json` as JSON.
  The schema rejects other file names, both `agent.yaml` and `a2a.yaml` in one
  agent, `mcp_config.json` next to `a2a.yaml`, and names starting with `.`
  (gentleman skips such directories).

  The chart lays an emptyDir at `agentsMountPath` and mounts one ConfigMap per
  agent on top of it, so the image's built-in example never mixes in.

  When `agents` and `existingAgents` are both empty, `defaultAgents` is used
  instead. It holds the built-in example, so `helm install gentleman` works
  out of the box. Once you set either, `defaultAgents` is ignored.

  Changes to `agents` or `defaultAgents` roll the pods automatically
  (checksum/agents).

  Agent names that are not valid Kubernetes names (`my_agent`, `Writer`) are
  fine: the ConfigMap and volume get a sanitized name with a short hash, and
  the directory keeps the real name.

  gentleman starts every agent's MCP servers before it opens its port, one
  after another (`initTimeout`, 30s each by default). `startupProbe` allows
  150s for that; raise `startupProbe.failureThreshold` for more servers.

### Your own ConfigMaps

  To manage an agent outside the chart, make one ConfigMap per agent from its
  directory — each file becomes a key:

    kubectl create configmap my-writer --from-file=agents/writer

  and map agent names to ConfigMap names:

    existingAgents:
      writer: my-writer

  `agents` and `existingAgents` can be used together, but the same agent name
  in both fails the render.

  NOTE: ConfigMaps in `existingAgents` are not watched. Restart the deployment
  after changing them:

    kubectl rollout restart deploy/gentleman

  NOTE: A missing ConfigMap keeps the pod in ContainerCreating (FailedMount).

### Your own volume

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
  path prefix is not enough. `httpRoute.timeouts` applies to the generated
  rule only; with `rules`, write `timeouts` in each rule yourself.

  AG-UI streams over SSE. Make sure the proxy in front of it does not buffer
  responses or cut idle connections too early:

    Traefik  — disable response buffering for the route.
    AWS ALB  — alb.ingress.kubernetes.io/load-balancer-attributes:
               idle_timeout.timeout_seconds=300
    Gateway  — httpRoute.timeouts.request covers the whole stream; its
               default depends on the implementation ("0s" disables it):

                 httpRoute:
                   timeouts:
                     request: 300s
                     backendRequest: 300s

  Enabling both `ingress` and `httpRoute` is supported for migration, but the
  same hostname may be served twice. Disable one once the cutover is complete.


## Replicas

  Run gentleman with one replica:

    replicaCount: 1
    autoscaling:
      enabled: false

  A2A tasks are kept in memory, in the pod that received them. With more than
  one replica, `tasks/get` and `tasks/resubscribe` for a task may reach
  another pod and fail (task not found).

  AG-UI and MCP keep no state between requests, but the A2A interface is
  served by the same pod, so the limit applies to the whole deployment.

  Tasks do not survive a restart or a rollout either: a task started on the
  old pod is gone once it stops.


## Values

  Deployment

  | Key | Description | Default |
  |---|---|---|
  | `replicaCount` | Number of replicas (ignored when autoscaling is enabled). Keep it at 1 — see Replicas | `1` |
  | `autoscaling.enabled` | Create a HorizontalPodAutoscaler. Keep it off — see Replicas | `false` |
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
  | `startupProbe` | Holds off the other probes until startup completes, MCP servers included (150s) | see values |
  | `livenessProbe` | Restarts the container when `/health` fails | see values |
  | `readinessProbe` | Takes the pod out of the Service when `/ready` returns 503 (starting up, shutting down) | see values |
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
  | `agentsMountPath` | Where agent directories are mounted | `/app/agents` |
  | `agents` | Your agents, keyed by agent name, then file name | `{}` |
  | `existingAgents` | Agents from your own ConfigMaps, as `name: ConfigMap` | `{}` |
  | `defaultAgents` | Used only when `agents` and `existingAgents` are empty; `null` for none | `example` |

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
  | `httpRoute.timeouts` | `request` / `backendRequest` for the generated rule; ignored with `rules` | `{}` |
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
