"""Answer agent: synthesizes final answer with citations using Gemini 2.5 Flash via Vertex AI."""
import os
import json
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.schemas import AnswerRequest, AnswerResponse

app = FastAPI(title="Answer Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PROJECT = os.environ.get("GCP_PROJECT", "")
REGION = os.environ.get("VERTEX_REGION", "us-central1")


def generate_answer(question: str, context: list[dict]) -> tuple[str, list[dict]]:
    """Use Gemini 2.5 Flash to generate answer with citations."""
    context_text = "\n\n".join(
        f"[{i+1}] {c.get('content') or c.get('snippet', '')} (Source: {c.get('url', c.get('source', ''))})"
        for i, c in enumerate(context)
    )
    prompt = f"""Based on the following sources, answer the question. Cite each claim with [1], [2], etc. matching the source index.

Sources:
{context_text}

Question: {question}

Answer with citations:"""
    citations = [{"index": i + 1, "url": c.get("url", c.get("source", "")), "title": c.get("title", c.get("source", ""))} for i, c in enumerate(context)]

    if not PROJECT:
        return (
            f"Demo answer for: {question}. Based on {len(context)} source(s). Configure GCP_PROJECT and Vertex AI for real generation.",
            citations[:5],
        )

    try:
        vertexai.init(project=PROJECT, location=REGION)
        model = GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        answer = response.text if response.text else "No response generated."
        return answer, citations
    except Exception as e:
        return f"Error generating answer: {e}. (Check Vertex AI and Gemini 2.0 Flash availability.)", citations


@app.post("/", response_model=AnswerResponse)
async def answer(request: AnswerRequest):
    """Synthesize answer from context (verified sources + retriever chunks)."""
    context = list(request.context) if request.context else []
    if request.search_results:
        context.extend(request.search_results)
    if not context:
        context = [{"content": "No sources available.", "url": "", "title": "N/A"}]
    answer_text, citations = generate_answer(request.question, context)
    return AnswerResponse(answer=answer_text, citations=citations)
