from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from pydantic_ai import AgentSpec

class LocalSpec(BaseModel):

    model_config = ConfigDict(extra='forbid', arbitrary_types_allowed=True)

    spec: AgentSpec
    delegates: list[str] = Field(default_factory=list)
    toolsets: list = Field(default_factory=list)
    # version: str = 'unknown'


class RemoteSpec(BaseModel):

    model_config = ConfigDict(extra='forbid')

    url: HttpUrl
    description: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: float = Field(default=60.0, gt=0)
    # version: str = 'unknown'
