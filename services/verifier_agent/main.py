"""Verifier agent: evaluates credibility of sources and filters low-quality ones."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.schemas import VerifierRequest, VerifierResponse

app = FastAPI(title="Verifier Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/", response_model=VerifierResponse)
async def verify(request: VerifierRequest):
    """Filter sources: keep credible ones, reject low-quality or off-topic."""
    verified = []
    rejected = []
    for s in request.sources:
        title = (s.get("title") or "").lower()
        url = (s.get("url") or "").lower()
        snippet = (s.get("snippet") or "").lower()
        # Simple heuristics: reject empty, obvious spam, or non-http
        if not url or not url.startswith("http"):
            rejected.append(s)
            continue
        if "spam" in title or "advertisement" in title:
            rejected.append(s)
            continue
        verified.append(s)
    return VerifierResponse(verified=verified, rejected=rejected)
