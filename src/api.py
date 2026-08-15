"""FastAPI wrapper around the Wonka Knowledge Base."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from src import config
from src.rag import ask, retrieve_chunks, serialize_chunk

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Wonka RAG",
    description="Ask the Bedrock Knowledge Base. Nova Lite writes the answer.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    include_chunks: bool = False


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "region": config.AWS_REGION,
        "model": config.BEDROCK_MODEL_ID,
        "knowledge_base_id": config.BEDROCK_KNOWLEDGE_BASE_ID,
    }


@app.post("/ask")
def post_ask(body: AskRequest) -> dict:
    if not config.BEDROCK_KNOWLEDGE_BASE_ID:
        raise HTTPException(status_code=500, detail="BEDROCK_KNOWLEDGE_BASE_ID is not set")
    try:
        return ask(body.question.strip(), include_chunks=body.include_chunks)
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/ask")
def get_ask(q: str, chunks: bool = False) -> dict:
    return post_ask(AskRequest(question=q, include_chunks=chunks))


@app.get("/chunks")
def get_chunks(q: str) -> dict:
    if not config.BEDROCK_KNOWLEDGE_BASE_ID:
        raise HTTPException(status_code=500, detail="BEDROCK_KNOWLEDGE_BASE_ID is not set")
    try:
        results = retrieve_chunks(q.strip())
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "question": q,
        "chunks": [serialize_chunk(item) for item in results],
    }


app.mount("/static", StaticFiles(directory=STATIC), name="static")
