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
    admin_ids: set[int]

    @staticmethod
    def load(path: Path, env_path: Path | None = None) -> "AppConfig":
        if env_path and env_path.exists():
            load_dotenv(env_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("Set BOT_TOKEN in .env (see .env.example).")
        admin_raw = os.getenv("ADMIN_IDS", "")
        admin_ids: set[int] = set()
        if admin_raw:
            for part in admin_raw.replace(";", ",").split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    admin_ids.add(int(part))
                except ValueError:
                    continue
        return AppConfig(bot_token=token, raw=data, admin_ids=admin_ids)

