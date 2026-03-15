"""Search agent: uses web search API (Google Custom Search or SerpAPI) to retrieve articles."""

import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from shared.schemas import SearchRequest, SearchResponse, SearchResult

app = FastAPI(title="Search Agent")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Optional: Google Custom Search JSON API (needs SEARCH_API_KEY = API key + search_engine_id in one JSON)
# Or use SerpAPI: https://serpapi.com/search?q=...&api_key=...
SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")


def search_serpapi(query: str, max_results: int = 5) -> list[SearchResult]:
    """Use SerpAPI Google search (requires SERPAPI_KEY in secret)."""
    try:
        resp = httpx.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": SEARCH_API_KEY, "num": max_results},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for i, r in enumerate(data.get("organic_results", [])[:max_results]):
            results.append(
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("link", ""),
                    snippet=r.get("snippet"),
                )
            )
        return results
    except Exception as e:
        return [SearchResult(title="Search unavailable", url="", snippet=str(e))]


def search_google_custom(query: str, max_results: int = 5) -> list[SearchResult]:
    """Google Custom Search JSON API. Expect SEARCH_API_KEY to be the API key; need cx in env."""
    cx = os.environ.get("GOOGLE_CX", "")
    if not SEARCH_API_KEY or not cx:
        return [
            SearchResult(
                title="(Configure SEARCH_API_KEY and GOOGLE_CX)",
                url="",
                snippet="Web search not configured.",
            )
        ]
    try:
        resp = httpx.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": SEARCH_API_KEY,
                "cx": cx,
                "q": query,
                "num": min(max_results, 10),
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for r in data.get("items", [])[:max_results]:
            results.append(
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("link", ""),
                    snippet=r.get("snippet"),
                )
            )
        return results
    except Exception as e:
        return [SearchResult(title="Search error", url="", snippet=str(e))]


@app.post("/", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Run web search and return results. Set SEARCH_API_KEY + GOOGLE_CX in .env for real search."""
    # If key looks like a SerpAPI key (long alphanumeric), use SerpAPI; else Google Custom Search
    if SEARCH_API_KEY and len(SEARCH_API_KEY) > 50 and " " not in SEARCH_API_KEY:
        results = search_serpapi(request.query, request.max_results)
    else:
        results = search_google_custom(request.query, request.max_results)

    # Only use demo placeholders when web search is not configured at all
    first_snippet = (results[0].snippet or "") if results else ""
    if not SEARCH_API_KEY and ("not configured" in first_snippet or not results):
        results = [
            SearchResult(
                title="Demo result 1",
                url="https://example.com/1",
                snippet="Demo snippet for: " + request.query,
            ),
            SearchResult(
                title="Demo result 2",
                url="https://example.com/2",
                snippet="Additional context.",
            ),
        ][: request.max_results]
    return SearchResponse(results=results)
