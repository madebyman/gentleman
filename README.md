# Gentleman

*A gentleman among agents.*

Declarative AI agent server — MCP for tools, A2A for agents, AG-UI for humans.

## Requirements

- Python 3.14+

## Quick start

Run without installing, using [uv](https://docs.astral.sh/uv/):

```sh
uvx --from gentleman-agents gentleman init my-agents
```

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

## Interactive chat

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

## Docker

Images are published to the GitHub Container Registry for `linux/amd64` and
`linux/arm64`:

```sh
docker pull ghcr.io/madebyman/gentleman:edge
```

`edge` tracks the latest build from `main`. See the
[packages page](https://github.com/madebyman/gentleman/pkgs/container/gentleman)
for available tags.

## Status

Alpha. The API and the configuration format may change without notice.

## License

MIT
