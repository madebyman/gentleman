from mcp.server.fastmcp import FastMCP

from ..ask import local, remote


class _MCP:

    def __init__(self, local_agents, remote_specs, *, app_name):

        # mcp
        self._mcp = FastMCP(app_name,
                            stateless_http=True,
                            json_response=True,
                            streamable_http_path='/')

        for k, v in local_agents.items():
           self._mcp.add_tool(local.make_ask(v),
                              name=f'ask_{k}',
                              description=v.render_description() or k)

        for k, v in remote_specs.items():
            self._mcp.add_tool(remote.make_ask(v),
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


def create_mcp(local_agents, remote_specs, *, app_name=None):

    mcp = _MCP(local_agents, remote_specs, app_name=app_name)
    return mcp


