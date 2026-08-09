from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, HTTPException

from pydantic_ai.ui.ag_ui import AGUIAdapter

from starlette.requests import Request
from starlette.responses import Response

from ._lib import config, loader

from ._lib.a2a import (build_a2a,
                       make_agui_proxy,
                       make_tool as make_remote_tool)

from ._lib.conductor import make_tool as make_delegation_tool
from ._lib.mcp import build_mcp

__all__ = ['create_gentleman']

class _Gentleman:

    def __init__(self, agents_dir=None, *, base_url=None, name=None):

        gentleman_settings = config.GentlemanSettings() 
        a2a_settings = config.A2ASettings()

        self._agents_dir = Path(
                agents_dir or gentleman_settings.agents_dir).resolve()

        self._base_url = (
                base_url or a2a_settings.base_url).rstrip('/')

        self._max_hop = a2a_settings.max_hop

        self._name = name or 'gentleman'

        self._agents, self._remotes = loader.load_agents(
                self._agents_dir, make_delegation_tool, make_remote_tool)

        self._proxies = {
                k: make_agui_proxy(v, self._max_hop) for k, v in self._remotes.items()}

        self._a2a = None

        self._mcp = build_mcp(self._agents, self._remotes, name=self._name)

    @property
    def agents(self):
        return dict(self._agents)

    @property
    def agents_dir(self):
        return self._agents_dir

    @property
    def is_bundled_example(self):
        return (self._agents_dir / '.bundled-example').exists()

    def _router(self):
        router = APIRouter()

        @router.post('/agents/{agent_name}')
        async def agents(agent_name: str, request: Request) -> Response:

           # ag-ui
            if (agent := self._agents.get(agent_name)) is not None:
                return await AGUIAdapter.dispatch_request(request,
                                                          agent=agent)

            # ag-ui proxy
            if (proxy := self._proxies.get(agent_name)) is not None:
                return await proxy(request)

            raise HTTPException(404)

        return router

    @asynccontextmanager
    async def lifespan(self, app=None):

        if self._a2a is None:
            raise RuntimeError('gentleman: attach() must be called before lifespan')

        async with AsyncExitStack() as stack:

            # agents
            for v in self._agents.values():
                await stack.enter_async_context(v)

            # a2a
            for v in self._a2a.values():
                await stack.enter_async_context(
                        v.router.lifespan_context(v))

            # mcp
            await stack.enter_async_context(
                    self._mcp.session_manager.run())

            yield

    def attach(self, app, prefix=''):

        if self._a2a is not None:
            raise RuntimeError('gentleman: already attached')

        prefix = prefix.rstrip('/')

        if prefix and not prefix.startswith('/'):
            raise ValueError(
                    f"gentleman: prefix must start with '/': {prefix!r}")

        app.include_router(self._router(), prefix=prefix)

        # /a2a
        self._a2a = build_a2a(self._agents,
                              self._remotes,
                              f'{self._base_url}{prefix}',
                              self._max_hop)

        for k, v in self._a2a.items():
            app.mount(f'{prefix}/a2a/{k}', v)

        # /mcp
        app.mount(f'{prefix}/mcp', self._mcp.streamable_http_app())

        return app


def create_gentleman(agents_dir=None, *, base_url=None, name=None):

    return _Gentleman(
            agents_dir, base_url=base_url, name=name)


