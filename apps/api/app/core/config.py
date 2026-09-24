from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "ImpactLedger API"
    app_version: str = "0.2.0"

    supabase_url: str
    supabase_anon_key: str
    supabase_jwt_secret: str
    supabase_service_role_key: str
    database_url: str

    # Blockchain anchor (rulebook §22, ADR-011, ADR-012)
    anchor_adapter: str = "noop"            # "evm" | "noop"
    anchor_chain_id: int = 84532            # Base Sepolia
    anchor_rpc_url: str = "https://sepolia.base.org"
    anchor_contract_address: str = ""
    anchor_runtime_private_key: str = ""
    anchor_batch_interval_seconds: int = 300
    anchor_max_pending_events: int = 512
    anchor_confirmations_required: int = 2

    # LLM + OCR (rulebook §12; interfaces default to noop)
    ocr_provider: str = "noop"
    llm_provider: str = "noop"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
