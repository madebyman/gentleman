from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from fastmcp.client.transports import StdioTransport

from pydantic_ai import Agent, DeferredToolRequests
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import PrefixedToolset
from pydantic_ai.exceptions import UserError

from ..agent import LocalAgent, RemoteAgent
from ..ask import make_tool
from ..specs import StdioServer
from ..model import resolve_model

from ..._version import DIST_NAME
from ..._errors import BuildError


_output_type = [str, DeferredToolRequests]
_init_timeout = 30.0

_provider_extras = {
    'openai': [
        'openai', 'openai-chat', 'openai-responses',
        # pydantic ai extras whose only sdk is openai
       'openrouter', 'cerebras', 'zai', 'snowflake', 'crusoe',
        # openai-compatible apis
        'ollama', 'alibaba', 'fireworks', 'heroku', 'nebius', 'ovhcloud',
        'sambanova', 'together', 'vercel', 'vllm',
        # needs botocore as well
        'bedrock-mantle',
    ],
    'anthropic': ['anthropic'],
    'google': ['google', 'google-cloud'],
    'bedrock': ['bedrock', 'bedrock-mantle'],
    'xai': ['xai'],
}


def _extras_for(model):
    prefix, sep, _ = (model or '').partition(':')
    return ''.join([k for k, v in _provider_extras.items() if sep and prefix in v])


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


def _build_agent_card(name, *, description, metadata, base_url):

    skill_id = f'ask_{name}'
    url = f'{base_url}/{name}'

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


def build_agents(specs, *, base_url):

    local_agents, remote_agents = {}, {}

    # remote_agents
    for k, v in specs.remote.items():

        agent_card = _build_agent_card(k,
                                       description=v.description,
                                       metadata=v.metadata,
                                       base_url=base_url)

        remote_agents[k] = RemoteAgent.from_spec(v, agent_card, name=k)

    # local_agents
    def build(name):

        if name in local_agents:
            return local_agents[name]

        local_spec = specs.local[name]

        tools = [make_tool(k, build(k)
                           if k in specs.local else remote_agents[k])
                 for k in local_spec.routing.delegates]

        toolsets = [_build_toolset(k, v)
                    for k, v in local_spec.mcp_servers.items()]

        try:
            agent = Agent.from_spec(local_spec.spec,
                                    name=name,
                                    model=resolve_model(local_spec.spec.model),
                                    tools=tools,
                                    toolsets=toolsets,
                                    output_type=_output_type)

        except (ImportError) as err:
            header = (f'{name}/agent.yaml: '
                     'a required package is not installed')

            message = (f'{header}; install "{DIST_NAME}[{extras}]" '
                       f'for model "{local_spec.spec.model}"'
                       if (extras := _extras_for(local_spec.spec.model)) else
                       f'{header}: {err}')

            raise BuildError(message)

        except (UserError) as err:
            raise BuildError(f'{name}/agent.yaml: {err}') from err

        agent_card = _build_agent_card(name,
                                       description=local_spec.description,
                                       metadata=local_spec.metadata,
                                       base_url=base_url)

        local_agents[name] = LocalAgent(agent, agent_card)

        return local_agents[name]

    for k in specs.local:
        build(k)

    return local_agents | remote_agents

