<p align="center">
  <img src="https://raw.githubusercontent.com/madebyman/gentleman/main/.github/assets/gentleman-logo.svg" alt="Gentleman" width="520">
</p>

<p align="center">
  <a href="https://pypi.org/project/gentleman-agents/"><img src="https://img.shields.io/pypi/v/gentleman-agents?labelColor=222&color=fff" alt="PyPI"></a>
  <a href="https://github.com/madebyman/gentleman/pkgs/container/gentleman"><img src="https://img.shields.io/badge/ghcr.io-gentleman-fff?labelColor=222&logo=docker&logoColor=fff" alt="Docker"></a>
  <a href="https://artifacthub.io/packages/helm/gentleman/gentleman"><img src="https://img.shields.io/badge/Artifact_Hub-gentleman-fff?labelColor=222&logo=artifacthub&logoColor=fff" alt="Artifact Hub"></a>
  <a href="https://pypi.org/project/gentleman-agents/"><img src="https://img.shields.io/pypi/pyversions/gentleman-agents?labelColor=222&color=fff" alt="Python"></a>
  <a href="https://github.com/madebyman/gentleman/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/gentleman-agents?labelColor=222&color=fff" alt="License"></a>
</p>

<p align="center">
  EN | <a href="https://github.com/madebyman/gentleman/blob/main/README.ja.md">JA</a>
</p>

<hr>

<p align="center">
  <b>Gentleman</b> <i>Declarative AI agent framework</i> — MCP for tools, A2A for agents, AG-UI for humans.
</p>

Gentleman is a multi-agent server built on Pydantic AI and FastAPI. Each agent
is a directory with a YAML file. Put them under `agents/`, and a single process
serves them all over three protocols:

- **AG-UI** — for humans, from a chat UI.
- **A2A** — for other agents, local or remote.
- **MCP** — for MCP clients, as tools.

Agents use tools from MCP servers and delegate to other agents. No glue code.

```
agents/
  concierge/
    agent.yaml
    mcp_config.json
  writer/
    agent.yaml
```

## Requirements

- Python 3.14+

## Quick start

Scaffold a project with [uv](https://docs.astral.sh/uv/) and run it:

```sh
uvx --from gentleman-agents gentleman init my-gentleman
cd my-gentleman
uv sync
# edit agents/example/agent.yaml
uv run gentleman dev
```

`gentleman dev` serves the agents at `http://127.0.0.1:8000`. The interfaces are
available at:

```
AG-UI : http://localhost:8000/agui
A2A   : http://localhost:8000/a2a
MCP   : http://localhost:8000/mcp
```

The example agent uses the built-in `gentleman:echo` model, so it runs without
any credentials. To use a model provider, copy `.env.sample` to `.env`, set its
API key, and run `uv run --env-file .env gentleman dev`.

`gentleman init` scaffolds a project into the given directory, creating it if it
does not exist. Without an argument, it scaffolds into the current directory.

The package is published as `gentleman-agents`, while the command is `gentleman`.
The `--from` flag is therefore required with `uvx`.

## Install

As a command-line tool:

```sh
uv tool install gentleman-agents
gentleman --help
```

As a project dependency:

```sh
uv add gentleman-agents
```

With pip:

```sh
pip install gentleman-agents
```

## Model providers

Model providers are extras. Install the ones you use:

```sh
uv add "gentleman-agents[openai]"
```

| Extra | Model prefix | Credentials |
|---|---|---|
| `openai` | `openai:`, `ollama:` and other OpenAI-compatible APIs | `OPENAI_API_KEY` |
| `anthropic` | `anthropic:` | `ANTHROPIC_API_KEY` |
| `google` | `google:`, `google-cloud:` | `GOOGLE_API_KEY` |
| `bedrock` | `bedrock:` | AWS credentials |
| `xai` | `xai:` | `XAI_API_KEY` |

`providers` installs all five. The built-in `gentleman:echo` model needs none.
Projects from `gentleman init` start with `openai`.

Other providers supported by Pydantic AI can be added directly:

```sh
uv add "pydantic-ai-slim[groq]"
```

## Interactive chat

`gentleman chat` is a small client for trying out your agents from a terminal.
It is meant for development and testing, not as a chat interface for users.

The `gentleman chat` subcommand needs the `chat` extra:

```sh
uv tool install "gentleman-agents[chat]"
gentleman chat
```

Or run it directly:

```sh
uvx --from "gentleman-agents[chat]" gentleman chat
```

To add it to a project instead:

```sh
uv add "gentleman-agents[chat]"
```

Extras can be combined, e.g. `gentleman-agents[chat,openai]`.

## Docker

Images are published to the GitHub Container Registry for `linux/amd64` and
`linux/arm64`, with all five model providers:

```sh
docker pull ghcr.io/madebyman/gentleman:edge
```

`edge` tracks the latest build from `main`. See the
[packages page](https://github.com/madebyman/gentleman/pkgs/container/gentleman)
for available tags.

## Helm

The Helm chart deploys gentleman on Kubernetes. Agents are declared as YAML in
the chart values and mounted into the pod, one directory per agent.

```sh
helm install gentleman oci://ghcr.io/madebyman/charts/gentleman
kubectl port-forward svc/gentleman 8000:80
```

The interfaces are then available at the same URLs as in [Quick start](#quick-start).

With no values, the chart ships an example agent using `gentleman:echo`, so it
runs without any credentials. For agents, secrets and ingress, see the chart on
[Artifact Hub](https://artifacthub.io/packages/helm/gentleman/gentleman).

## Status

Alpha. The API and the configuration format may change without notice.

## License

MIT
