import os
import re

import yaml

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from pydantic_ai import Agent, DeferredToolRequests
from pydantic_ai.mcp import load_mcp_toolsets

class A2AConfig(BaseModel):

    model_config = ConfigDict(extra='forbid')

    url: HttpUrl
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: float = Field(default=60.0, gt=0)
    description: str | None = None


class ConfigError(RuntimeError):
    pass


def _check_exclusive(agent_dir):

    files = [v for v in ('conductor.yaml', 'agent.yaml', 'a2a.yaml')
             if (agent_dir / v).exists()]

    if len(files) > 1:
        return (f'{agent_dir.name}: '
                f'{" and ".join(files)} cannot coexist in the same directory')

    if files == ['a2a.yaml'] and (agent_dir / 'mcp_config.json').exists():
        return (f'{agent_dir.name}: a2a.yaml cannot be accompanied by mcp_config.json '
                '(MCP is configured on the remote side)')

    return None


def _expand_env_vars(text):

    def repl(m):
        if (v := os.environ.get(m[1])) is not None:
            return v

        if m[2] is not None:
            return m[2]

        raise ConfigError(f'environment variable ${{{m[1]}}} is not defined')

    return re.compile(r'\$\{(\w+)(?::?-([^}]*))?\}').sub(repl, text)


def load_toolsets(config_dir):

    mcp_config_file_path = config_dir / 'mcp_config.json'

    if not mcp_config_file_path.exists():
        return []

    toolsets = load_mcp_toolsets(mcp_config_file_path)
    return toolsets


def load_a2a_config(agent_dir):

    text = (agent_dir / 'a2a.yaml').read_text(encoding='utf-8')
    a2a_yaml = yaml.safe_load(_expand_env_vars(text)) or {}

    return A2AConfig.model_validate(a2a_yaml)


def load_agents(config_dir, make_delegation_tool, make_remote_tool):

    if (config_dir / 'conductor.yaml').exists():

        raise ConfigError(
            'config/conductor.yaml is no longer supported: '
            'move it into config/<name>/conductor.yaml with metadata.delegates')

    agents_dirs = sorted(v for v in config_dir.iterdir() if v.is_dir())
    output_type = [str, DeferredToolRequests]

    errors, specs, remote_agents = [], {}, {}

    for v in agents_dirs:

        if (err := _check_exclusive(v)) is not None:
            errors.append(err)
            continue

        # a2a
        if (v / 'a2a.yaml').exists():

            try:
                remote_agents[v.name] = load_a2a_config(v)

            except (Exception) as err:
                errors.append(f'{v.name}/a2a.yaml: {err}')

        # conductor or agent
        elif ((file := v / 'conductor.yaml').exists()
                or (file := v / 'agent.yaml').exists()):

            try:
                spec = yaml.safe_load(file.read_text(encoding='utf-8')) or {}

            except (Exception) as err:
                errors.append(f'{v.name}/{file.name}: {err}')
                continue

            metadata = spec.pop('metadata', None) or {}

            specs[v.name] = {'dir': v, 'spec': spec,
                             'delegates': metadata.get('delegates', [])}

    if errors:
        err_text = '\n  - ' + '\n  - '.join(errors)
        raise ConfigError(f'invalid agent configuration:{err_text}')

    local_agents = {}

    def build(name, trail=()):

        if name in local_agents:
            return local_agents[name]

        if name in trail:
            raise ConfigError(f'circular delegation: {" -> ".join((*trail, name))}')

        entry = specs[name]
        tools = []

        for v in entry['delegates']:

            if v in specs:
                tools.append(make_delegation_tool(v, build(v, (*trail, name))))

            elif v in remote_agents:
                tools.append(make_remote_tool(v, remote_agents[v]))

            else:
                raise ConfigError(f'{name}: unknown delegate "{v}"')

        local_agents[name] = Agent.from_spec(entry['spec'],
                                             name=name,
                                             toolsets=load_toolsets(entry['dir']),
                                             tools=tools,
                                             output_type=output_type)

        return local_agents[name]

    for name in specs:
        build(name)

    return local_agents, remote_agents

