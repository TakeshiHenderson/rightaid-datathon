import json
import os
from pathlib import Path
from pydantic_settings import BaseSettings

_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
# Repo root = parent of backend/
_REPO = Path(__file__).parent.parent


class Settings(BaseSettings):
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # JSON array: [{"email":"...","password":"...","name":"...","role":"..."}]
    RIGHTAID_USERS_JSON: str

    # Azure OpenAI — optional; policy brief will return a fallback if not set
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"

    # Paths — defaults resolve relative to repo root for local dev
    # Docker overrides these via ENV in Dockerfile
    PROVINCE_CONFIG_PATH: str = str(_REPO / "model" / "province_master_config.json")
    MODEL_ELIGIBILITY_PATH: str = str(_REPO / "model" / "output" / "xgboost_eligibility_v3.pkl")
    MODEL_ANOMALY_PATH: str = str(_REPO / "model" / "output" / "xgboost_anomaly_v2.pkl")

    model_config = {"env_file": _ENV_FILE}


settings = Settings()


def get_users() -> list[dict]:
    return json.loads(settings.RIGHTAID_USERS_JSON)
