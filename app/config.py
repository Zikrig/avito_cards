import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass
class AppConfig:
    bot_token: str
    raw: dict[str, Any]

    @staticmethod
    def load(path: Path, env_path: Path | None = None) -> "AppConfig":
        if env_path and env_path.exists():
            load_dotenv(env_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("Set BOT_TOKEN in .env (see .env.example).")
        return AppConfig(bot_token=token, raw=data)

