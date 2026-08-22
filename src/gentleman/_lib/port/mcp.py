from mcp.server.fastmcp import FastMCP

from ..ask import make_ask


__all__ = ['create_mcp']


class _MCP:

    def __init__(self, agents, *, app_name):

        # mcp
        self._mcp = FastMCP(app_name,
                            stateless_http=True,
                            json_response=True,
                            streamable_http_path='/')

        for k, v in agents.items():

           self._mcp.add_tool(make_ask(v),
                              name=f'ask_{k}',
                              description=v.description or k)

        # app
        self._app = self._build_app()

    @property
    def app(self):
        return self._app

    def _build_app(self):
        return self._mcp.streamable_http_app()

    def lifespan(self):
        return self._mcp.session_manager.run()


def create_mcp(agents, *, app_name=None):

    mcp = _MCP(agents, app_name=app_name)
    return mcp


