"""Load API keys and runtime settings from .env without hard-coding secrets."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _drop_empty_aws_env() -> None:
    """Blank .env keys must not override ~/.aws (boto3 treats AWS_PROFILE= as a name)."""
    for name in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
    ):
        if not os.getenv(name, "").strip():
            os.environ.pop(name, None)


_drop_empty_aws_env()


AWS_REGION = _env("AWS_REGION") or _env("AWS_DEFAULT_REGION") or "us-east-1"
BEDROCK_API_KEY = _env("AWS_BEARER_TOKEN_BEDROCK")
BEDROCK_MODEL_ID = _env(
    "BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"
)
BEDROCK_EMBEDDING_MODEL_ID = _env(
    "BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
)
OPENAI_API_KEY = _env("OPENAI_API_KEY")
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
RAG_DATA_DIR = ROOT / _env("RAG_DATA_DIR", "data/raw")
RAG_INDEX_DIR = ROOT / _env("RAG_INDEX_DIR", "data/index")
AWS_PROFILE = _env("AWS_PROFILE")
S3_BUCKET = _env("S3_BUCKET")
S3_PREFIX = _env("S3_PREFIX")
BEDROCK_KNOWLEDGE_BASE_ID = _env("BEDROCK_KNOWLEDGE_BASE_ID")


def has_bedrock_api_key() -> bool:
    return bool(BEDROCK_API_KEY)


def has_aws_keys_in_env() -> bool:
    return bool(_env("AWS_ACCESS_KEY_ID") and _env("AWS_SECRET_ACCESS_KEY"))


def has_openai_key() -> bool:
    return bool(OPENAI_API_KEY)


def has_anthropic_key() -> bool:
    return bool(ANTHROPIC_API_KEY)
