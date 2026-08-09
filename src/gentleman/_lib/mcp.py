from mcp.server.fastmcp import FastMCP

from .a2a import make_ask as make_remote_ask

def make_ask(agent):

    async def ask(prompt):
        res = await agent.run(prompt)
        return res.output

    return ask


def build_mcp(agents, remotes, name):

    mcp = FastMCP(name,
                  stateless_http=True,
                  json_response=True,
                  streamable_http_path='/')

    for k, v in agents.items():
        mcp.add_tool(make_ask(v),
                     name=f'ask_{k}',
                     description=v.render_description() or k)

    for k, v in remotes.items():
        mcp.add_tool(make_remote_ask(v),
                     name=f'ask_{k}',
                     description=v.description or k)

    return mcp


