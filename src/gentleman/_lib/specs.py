from enum import StrEnum
from typing import NamedTuple

from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from pydantic.alias_generators import to_camel

from pydantic_ai import AgentSpec


class Visibility(StrEnum):
    PUBLIC = 'public'
    PRIVATE = 'private'


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
    visibility: Visibility = Visibility.PRIVATE
    mcp_servers: dict[str, StdioServer | HttpServer] = Field(
            default_factory=dict)


class RemoteSpec(BaseModel):

    model_config = ConfigDict(extra='forbid')

    url: HttpUrl
    description: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: float = Field(default=60.0, gt=0)
    visibility: Visibility = Visibility.PRIVATE
    metadata: dict = {}


class Specs(NamedTuple):
    local: dict[str, LocalSpec]
    remote: dict[str, RemoteSpec]
    public: frozenset[str]

    @property
    def keys(self):
        return self.local.keys() | self.remote.keys()

