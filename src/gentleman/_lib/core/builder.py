from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from fastmcp.client.transports import StdioTransport

from pydantic_ai import Agent, DeferredToolRequests
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import PrefixedToolset

from ..agent import LocalAgent, RemoteAgent
from ..ask import make_tool
from ..specs import StdioServer


_output_type = [str, DeferredToolRequests]
_init_timeout = 30.0


def _build_stdio_toolset(entry, *, init_timeout):

    transport = StdioTransport(command=entry.command,
                               args=entry.args,
                               env=entry.env,
                               cwd=entry.cwd)

    return MCPToolset(transport, init_timeout=init_timeout)


def _build_http_toolset(entry, *, init_timeout):

    return MCPToolset(entry.url,
                      headers=entry.headers,
                      init_timeout=init_timeout)


def _build_toolset(name, entry):

    init_timeout = entry.init_timeout or _init_timeout

    toolset = (_build_stdio_toolset(entry, init_timeout=init_timeout)
               if isinstance(entry, StdioServer) else
               _build_http_toolset(entry, init_timeout=init_timeout))

    return PrefixedToolset(toolset, name)


def _build_agent_card(name, spec, base_url):

    description = spec.description or name

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


def build_agents(spec, *, base_url):

    local_agents, remote_agents = {}, {}

    for k, v in spec.remote.items():
        remote_agents[k] = RemoteAgent.from_spec(
                v, _build_agent_card(k, v, base_url), name=k)

    def build(key):

        if key in local_agents:
            return local_agents[key]

        agent_spec = spec.local[key]

        tools = [make_tool(k, build(k)
                           if k in spec.local else remote_agents[k])
                 for k in agent_spec.delegates]

        toolsets = [_build_toolset(k, v)
                    for k, v in agent_spec.mcp_servers.items()]

        agent = Agent.from_spec(agent_spec.spec,
                                name=key,
                                tools=tools,
                                toolsets=toolsets,
                                output_type=_output_type)

        local_agents[key] = LocalAgent(
                agent, _build_agent_card(key, agent_spec.spec, base_url))

        return local_agents[key]

    for k in spec.local:
        build(k)

    return local_agents | remote_agents

