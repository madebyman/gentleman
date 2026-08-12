# build
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml ./
COPY uv.loc[k] ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-workspace --no-dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-editable

# deploy
FROM python:3.14-slim-bookworm
WORKDIR /app

RUN groupadd -r gentleman && useradd -r -g gentleman gentleman

COPY --from=builder --chown=gentleman:gentleman /app/.venv /app/.venv

# Mount agents/ at /app/agents/ (see compose.yaml for an example).
# If your environment cannot mount files, you may bake it into the image
# instead — but do not include credentials in it.

# COPY agents/ /app/agents/

ENV PATH="/app/.venv/bin:$PATH" \
    GENTLEMAN_APP_AGENTS_DIR=/app/agents

USER gentleman
EXPOSE 8000

ENTRYPOINT ["uvicorn", "gentleman:app"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
