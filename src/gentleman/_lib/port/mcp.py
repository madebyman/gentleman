from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from ..ask import make_ask


__all__ = ['create_mcp']


class _MCP:

    def __init__(self, agents, *, app_name, settings):

        # mcp
        self._mcp = MCPServer(app_name)

        for k, v in agents.items():
           self._mcp.add_tool(make_ask(v),
                              name=f'ask_{k}',
                              description=v.description)

        self._transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=settings.dns_rebinding_protection,
            allowed_hosts=settings.allowed_hosts,
            allowed_origins=settings.allowed_origins)

        # app
        self._app = self._build_app()

    @property
    def app(self):
        return self._app

    def _build_app(self):

        return self._mcp.streamable_http_app(
            stateless_http=True,
            json_response=True,
            streamable_http_path='/',
            transport_security=self._transport_security)

    def lifespan(self):
        return self._mcp.session_manager.run()


def create_mcp(agents, *, app_name, settings):

    mcp = _MCP(agents, app_name=app_name, settings=settings)
    return mcp

