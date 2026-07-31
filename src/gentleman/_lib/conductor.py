# from pydantic_ai import Agent, DeferredToolRequests
# from .loader import load_toolsets
# output_type = [str, DeferredToolRequests]

from pydantic_ai import Tool

# def _make_delegation_tool(name, agent):

def make_delegation_tool(name, agent):

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

    # delegate.__name__ = f'ask_{name}'
    # delegate.__doc__ = agent.render_description() or f'Delegate the task to the {name} agent.'

    # return delegate


# def build_conductor(config_dir, agents, extra_tools=()):

    # conductor = Agent.from_file(config_dir / 'conductor.yaml',
                            # name='conductor',
                            # toolsets=load_toolsets(config_dir),
                            # tools=list(extra_tools),
                            # output_type=output_type)

    # for k, v in agents.items():
        # conductor.tool(_make_delegation_tool(k, v))

    # return conductor

