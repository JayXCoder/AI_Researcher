"""Backend API gateway: orchestrates planner -> search -> retriever -> verifier -> answer -> reflection."""
import os
import uuid
import json
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery

from shared.schemas import QueryRequest, QueryResponse, SourceItem

app = FastAPI(title="Backend API Gateway")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PLANNER_URL = os.environ.get("PLANNER_AGENT_URL", "http://planner-agent:8080")
SEARCH_URL = os.environ.get("SEARCH_AGENT_URL", "http://search-agent:8080")
RETRIEVER_URL = os.environ.get("RETRIEVER_AGENT_URL", "http://retriever-agent:8080")
VERIFIER_URL = os.environ.get("VERIFIER_AGENT_URL", "http://verifier-agent:8080")
ANSWER_URL = os.environ.get("ANSWER_AGENT_URL", "http://answer-agent:8080")
REFLECTION_URL = os.environ.get("REFLECTION_AGENT_URL", "http://reflection-agent:8080")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "")
BIGQUERY_DATASET = os.environ.get("BIGQUERY_DATASET", "perplexity_logs")
BIGQUERY_TABLES = os.environ.get("BIGQUERY_TABLES", "[]")


def log_to_bigquery(log_id: str, query: str, response: str, sources: list[dict]):
    if not GCP_PROJECT or not BIGQUERY_DATASET:
        return
    try:
        table_ids = json.loads(BIGQUERY_TABLES) if isinstance(BIGQUERY_TABLES, str) else BIGQUERY_TABLES
        table_id = table_ids[0] if isinstance(table_ids, list) and table_ids else "query_logs"
        client = bigquery.Client(project=GCP_PROJECT)
        table_ref = f"{GCP_PROJECT}.{BIGQUERY_DATASET}.{table_id}"
        row = {
            "id": log_id,
            "query": query,
            "response": response,
            "sources": json.dumps(sources),
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }
        errors = client.insert_rows_json(table_ref, [row])
        if errors:
            print("BigQuery insert errors:", errors)
    except Exception as e:
        print("BigQuery logging failed:", e)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Run the full pipeline: planner -> search -> retriever -> verifier -> answer -> reflection."""
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Planner
        plan_resp = await client.post(f"{PLANNER_URL.rstrip('/')}/", json={"question": question})
        plan_resp.raise_for_status()
        plan = plan_resp.json()
        steps = plan.get("steps", [])

        search_results = []
        for step in steps:
            if step.get("tool") == "search" and step.get("query"):
                sr = await client.post(
                    f"{SEARCH_URL.rstrip('/')}/",
                    json={"query": step["query"], "max_results": 5},
                )
                if sr.is_success:
                    search_results = sr.json().get("results", [])

        retriever_chunks = []
        for step in steps:
            if step.get("tool") == "retriever" and step.get("query"):
                rr = await client.post(
                    f"{RETRIEVER_URL.rstrip('/')}/",
                    json={"query": step["query"], "top_k": 5},
                )
                if rr.is_success:
                    retriever_chunks = rr.json().get("chunks", [])

        # 2. Verifier (verify search results)
        verified_sources = []
        if search_results:
            verifier_payload = {
                "sources": [{"title": r["title"], "url": r["url"], "snippet": r.get("snippet")} for r in search_results],
                "question": question,
            }
            vr = await client.post(f"{VERIFIER_URL.rstrip('/')}/", json=verifier_payload)
            if vr.is_success:
                verified_sources = vr.json().get("verified", [])

        # 3. Context: verified sources + retriever chunks
        context = []
        for s in verified_sources:
            context.append({"title": s.get("title"), "url": s.get("url"), "snippet": s.get("snippet"), "content": s.get("snippet")})
        for c in retriever_chunks:
            context.append({"content": c.get("content"), "source": c.get("source"), "url": c.get("source")})

        # 4. Answer
        answer_payload = {"question": question, "context": context, "search_results": verified_sources}
        ar = await client.post(f"{ANSWER_URL.rstrip('/')}/", json=answer_payload)
        ar.raise_for_status()
        answer_data = ar.json()
        draft_answer = answer_data.get("answer", "")
        citations = answer_data.get("citations", [])

        # 5. Reflection
        ref_payload = {"question": question, "draft_answer": draft_answer, "citations": citations}
        refr = await client.post(f"{REFLECTION_URL.rstrip('/')}/", json=ref_payload)
        if refr.is_success:
            ref_data = refr.json()
            final_answer = ref_data.get("answer", draft_answer)
            citations = ref_data.get("citations", citations)
        else:
            final_answer = draft_answer

    # Build source list for response
    sources_out = [
        SourceItem(index=c.get("index", i + 1), url=c.get("url", ""), title=c.get("title"))
        for i, c in enumerate(citations)
    ]

    # Log to BigQuery
    log_id = str(uuid.uuid4())
    log_to_bigquery(log_id, question, final_answer, [s.model_dump() for s in sources_out])

    return QueryResponse(answer=final_answer, sources=sources_out)
