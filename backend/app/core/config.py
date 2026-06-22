from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Dealer Paint Ordering System"
    api_prefix: str = "/api"
    database_url: str = Field(default="sqlite:///./dev.db", alias="DATABASE_URL")
    cors_origins: List[str] = Field(default=["http://localhost:5173", "http://127.0.0.1:5173"])
    auth_secret: str = Field(default="change-me-in-production", alias="AUTH_SECRET")
    token_ttl_seconds: int = 60 * 60 * 12
    default_carrier: str = Field(default="sf", alias="DEFAULT_CARRIER")
    shipper_name: str = Field(default="", alias="SHIPPER_NAME")
    shipper_phone: str = Field(default="", alias="SHIPPER_PHONE")
    shipper_address: str = Field(default="", alias="SHIPPER_ADDRESS")

    sf_app_id: str = Field(default="", alias="SF_APP_ID")
    sf_app_secret: str = Field(default="", alias="SF_APP_SECRET")
    sf_api_url: str = Field(default="", alias="SF_API_URL")
    sf_track_url: str = Field(default="", alias="SF_TRACK_URL")
    sf_webhook_secret: str = Field(default="", alias="SF_WEBHOOK_SECRET")
    sf_sign_algorithm: str = Field(default="hmac-sha256", alias="SF_SIGN_ALGORITHM")
    sf_partner_id: str = Field(default="", alias="SF_PARTNER_ID")
    sf_check_word: str = Field(default="", alias="SF_CHECK_WORD")
    sf_gateway_url: str = Field(default="https://sfapi.sf-express.com/std/service", alias="SF_GATEWAY_URL")
    sf_create_service_code: str = Field(default="EXP_RECE_CREATE_ORDER", alias="SF_CREATE_SERVICE_CODE")
    sf_track_service_code: str = Field(default="EXP_RECE_SEARCH_ROUTES", alias="SF_TRACK_SERVICE_CODE")
    sf_pay_method: int = Field(default=1, alias="SF_PAY_METHOD")
    sf_express_type_id: int = Field(default=1, alias="SF_EXPRESS_TYPE_ID")

    jd_app_key: str = Field(default="", alias="JD_APP_KEY")
    jd_app_secret: str = Field(default="", alias="JD_APP_SECRET")
    jd_token_url: str = Field(default="", alias="JD_TOKEN_URL")
    jd_refresh_token: str = Field(default="", alias="JD_REFRESH_TOKEN")
    jd_api_url: str = Field(default="", alias="JD_API_URL")
    jd_track_url: str = Field(default="", alias="JD_TRACK_URL")
    jd_webhook_secret: str = Field(default="", alias="JD_WEBHOOK_SECRET")
    jd_gateway_url: str = Field(default="https://api.jd.com/routerjson", alias="JD_GATEWAY_URL")
    jd_create_method: str = Field(default="", alias="JD_CREATE_METHOD")
    jd_track_method: str = Field(default="", alias="JD_TRACK_METHOD")
    jd_access_token: str = Field(default="", alias="JD_ACCESS_TOKEN")
    jd_sign_method: str = Field(default="md5", alias="JD_SIGN_METHOD")
    jd_version: str = Field(default="2.0", alias="JD_VERSION")

    yimi_app_key: str = Field(default="", alias="YIMI_APP_KEY")
    yimi_app_secret: str = Field(default="", alias="YIMI_APP_SECRET")
    yimi_api_url: str = Field(default="", alias="YIMI_API_URL")
    yimi_track_url: str = Field(default="", alias="YIMI_TRACK_URL")
    yimi_webhook_secret: str = Field(default="", alias="YIMI_WEBHOOK_SECRET")
    yimi_gateway_url: str = Field(default="", alias="YIMI_GATEWAY_URL")
    yimi_create_method: str = Field(default="", alias="YIMI_CREATE_METHOD")
    yimi_track_method: str = Field(default="", alias="YIMI_TRACK_METHOD")

    carrier_timeout_seconds: float = 8.0
    carrier_retry_attempts: int = 3
    carrier_retry_backoff_seconds: float = 0.8

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
