from .config import AppConfig


APP_CONFIG: AppConfig | None = None


def set_app_config(config: AppConfig) -> None:
    global APP_CONFIG
    APP_CONFIG = config


def get_app_config() -> AppConfig:
    if APP_CONFIG is None:
        raise RuntimeError("Config not loaded")
    return APP_CONFIG

