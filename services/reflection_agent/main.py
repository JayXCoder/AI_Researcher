"""Reflection agent: second pass to improve clarity and factual grounding."""
import os
import vertexai
from vertexai.generative_models import GenerativeModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.schemas import ReflectionRequest, ReflectionResponse

app = FastAPI(title="Reflection Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PROJECT = os.environ.get("GCP_PROJECT", "")
REGION = os.environ.get("VERTEX_REGION", "us-central1")


def reflect(question: str, draft: str, citations: list[dict]) -> tuple[str, list[dict]]:
    """Improve draft answer: clearer, more factual, keep citations."""
    prompt = f"""Improve this answer for clarity and factual grounding. Keep the same citation indices [1], [2], etc.

Original question: {question}

Draft answer:
{draft}

Improved answer (with same citations):"""
    if not PROJECT:
        return draft, citations

    try:
        vertexai.init(project=PROJECT, location=REGION)
        model = GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        improved = response.text if response.text else draft
        return improved, citations
    except Exception:
        return draft, citations


@app.post("/", response_model=ReflectionResponse)
async def reflect_post(request: ReflectionRequest):
    """Return improved answer and same citations."""
    answer, citations = reflect(request.question, request.draft_answer, request.citations)
    return ReflectionResponse(answer=answer, citations=citations)
