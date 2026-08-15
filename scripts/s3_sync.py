"""List or download objects from the configured S3 bucket into data/raw."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from src import config  # noqa: E402
from src.aws import iam_session, s3  # noqa: E402


def _auth_hint() -> str:
    profile = config.AWS_PROFILE or "default"
    try:
        ident = iam_session().client("sts").get_caller_identity()
        arn = ident.get("Arn", "")
        return f"profile={profile} identity={arn}"
    except (NoCredentialsError, ClientError, BotoCoreError):
        return f"profile={profile} (could not resolve IAM identity)"


def _relative_key(key: str) -> str:
    prefix = config.S3_PREFIX
    if prefix and key.startswith(prefix):
        return key[len(prefix) :].lstrip("/")
    return key


def iter_keys(client, bucket: str, prefix: str):
    kwargs = {"Bucket": bucket}
    if prefix:
        kwargs["Prefix"] = prefix
    while True:
        resp = client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents") or []:
            key = obj["Key"]
            if key.endswith("/"):
                continue
            yield key, int(obj.get("Size") or 0)
        token = resp.get("NextContinuationToken")
        if not token:
            break
        kwargs["ContinuationToken"] = token


def list_objects() -> int:
    if not config.S3_BUCKET:
        print("S3_BUCKET is not set in .env")
        return 1
    try:
        client = s3()
        count = 0
        for key, size in iter_keys(client, config.S3_BUCKET, config.S3_PREFIX):
            print(f"{size:>10}  {key}")
            count += 1
        print(f"{count} object(s) in s3://{config.S3_BUCKET}/{config.S3_PREFIX}")
        return 0
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        print("Could not list the bucket.")
        print(" ", exc)
        print(" ", _auth_hint())
        print(" S3 needs a valid IAM profile with s3:ListBucket on this bucket.")
        return 1


def download_objects() -> int:
    if not config.S3_BUCKET:
        print("S3_BUCKET is not set in .env")
        return 1
    try:
        client = s3()
        dest_root = config.RAG_DATA_DIR
        dest_root.mkdir(parents=True, exist_ok=True)
        count = 0
        for key, _size in iter_keys(client, config.S3_BUCKET, config.S3_PREFIX):
            relative = _relative_key(key)
            if not relative:
                continue
            dest = dest_root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(config.S3_BUCKET, key, str(dest))
            print(f"downloaded {key} -> {dest}")
            count += 1
        print(f"{count} file(s) saved under {dest_root}")
        return 0
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        print("Could not download from the bucket.")
        print(" ", exc)
        print(" ", _auth_hint())
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download",
        action="store_true",
        help="Copy objects into data/raw (default is list only)",
    )
    args = parser.parse_args()
    return download_objects() if args.download else list_objects()


if __name__ == "__main__":
    raise SystemExit(main())
