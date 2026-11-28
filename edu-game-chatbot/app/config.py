"""Cấu hình ứng dụng, đọc từ .env. (T02)"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    design_model: str = "gpt-6-sol"
    codegen_model: str = "gpt-6-sol"
    fix_model: str = "gpt-6-sol"
    question_model: str = "gpt-6-sol"
    intake_model: str = "gpt-6-sol"
    llm_timeout_s: int = 120
    llm_max_retries: int = 2

    # Vòng lặp
    max_fix_attempts: int = 2
    max_revision_rounds: int = 10
    default_num_questions: int = 10

    # Giới hạn đầu vào
    max_doc_chars: int = 60_000
    max_upload_mb: int = 10
    max_files_per_session: int = 5

    # Kiểm thử N4
    playwright_timeout_ms: int = 10_000
    headless: bool = True

    # Thư mục & MAIN
    sessions_dir: Path = Path("sessions")
    output_dir: Path = Path("output")
    main_inbox_dir: Path = Path("main_inbox")
    main_webhook_url: str | None = None

    def ensure_dirs(self) -> None:
        """Tạo sessions_dir, output_dir, main_inbox_dir nếu chưa có."""
        raise NotImplementedError


def get_settings() -> Settings:
    """Trả về Settings dùng chung (bọc lru_cache), đã gọi ensure_dirs()."""
    raise NotImplementedError
