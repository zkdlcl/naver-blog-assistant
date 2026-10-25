from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


def extract_blog_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""

    if "://" not in normalized:
        return normalized.strip("/")

    parsed = urlparse(normalized)
    if parsed.netloc.lower() != "blog.naver.com":
        raise ValueError("TARGET_BLOG_URL must be a blog.naver.com URL")

    parts = [part for part in parsed.path.split("/") if part]
    return parts[0] if parts else ""


def parse_keywords(value: str | None) -> list[str]:
    if not value:
        return []
    return [keyword.strip() for keyword in value.split(",") if keyword.strip()]


@dataclass(frozen=True)
class AppConfig:
    discord_token: str
    target_blog_id: str
    target_blog_url: str
    tracked_keywords: list[str]
    app_password: str
    app_host: str
    app_port: int
    app_data_dir: Path
    watch_rank_interval_minutes: int
    ai_provider: str
    ai_api_key: str
    ai_model: str
    ai_base_url: str

    @property
    def has_target_blog(self) -> bool:
        return bool(self.target_blog_id)

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_api_key and self.ai_model and self.ai_base_url)


def load_config() -> AppConfig:
    load_dotenv()

    target_blog_id = os.getenv("TARGET_BLOG_ID", "").strip()
    target_blog_url = os.getenv("TARGET_BLOG_URL", "").strip()

    if not target_blog_id and target_blog_url:
        target_blog_id = extract_blog_id(target_blog_url)

    if target_blog_id and not target_blog_url:
        target_blog_url = f"https://blog.naver.com/{target_blog_id}"

    ai_provider = os.getenv("AI_PROVIDER", "groq").strip().lower() or "groq"
    ai_base_url = os.getenv("AI_BASE_URL", "").strip()
    if not ai_base_url:
        ai_base_url = {
            "groq": "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
        }.get(ai_provider, "")

    ai_model = os.getenv("AI_MODEL", "").strip()
    if not ai_model and ai_provider == "groq":
        ai_model = "qwen/qwen3-32b"

    return AppConfig(
        discord_token=os.getenv("DISCORD_TOKEN", "").strip(),
        target_blog_id=target_blog_id,
        target_blog_url=target_blog_url,
        tracked_keywords=parse_keywords(os.getenv("TRACKED_KEYWORDS")),
        app_password=os.getenv("APP_PASSWORD", "").strip(),
        app_host=os.getenv("APP_HOST", "127.0.0.1").strip(),
        app_port=int(os.getenv("APP_PORT", "8000")),
        app_data_dir=Path(os.getenv("APP_DATA_DIR", "data")),
        watch_rank_interval_minutes=int(os.getenv("WATCH_RANK_INTERVAL_MINUTES", "60")),
        ai_provider=ai_provider,
        ai_api_key=os.getenv("AI_API_KEY", "").strip(),
        ai_model=ai_model,
        ai_base_url=ai_base_url,
    )
