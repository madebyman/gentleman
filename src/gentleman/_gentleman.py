from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from ._lib.settings import AppSettings, RemoteSettings
from ._lib.core import builder, loader

from ._lib.port.agui import create_agui_router
from ._lib.port.a2a import create_a2a
from ._lib.port.mcp import create_mcp


__all__ = ['create_gentleman']


class _Gentleman:

    def __init__(self, agents_dir=None, *, app_name=None, app_origin=None):

        app_settings = AppSettings() 
        remote_settings = RemoteSettings()

        self._app_name = app_name or app_settings.name

        self._app_origin = (
                app_origin or app_settings.origin).rstrip('/')

        self._agents_dir = Path(
                agents_dir or app_settings.agents_dir).resolve()

        self._max_hop = remote_settings.max_hop

        self._local_specs, self._remote_specs = loader.load_specs(
                self._agents_dir)

        self._agents = builder.build_agents(
                self._local_specs, self._remote_specs)

        self._a2a, self._mcp = {}, None

    @property
    def app_name(self):
        return self._app_name

    @property
    def agents(self):
        return dict(self._agents)

    @property
    def agents_dir(self):
        return self._agents_dir

    @property
    def is_bundled_example(self):
        return (self._agents_dir / '.bundled-example').exists()

    @asynccontextmanager
    async def lifespan(self, app=None):

        # if self._a2a is None:
            # raise RuntimeError('gentleman: attach() must be called before lifespan')

        async with AsyncExitStack() as stack:

            # agents
            for v in self._agents.values():
                await stack.enter_async_context(v)

            # a2a
            await stack.enter_async_context(self._a2a.lifespan())

            # mcp
            await stack.enter_async_context(self._mcp.lifespan())

            yield

    def attach(self, app, prefix=''):

        # if self._a2a is not None:
            # raise RuntimeError('gentleman: already attached')

        prefix = prefix.rstrip('/')

        if prefix and not prefix.startswith('/'):
            raise ValueError(
                    f"gentleman: prefix must start with '/': {prefix!r}")

        # agui
        agui_router = create_agui_router(
                self._agents, self._remote_specs, max_hop=self._max_hop)

        app.include_router(agui_router, prefix=prefix)

        # a2a
        self._a2a = create_a2a(self._agents,
                               self._remote_specs,
                               base_url=f'{self._app_origin}{prefix}',
                               max_hop=self._max_hop)

        app.mount(f'{prefix}/a2a', self._a2a.app)

        # mcp
        self._mcp = create_mcp(
                self._agents, self._remote_specs, app_name=self._app_name)

        app.mount(f'{prefix}/mcp', self._mcp.app)

        return app


def create_gentleman(agents_dir=None, *, app_name=None, app_origin=None):

    return _Gentleman(
            agents_dir, app_name=app_name, app_origin=app_origin)


