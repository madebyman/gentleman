from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from ._lib.settings import AppSettings, RemoteSettings
from ._lib.core import builder, loader, hop

from ._lib.port.agui import create_agui_router
from ._lib.port.a2a import create_a2a_router, a2a_path_prefix
from ._lib.port.mcp import create_mcp

from ._errors import LifecycleError


__all__ = ['create_gentleman']


class _Gentleman:

    def __init__(
            self, agents_dir=None, *, name=None, origin=None, prefix=''):

        if prefix and not prefix.startswith('/'):
            raise ValueError(
                    f"gentleman: prefix must start with '/': {prefix!r}")

        app_settings = AppSettings() 
        remote_settings = RemoteSettings()

        self._agents_dir = Path(
                agents_dir or app_settings.agents_dir).resolve()

        self._app_name = name or app_settings.name

        self._app_origin = (
                origin or app_settings.origin).rstrip('/')

        self._app_prefix = prefix.rstrip('/')

        self._max_hop = remote_settings.max_hop

        # load
        self._local_specs, self._remote_specs = loader.load_specs(
                self._agents_dir)

        # build
        base_url = f'{self._app_origin}{self._app_prefix}{a2a_path_prefix}'

        self._agents = builder.build_agents(
                self._local_specs, self._remote_specs, base_url=base_url)

        self._mcp = None

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

        if self._mcp is None:
            raise LifecycleError(
                    'gentleman: attach() must be called before lifespan')

        async with AsyncExitStack() as stack:

            # _agents
            for v in self._agents.values():
                await stack.enter_async_context(v)

            # mcp
            await stack.enter_async_context(self._mcp.lifespan())

            yield

    def attach(self, app):

        if self._mcp is not None:
            raise LifecycleError('gentleman: already attached')

        # router
        routers = {'agui': create_agui_router, 'a2a': create_a2a_router}

        for k, v in routers.items():
            app.include_router(v(self._agents, max_hop=self._max_hop),
                               prefix=self._app_prefix)

        # mcp
        self._mcp = create_mcp(self._agents, app_name=self._app_name)

        app.mount(f'{self._app_prefix}/mcp',
                  hop.Guard(self._mcp.app, self._max_hop))

        return app


def create_gentleman(
        agents_dir=None,*, name=None, origin=None, prefix=''):

    return _Gentleman(
            agents_dir, name=name, origin=origin, prefix=prefix)


