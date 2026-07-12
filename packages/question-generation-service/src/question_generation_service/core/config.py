from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    DATABASE_URL: str
    MISTRAL_API_KEY: str
    MISTRAL_MODEL: str = "mistral-large-latest"
    # Cheap/fast model for lightweight NLU (e.g. quiz-length interpretation).
    MISTRAL_FAST_MODEL: str = "mistral-small-latest"
    # See docs/architecture/question-diversity-and-dedup.md — 1024-dim vectors,
    # used for question/concept similarity checks.
    MISTRAL_EMBED_MODEL: str = "mistral-embed"
    # pgvector cosine distance: 0 = identical, up to 2 = opposite (distance =
    # 1 - cosine similarity, so 0.15 ~= reject anything more than 85% similar).
    # Conservative starting points — tune independently per reviewing what
    # actually gets rejected in practice; question text and concept names are
    # different enough in length/entropy that they likely won't converge on
    # the same value.
    QUESTION_SIMILARITY_DISTANCE_THRESHOLD: float = 0.15
    CONCEPT_SIMILARITY_DISTANCE_THRESHOLD: float = 0.15
    COGNITO_ISSUER: str
    COGNITO_CLIENT_ID: str
    DEBUG: bool = False
    REDIS_URL: str = "redis://localhost:6379"
    # Off by default so tests/tooling never spin workers; compose sets it on.
    ENABLE_BACKGROUND_WORKERS: bool = False

    # Routes generation/judge calls through Mistral's Batch API (50% cheaper,
    # minutes-to-hours turnaround) instead of synchronous calls. Requires a
    # paid plan — the free tier 402s on batch job creation. Interactive calls
    # (wizard turns, quiz-length parsing) always stay synchronous regardless.
    MISTRAL_BATCH_MODE: bool = False
    MISTRAL_BATCH_POLL_INTERVAL_S: float = 10.0
    MISTRAL_BATCH_TIMEOUT_H: int = 24

    # Thema self-consistency decision gate (vote-share over n samples).
    THEMA_T_HIGH: float = 0.6  # min winner vote share to skip the picker
    THEMA_MARGIN: float = 0.4  # min lead of winner over runner-up
    THEMA_T_LOW: float = 0.2  # at/below this the result is too scattered to use

    # Looser gate for refine() — the learner already disambiguated once, so a
    # weak plurality there is more likely paraphrase noise than real ambiguity.
    THEMA_REFINE_T_HIGH: float = 0.4
    THEMA_REFINE_MARGIN: float = 0.2

    model_config = SettingsConfigDict(env_file=str(ENV_PATH), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
