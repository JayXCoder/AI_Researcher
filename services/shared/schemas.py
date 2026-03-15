"""Shared Pydantic schemas for agent requests/responses."""
from pydantic import BaseModel, Field
from typing import Optional


class PlanStep(BaseModel):
    tool: str
    query: Optional[str] = None
    rationale: Optional[str] = None


class PlannerRequest(BaseModel):
    question: str


class PlannerResponse(BaseModel):
    steps: list[PlanStep]
    reasoning: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = None


class SearchResponse(BaseModel):
    results: list[SearchResult]


class RetrieverRequest(BaseModel):
    query: str
    doc_ids: Optional[list[str]] = None
    top_k: int = 5


class RetrieverChunk(BaseModel):
    content: str
    source: Optional[str] = None
    score: Optional[float] = None


class RetrieverResponse(BaseModel):
    chunks: list[RetrieverChunk]


class VerifierRequest(BaseModel):
    sources: list[dict]  # [{title, url, snippet}, ...]
    question: str


class VerifierResponse(BaseModel):
    verified: list[dict]
    rejected: list[dict]


class AnswerRequest(BaseModel):
    question: str
    context: list[dict]  # verified sources + retriever chunks
    search_results: Optional[list[dict]] = None


class AnswerResponse(BaseModel):
    answer: str
    citations: list[dict]  # [{index, url, title}, ...]


class ReflectionRequest(BaseModel):
    question: str
    draft_answer: str
    citations: list[dict]


class ReflectionResponse(BaseModel):
    answer: str
    citations: list[dict]


class QueryRequest(BaseModel):
    question: str


class SourceItem(BaseModel):
    index: int
    url: str
    title: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
