"""Planner agent: determines how to answer a question and which tools to use."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.schemas import PlannerRequest, PlannerResponse, PlanStep

app = FastAPI(title="Planner Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/", response_model=PlannerResponse)
async def plan(request: PlannerRequest):
    """Produce a plan: which tools to use (search, retriever) and with what queries."""
    question = request.question.strip().lower()
    steps = []

    # Heuristic: always start with search for broad questions, then RAG
    if any(w in question for w in ["what", "how", "why", "when", "where", "who", "latest", "current"]):
        steps.append(PlanStep(tool="search", query=request.question, rationale="Web search for up-to-date information"))
    steps.append(PlanStep(tool="retriever", query=request.question, rationale="RAG retrieval from documents"))

    return PlannerResponse(steps=steps, reasoning="Use search then retriever for comprehensive answer.")
