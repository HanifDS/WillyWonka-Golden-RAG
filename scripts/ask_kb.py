"""Ask the Bedrock Knowledge Base from the command line."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from src import config  # noqa: E402
from src.rag import ask, retrieve_chunks, serialize_chunk  # noqa: E402


def print_chunks(results: list[dict]) -> None:
    serialized = [serialize_chunk(item) for item in results]
    if not serialized:
        print("No matching chunks.")
        return
    print("Matching chunks from the Knowledge Base:")
    for i, item in enumerate(serialized, start=1):
        print(f"\n[{i}] score={item['score']} {item['uri']}")
        print((item["text"] or "")[:800])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="+", help="Question to ask the Knowledge Base")
    parser.add_argument(
        "--chunks",
        action="store_true",
        help="Only show retrieved chunks (no model answer)",
    )
    args = parser.parse_args()
    question = " ".join(args.question)

    if not config.BEDROCK_KNOWLEDGE_BASE_ID:
        print("BEDROCK_KNOWLEDGE_BASE_ID is not set in .env")
        return 1

    try:
        if args.chunks:
            print_chunks(retrieve_chunks(question))
            return 0
        print(ask(question)["answer"])
        return 0
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        print("Knowledge Base request failed.")
        print(" ", exc)
        print(" Showing retrieved chunks instead:\n")
        try:
            print_chunks(retrieve_chunks(question))
            return 0
        except (NoCredentialsError, ClientError, BotoCoreError) as inner:
            print(" ", inner)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
