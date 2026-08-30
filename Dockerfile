# Gentleman official image

# build
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

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
FROM python:3.14-slim-bookworm
WORKDIR /app

# uv
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uvx /usr/local/bin/
RUN uvx --version

# node
COPY --from=node:24-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:24-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && node --version

RUN groupadd -r gentleman \
 && useradd -r -g gentleman -m -d /home/gentleman gentleman

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

USER gentleman
EXPOSE 8000

ENTRYPOINT ["uvicorn", "gentleman:app"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
