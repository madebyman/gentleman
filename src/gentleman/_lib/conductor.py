from pydantic_ai import Tool

def make_tool(name, agent):

    async def delegate(ctx, task):
        res = await agent.run(task, usage=ctx.usage)

        if not isinstance(res.output, str):
            return '(This request requires user approval, which is not available in the current configuration.)'

        return res.output

    return Tool(delegate,
                takes_ctx=True,
                name=f'ask_{name}',
                description=(agent.render_description()
                             or f'Delegate the task to the {name} agent.'))
