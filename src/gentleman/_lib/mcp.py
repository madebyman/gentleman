from mcp.server.fastmcp import FastMCP

def build_mcp(agents):

    mcp = FastMCP('gentleman',
                  stateless_http=True,
                  json_response=True,
                  streamable_http_path='/')

    for k, v in agents.items():

        def make_tool(agent):

            async def ask(prompt):
                res = await agent.run(prompt)
                return res.output

            return ask

        mcp.add_tool(make_tool(v),
                     name=f'ask_{k}',
                     description=v.render_description() or k)

    return mcp


