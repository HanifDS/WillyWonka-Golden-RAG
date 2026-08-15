"""Retrieve from the Bedrock Knowledge Base and write an answer with Nova Lite."""

from __future__ import annotations

from src import config
from src.aws import bedrock_agent_runtime, bedrock_runtime


def chunk_text(item: dict) -> str:
    return ((item.get("content") or {}).get("text") or "").strip()


def chunk_uri(item: dict) -> str:
    loc = item.get("location") or {}
    return ((loc.get("s3Location") or {}).get("uri")) or ""


def serialize_chunk(item: dict) -> dict:
    return {
        "text": chunk_text(item),
        "score": item.get("score"),
        "uri": chunk_uri(item),
    }


def retrieve_chunks(question: str, number_of_results: int = 5) -> list[dict]:
    """Managed KBs need managedSearchConfiguration, not vector search."""
    resp = bedrock_agent_runtime().retrieve(
        knowledgeBaseId=config.BEDROCK_KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": question},
        retrievalConfiguration={
            "managedSearchConfiguration": {"numberOfResults": number_of_results},
        },
    )
    return resp.get("retrievalResults") or []


def generate(prompt: str) -> str:
    resp = bedrock_runtime().converse(
        modelId=config.BEDROCK_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
    )
    parts = ((resp.get("output") or {}).get("message") or {}).get("content") or []
    return "".join(part.get("text", "") for part in parts).strip()


def ask(question: str, include_chunks: bool = False) -> dict:
    chunks = retrieve_chunks(question)
    serialized = [serialize_chunk(item) for item in chunks]
    context = "\n\n".join(item["text"] for item in serialized if item["text"])
    if not context:
        answer = "The Knowledge Base did not return any matching chunks."
    else:
        prompt = (
            "Answer using only the Knowledge Base excerpts below. "
            "If the excerpts are not enough, say you do not know.\n\n"
            f"Excerpts:\n{context}\n\n"
            f"Question: {question}"
        )
        answer = generate(prompt)
    result = {
        "question": question,
        "answer": answer,
        "model": config.BEDROCK_MODEL_ID,
        "knowledge_base_id": config.BEDROCK_KNOWLEDGE_BASE_ID,
    }
    if include_chunks:
        result["chunks"] = serialized
    return result
