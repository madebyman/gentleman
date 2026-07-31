from pydantic_settings import BaseSettings, SettingsConfigDict

class CorsSettings(BaseSettings):

    model_config = SettingsConfigDict(env_prefix='GENTLEMAN_CORS_')

    allow_origins: list[str] = ['*']
    allow_methods: list[str] = ['*']
    allow_headers: list[str] = ['*']

    allow_credentials: bool = False


class A2ASettings(BaseSettings):

    model_config = SettingsConfigDict(env_prefix='GENTLEMAN_A2A_')
    base_url: str = 'http://localhost:8000'


