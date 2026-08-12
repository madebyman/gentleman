from pydantic_ai import Tool


APPROVAL_UNAVAILABLE = ('(This request requires user approval, '
                        'which is not available in the current configuration.)')


def _as_text(res):

    if not isinstance(res.output, str):
        return APPROVAL_UNAVAILABLE

    return res.output


# make_ask
def make_ask(agent):

    async def ask(prompt):
        return _as_text(await agent.run(prompt))

    return ask


# make_tool
def make_tool(agent_name, agent):

    async def delegate(ctx, task):
        return _as_text(await agent.run(task, usage=ctx.usage))

    return Tool(delegate,
                takes_ctx=True,
                name=f'ask_{agent_name}',
                description=(
                    agent.render_description()
                    or f'Delegate the task to the {agent_name} agent.'))


