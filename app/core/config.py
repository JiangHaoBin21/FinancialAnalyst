"""Application configuration."""
import os
from dataclasses import dataclass

from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

@dataclass(slots=True)
class Settings:
    """Static settings placeholder for the application."""

    app_name: str = "FinancialAnalyst"
    environment: str = "development"
    database_url: str = os.getenv("DATABASE_URL")
    TuShare_Token: str = os.getenv("TUSHARE_TOKEN")

    def validate(self) -> None:
        missing = []

        if not self.database_url:
            missing.append("database_url")
        if not self.TuShare_Token:
            missing.append("TuShare_Token")

        if missing:
            raise ValueError(f"缺少必要环境变量: {', '.join(missing)}")

settings = Settings()