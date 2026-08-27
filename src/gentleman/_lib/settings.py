from pathlib import Path
from typing import ClassVar, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):

    model_config = SettingsConfigDict(env_prefix='GENTLEMAN_APP_')

    # env
    name: str = 'Gentleman'
    origin: str = 'http://localhost:8000'
    agents_dir: Path = Path('agents')
    expose: frozenset[Literal['agui', 'a2a', 'mcp']] = frozenset(
            {'agui','a2a', 'mcp'})

class RemoteSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='GENTLEMAN_REMOTE_')

    # env
    max_hop: int = 8


class CorsSettings(BaseSettings):

    model_config = SettingsConfigDict(env_prefix='GENTLEMAN_CORS_')

    # env
    allow_origins: list[str] = ['*']
    allow_methods: list[str] = ['*']
    allow_headers: list[str] = ['*']
    allow_credentials: bool = False

