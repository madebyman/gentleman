from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from pydantic.alias_generators import to_camel

from pydantic_ai import AgentSpec


class _McpServer(BaseModel):

    model_config = ConfigDict(extra='forbid',
                              alias_generator=to_camel,
                              populate_by_name=True)

    init_timeout: float | None = None


class StdioServer(_McpServer):
    command: str
    args: list[str] = []
    env: dict[str, str] | None = None
    cwd: str | None = None


class HttpServer(_McpServer):
    url: str
    headers: dict[str, str] | None = None


class McpConfig(BaseModel):
    model_config = ConfigDict(extra='forbid',
                              alias_generator=to_camel,
                              populate_by_name=True)

    mcp_servers: dict[str, StdioServer | HttpServer] = {}


class LocalSpec(BaseModel):

    model_config = ConfigDict(extra='forbid', arbitrary_types_allowed=True)

    spec: AgentSpec
    delegates: list[str] = Field(default_factory=list)

    mcp_servers: dict[str, StdioServer | HttpServer] = Field(
            default_factory=dict)


class RemoteSpec(BaseModel):

    model_config = ConfigDict(extra='forbid')

    url: HttpUrl
    description: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: float = Field(default=60.0, gt=0)
    metadata: dict | None = None

