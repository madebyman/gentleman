import os
import re
import yaml

from pydantic import ValidationError

from ..specs import McpConfig, LocalSpec, RemoteSpec
from ..._errors import LoadError


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


def _bullets(errors):
    return '\n  - ' + '\n  - '.join(errors)


def _check_delegates(local_specs, remote_specs):

    known = set(local_specs) | set(remote_specs)
    errors, visited = [], set()

    for k, v in local_specs.items():

        for name in v.delegates:
            if name not in known:
                errors.append(f'{k}: unknown delegate "{name}"')

    def walk(name, trail):

        if name in trail:
            return [f'circular delegation: {" -> ".join((*trail, name))}']

        if name in visited:
            return []

        visited.add(name)

        return [err for v in local_specs[name].delegates if v in local_specs
                    for err in walk(v, (*trail, name))]

    for v in local_specs:
        errors.extend(walk(v, ()))

    return errors


def _expand_env_vars(text):

    def repl(m):
        if (v := os.environ.get(m[1])) is not None:
            return v

        if m[2] is not None:
            return m[2]

        raise LoadError(f'environment variable ${{{m[1]}}} is not defined')

    return re.compile(r'\$\{([^}:]+)(:-([^}]*))?\}').sub(repl, text)


def _label(spec_file_path):
    return f'{spec_file_path.parent.name}/{spec_file_path.name}'


def _load_mcp_servers(mcp_config_file_path):

    if not mcp_config_file_path.exists():
        return {}

    try:
        raw = mcp_config_file_path.read_text(encoding='utf-8')
        return McpConfig.model_validate_json(_expand_env_vars(raw)).mcp_servers

    except (OSError, ValidationError, LoadError) as err:
        raise LoadError(f'{_label(mcp_config_file_path)}: {err}') from err


def _load_yaml(spec_file_path):

    try:
        raw = spec_file_path.read_text(encoding='utf-8')
        return yaml.safe_load(_expand_env_vars(raw)) or {}

    except (OSError, yaml.YAMLError, LoadError) as err:
        raise LoadError(f'{_label(spec_file_path)}: {err}') from err


def _load_local_spec(spec_file_path, *, allow_delegates):

    spec = _load_yaml(spec_file_path)

    if not isinstance(spec, dict):
        raise LoadError(f'{_label(spec_file_path)}: mapping expected')

    metadata = spec.get('metadata', None) or {}

    if not isinstance(metadata, dict):
        raise LoadError(f'{_label(spec_file_path)}: metadata must be a mapping')

    delegates = metadata.get('delegates', [])

    if delegates and not allow_delegates:
        raise LoadError(f'{_label(spec_file_path)}: '
                        'metadata.delegates is only allowed in conductor.yaml')

    mcp_servers = _load_mcp_servers(
            spec_file_path.with_name('mcp_config.json'))

    try:
        return LocalSpec(
                spec=spec, delegates=delegates, mcp_servers=mcp_servers)

    except (ValidationError) as err:
        raise LoadError(f'{_label(spec_file_path)}: {err}') from err


def _load_remote_spec(spec_file_path):

    try:
        return RemoteSpec.model_validate(_load_yaml(spec_file_path))

    except (ValidationError) as err:
        raise LoadError(f'{_label(spec_file_path)}: {err}') from err


def load_specs(agents_dir):

    if not agents_dir.is_dir():
        raise LoadError(f'agents directory not found: {agents_dir}')

    candidates = sorted(v for v in agents_dir.iterdir()
                        if v.is_dir() and not v.name.startswith('.'))

    if not candidates:
        raise LoadError(f'no agents found in {agents_dir}')

    errors, local_specs, remote_specs = [], {}, {}

    for v in candidates:

        if (err := _check_exclusive(v)) is not None:
            errors.append(err)
            continue

        try:

            if (f := v / 'conductor.yaml').exists():
                local_specs[v.name] = _load_local_spec(f, allow_delegates=True)

            elif (f := v / 'agent.yaml').exists():
                local_specs[v.name] = _load_local_spec(f, allow_delegates=False)

            elif (f := v / 'a2a.yaml').exists():
                remote_specs[v.name] = _load_remote_spec(f)

        except (LoadError) as err:
            errors.append(str(err))
            continue

    if errors:
        raise LoadError(f'invalid agent configuration:{_bullets(errors)}')

    if errors := _check_delegates(local_specs, remote_specs):
        raise LoadError(f'invalid agent configuration:{_bullets(errors)}')

    return local_specs, remote_specs

