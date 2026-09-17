import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    database: Path
    api_key: str = field(default="", repr=False)
    model: str = ""
    analysis_mode: str = "baseline"


def get_settings():
    load_dotenv(ROOT / ".env", override=False)
    database = Path(os.getenv("FITWISE_DB_PATH", "data/demo/fashion_shop.db"))
    if not database.is_absolute():
        database = ROOT / database
    return Settings(database=database, api_key=os.getenv("OPENAI_API_KEY", "").strip(),
                    model=os.getenv("OPENAI_MODEL", "").strip(),
                    analysis_mode=os.getenv("FITWISE_ANALYSIS_MODE", "baseline").strip())
