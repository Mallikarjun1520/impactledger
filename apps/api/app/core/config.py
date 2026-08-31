from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "ImpactLedger API"
    app_version: str = "0.1.0"

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()