"""Verify the Python env, boto3, and API-key loading."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402
from src.aws import check_credentials, check_s3  # noqa: E402


def main() -> int:
    print("Python:", sys.version.split()[0])
    print("Project root:", ROOT)
    print("Region:", config.AWS_REGION)
    print("Bedrock model:", config.BEDROCK_MODEL_ID)
    print("Data dir:", config.RAG_DATA_DIR)
    print(
        "Bedrock API key:",
        "set" if config.has_bedrock_api_key() else "not set",
    )
    print(
        "AWS IAM keys in .env:",
        "yes" if config.has_aws_keys_in_env() else "no (will use ~/.aws if present)",
    )
    print("OPENAI_API_KEY:", "set" if config.has_openai_key() else "not set")
    print("ANTHROPIC_API_KEY:", "set" if config.has_anthropic_key() else "not set")

    status = check_credentials()
    failed = False
    if status["ok"]:
        print("boto3 check: ok")
        print("  auth:", status.get("auth"))
        if status.get("account"):
            print("  account:", status["account"])
            print("  identity:", status["arn"])
        if "models" in status:
            print("  Bedrock models visible:", status["models"])
    else:
        failed = True
        print("boto3 check: failed")
        print(" ", status["error"])
        print("Paste the Bedrock API key into AWS_BEARER_TOKEN_BEDROCK in .env, then retry.")

    s3_status = check_s3()
    print("S3 bucket:", config.S3_BUCKET or "(not set)")
    print("S3 profile:", config.AWS_PROFILE or "default")
    if s3_status["ok"]:
        print("S3 check: ok")
        sample = s3_status.get("key_sample") or []
        print("  objects listed:", len(sample), "(sample)")
        for key in sample[:10]:
            print("   ", key)
        if s3_status.get("truncated"):
            print("  ... more objects in the bucket")
    else:
        failed = True
        print("S3 check: failed")
        print(" ", s3_status["error"])
        print(" S3 needs IAM from ~/.aws (or AWS_ACCESS_KEY_ID). Set AWS_PROFILE if the bucket is not on default.")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
