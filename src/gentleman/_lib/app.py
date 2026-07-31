import sys

from pathlib import Path
from contextlib import AsyncExitStack, asynccontextmanager

from pydantic_ai.ui.ag_ui import AGUIAdapter

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from starlette.requests import Request
from starlette.responses import Response

from . import loader, config

# from .conductor import build_conductor
# from .a2a import build_a2a, build_remote_tools

from .conductor import make_delegation_tool
from .a2a import build_a2a, make_agui_proxy, make_remote_tool
from .mcp import build_mcp

def create_app():

    # config
    config_dir = Path('./agents')

    # agents
    try:
        agents, remote_agents = loader.load_agents(
                config_dir, make_delegation_tool, make_remote_tool)

    except (loader.ConfigError) as err:
        print(err, file=sys.stderr)
        sys.exit(1)

    # ag-ui proxy
    proxies = {k: make_agui_proxy(v) for k, v in remote_agents.items()}

    # a2a
    a2a_settings = config.A2ASettings()
    a2a = build_a2a(agents, a2a_settings.base_url)

    # mcp
    mcp = build_mcp(agents)

    # lifespan
    @asynccontextmanager
    async def lifespan(app):

        async with AsyncExitStack() as stack:

            # agents
            for v in agents.values():
                await stack.enter_async_context(v)

            # a2a
            for v in a2a.values():
                await stack.enter_async_context(
                        v.router.lifespan_context(v))

            # mcp
            await stack.enter_async_context(mcp.session_manager.run())

            yield

    # app
    app = FastAPI(title='Gentleman', lifespan=lifespan)

    # cors
    cors_settings = config.CorsSettings()
    app.add_middleware(CORSMiddleware, **cors_settings.model_dump())

    # /agents
    @app.post('/agents/{agent_name}')
    async def perform(agent_name: str, request: Request) -> Response:

        # ag-ui
        if (agent := agents.get(agent_name)) is not None:
            return await AGUIAdapter.dispatch_request(request, agent=agent)

        # ag-ui proxy
        if (proxy := proxies.get(agent_name)) is not None:
            return await proxy(request)

        raise HTTPException(404)

    # /a2a
    for k, v in a2a.items():
        app.mount(f'/a2a/{k}', v)

    # /mcp
    app.mount('/mcp', mcp.streamable_http_app())

    return app
