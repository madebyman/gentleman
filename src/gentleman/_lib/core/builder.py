from pydantic_ai import Agent, DeferredToolRequests

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from ..agent import LocalAgent, RemoteAgent
from ..ask import make_tool
# from ..._errors import BuildError


_output_type = [str, DeferredToolRequests]


def _build_agent_card(name, spec, base_url):

    description=spec.description or name

    skill_id = f'ask_{name}'
    url = f'{base_url}/{name}'

    metadata = spec.metadata or {}
    agent_version = metadata.get('version', 'unknown')

    skill = AgentSkill(id=skill_id,
                       name=name,
                       description=description,
                       # input_modes=['text/plain'],
                       # output_modes=['text/plain'],
                       tags=[])

    supported_interface = AgentInterface(protocol_binding='JSONRPC',
                                         protocol_version='1.0',
                                         url=url)

    return AgentCard(name=name,
                     description=description,
                     version=agent_version,
                     default_input_modes=['text/plain'],
                     default_output_modes=['text/plain'],
                     capabilities=AgentCapabilities(streaming=True),
                     skills=[skill],
                     supported_interfaces=[supported_interface])


def build_agents(local_specs, remote_specs, *, base_url):

    local_agents, remote_agents = {}, {}

    for k, v in remote_specs.items():
        remote_agents[k] = RemoteAgent.from_spec(
                v, _build_agent_card(k, v, base_url), name=k)

    def build(key):

        if key in local_agents:
            return local_agents[key]

        agent_spec = local_specs[key]

        tools = [make_tool(k, build(k)
                           if k in local_specs else remote_agents[k])
                 for k in agent_spec.delegates]

        agent = Agent.from_spec(agent_spec.spec,
                                name=key,
                                tools=tools,
                                toolsets=agent_spec.toolsets,
                                output_type=_output_type)

        local_agents[key] = LocalAgent(
                agent, _build_agent_card(key, agent_spec.spec, base_url))

        return local_agents[key]

    for k in local_specs:
        build(k)

    return local_agents | remote_agents


