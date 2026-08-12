from pydantic_ai import Agent, DeferredToolRequests

from ..ask import local, remote
from ..._errors import BuildError


_output_type = [str, DeferredToolRequests]


def build_agents(local_specs, remote_specs):

    agents = {}

    def build(key):

        if key in agents:
            return agents[key]

        agent_spec = local_specs[key]
        tools = []

        for k in agent_spec.delegates:

            if k in local_specs:
                tools.append(local.make_tool(k, build(k)))

            else:
                tools.append(remote.make_tool(k, remote_specs[k]))

        agents[key] = Agent.from_spec(agent_spec.spec,
                                      name=key,
                                      tools=tools,
                                      toolsets=agent_spec.toolsets,
                                      output_type=_output_type)

        return agents[key]

    for k in local_specs:
        build(k)

    return agents


