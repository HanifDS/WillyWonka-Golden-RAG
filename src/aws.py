"""boto3 session helpers for the RAG stack (Bedrock, S3, etc.)."""

from __future__ import annotations

import os
from contextlib import contextmanager

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from src.config import AWS_PROFILE, AWS_REGION, S3_BUCKET, S3_PREFIX, has_bedrock_api_key


def session() -> boto3.Session:
    """Region comes from .env. Auth is AWS_BEARER_TOKEN_BEDROCK, IAM keys, or ~/.aws."""
    return boto3.Session(region_name=AWS_REGION)


def iam_session() -> boto3.Session:
    """IAM session for S3 (Bedrock API keys cannot open buckets)."""
    kwargs = {"region_name": AWS_REGION}
    if AWS_PROFILE:
        kwargs["profile_name"] = AWS_PROFILE
    return boto3.Session(**kwargs)


def s3():
    return iam_session().client("s3")


def bedrock_agent_runtime():
    """Knowledge Base Retrieve / RetrieveAndGenerate (needs IAM, not only a Bedrock API key)."""
    return iam_session().client("bedrock-agent-runtime")


def bedrock_runtime():
    return session().client("bedrock-runtime")


@contextmanager
def _without_iam_env():
    """IAM keys in .env beat the Bedrock API key. Hide them for InvokeModel/Converse."""
    saved: dict[str, str] = {}
    for key in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "AWS_SHARED_CREDENTIALS_FILE",
        "AWS_CONFIG_FILE",
    ):
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    os.environ["AWS_EC2_METADATA_DISABLED"] = "true"
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = os.devnull
    os.environ["AWS_CONFIG_FILE"] = os.devnull
    try:
        yield
    finally:
        os.environ.pop("AWS_SHARED_CREDENTIALS_FILE", None)
        os.environ.pop("AWS_CONFIG_FILE", None)
        os.environ.update(saved)


def converse_with_api_key(model_id: str, prompt: str) -> str:
    """Call Claude/Opus with AWS_BEARER_TOKEN_BEDROCK, not sandbox IAM."""
    if not has_bedrock_api_key():
        raise RuntimeError("AWS_BEARER_TOKEN_BEDROCK is not set in .env")
    with _without_iam_env():
        client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        resp = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
        )
    parts = ((resp.get("output") or {}).get("message") or {}).get("content") or []
    return "".join(part.get("text", "") for part in parts).strip()


def bedrock():
    return session().client("bedrock")


def check_credentials() -> dict:
    """Return a small status dict so setup can be verified without leaking secrets."""
    if has_bedrock_api_key():
        try:
            models = bedrock().list_foundation_models().get("modelSummaries", [])
            return {
                "ok": True,
                "auth": "bedrock-api-key",
                "region": AWS_REGION,
                "models": len(models),
            }
        except (NoCredentialsError, ClientError, BotoCoreError) as exc:
            return {"ok": False, "error": str(exc), "region": AWS_REGION}

    try:
        sts = session().client("sts")
        identity = sts.get_caller_identity()
        return {
            "ok": True,
            "auth": "iam",
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
            "region": AWS_REGION,
        }
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        return {"ok": False, "error": str(exc), "region": AWS_REGION}


def check_s3() -> dict:
    """Confirm IAM can reach S3_BUCKET without printing object bodies."""
    if not S3_BUCKET:
        return {"ok": False, "error": "S3_BUCKET is not set in .env"}

    try:
        client = s3()
        client.head_bucket(Bucket=S3_BUCKET)
        kwargs: dict = {"Bucket": S3_BUCKET, "MaxKeys": 20}
        if S3_PREFIX:
            kwargs["Prefix"] = S3_PREFIX
        resp = client.list_objects_v2(**kwargs)
        keys = [obj["Key"] for obj in resp.get("Contents") or []]
        return {
            "ok": True,
            "bucket": S3_BUCKET,
            "prefix": S3_PREFIX or "",
            "region": AWS_REGION,
            "profile": AWS_PROFILE or "default",
            "key_sample": keys,
            "truncated": bool(resp.get("IsTruncated")),
        }
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        return {
            "ok": False,
            "error": str(exc),
            "bucket": S3_BUCKET,
            "region": AWS_REGION,
            "profile": AWS_PROFILE or "default",
        }
