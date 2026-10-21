# Gentleman official image

# build
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY README.md LICENSE ./
COPY src/ ./src/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# deploy
FROM python:3.14-slim-trixie
WORKDIR /app

# os: pick up security updates published after the base image was built
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

# python: the app runs from /app/.venv; pip (and the libraries it vendors)
# is not used at runtime
RUN python -m pip uninstall -y pip

# uv
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uvx /usr/local/bin/
RUN uvx --version

# node: npx is needed for stdio MCP servers; corepack is not
COPY --from=node:24-trixie-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:24-trixie-slim /usr/local/lib/node_modules /usr/local/lib/node_modules

RUN rm -rf /usr/local/lib/node_modules/corepack \
 && ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && npm install -g npm@latest \
 && npm cache clean --force \
 && node --version && npm --version

# Fixed uid/gid 1000, matching the Helm chart's runAsUser/runAsGroup.
# Without -u/-g, useradd -r picks a system id (999), and a pod running as
# 1000 cannot write $HOME (npx / uvx caches for stdio MCP servers).
RUN groupadd -r -g 1000 gentleman \
 && useradd -r -u 1000 -g gentleman -m -d /home/gentleman gentleman

COPY --from=builder --chown=gentleman:gentleman /app/.venv /app/.venv
COPY --chown=gentleman:gentleman src/gentleman/_tmpl/agents/ /app/agents/

ENV PATH="/app/.venv/bin:$PATH" \
    GENTLEMAN_APP_AGENTS_DIR=/app/agents \
    HOME=/home/gentleman \
    NPM_CONFIG_CACHE=/home/gentleman/.npm \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    UV_CACHE_DIR=/home/gentleman/.cache/uv \
    UV_PYTHON_INSTALL_DIR=/home/gentleman/.local/share/uv/python

# Numeric, so that runAsNonRoot can be verified without resolving the name.
USER 1000:1000
EXPOSE 8000

ENTRYPOINT ["uvicorn", "gentleman:app"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
