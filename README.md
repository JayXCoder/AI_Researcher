# AI Research Assistant

Query the web and get answers with cited sources. A multi-agent pipeline runs search, retrieval, verification, and synthesis; the UI is a single-page Flutter app.

---

## What this app does

You type a question in the search bar. The app:

1. **Sends the question** to a backend API, which orchestrates several specialized agents in sequence.
2. **Planner** — Decides how to answer (e.g. “run web search” and “retrieve from knowledge base”) and produces a short list of steps.
3. **Search** — Calls a web search API (Google Custom Search or SerpAPI) with the planner’s search query and returns titles, URLs, and snippets.
4. **Retriever** — Uses embeddings (Vertex AI) to pull relevant chunks from a document store (in-memory for the demo; can be backed by Vector Search or a vector DB). These chunks add context on top of web results.
5. **Verifier** — Filters low-quality or off-topic items so only useful sources are passed to the answer step.
6. **Answer** — Takes the question plus the verified search results and retriever chunks, and uses Vertex AI (Gemini 2.5 Flash) to write a single answer with inline citations like [1], [2] that map to the source list.
7. **Reflection** — Optional second pass that improves clarity and factual grounding while keeping the same citation indices.

The frontend shows the final answer and a **Sources** list: each citation is a link (title + URL) so you can open the original page. Optionally, queries and responses are logged to BigQuery for analytics.

**In short:** question in → planner → search + retrieval → verification → generated answer with citations → optional reflection → answer and clickable sources in the UI.

---

## Technologies

Technologies used across the codebase:

<p align="center">
  <img src="https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white" alt="Flutter" />
  <img src="https://img.shields.io/badge/Dart-0175C2?style=for-the-badge&logo=dart&logoColor=white" alt="Dart" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white" alt="Google Cloud" />
  <img src="https://img.shields.io/badge/Vertex_AI-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white" alt="Vertex AI" />
  <img src="https://img.shields.io/badge/Terraform-7B42BC?style=for-the-badge&logo=terraform&logoColor=white" alt="Terraform" />
  <img src="https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white" alt="Nginx" />
</p>

| Area                 | Technology                                   | Role                                                         |
| -------------------- | -------------------------------------------- | ------------------------------------------------------------ |
| **Frontend**         | Flutter, Dart                                | Single-page web UI (search bar, answer panel, source links). |
| **Frontend serve**   | Nginx                                        | Serves the built Flutter web app in production/Docker.       |
| **Backend**          | Python, FastAPI, Pydantic                    | API gateway and all agents; request/response schemas.        |
| **HTTP client**      | httpx                                        | Backend calls to search APIs and between agents.             |
| **Search**           | Google Custom Search API / SerpAPI           | Web search results (titles, URLs, snippets).                 |
| **LLM & embeddings** | Vertex AI (Gemini 2.5 Flash, text-embedding) | Answer generation, reflection, and retriever embeddings.     |
| **Analytics**        | BigQuery                                     | Optional logging of queries and responses.                   |
| **Runtime**          | Docker, Docker Compose                       | Local run of frontend + backend + all agents.                |
| **Deploy**           | Terraform, Cloud Run, Artifact Registry      | GCP deployment and container images.                         |

---

## Quick start

**Requirements:** Docker and Docker Compose.

```bash
cp .env.example .env
# Edit .env: set GCP_PROJECT, GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON).
# For real web search, add SEARCH_API_KEY and GOOGLE_CX. See SECRETS_AND_CONFIG.md.

./run.sh local
```

- **App:** http://localhost:3000
- **API:** http://localhost:8080

Without GCP credentials the answer agent will fail; without a search API key you get placeholder search results.

---

## Config

- **`.env`** — All secrets and project config. Copy from `.env.example`. Never commit `.env`.
- **[SECRETS_AND_CONFIG.md](SECRETS_AND_CONFIG.md)** — What each env var does and how to get keys.
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Local Docker Compose and GCP deploy (Terraform).

---

## Repo layout

```
├── frontend/          # Flutter web app
├── services/          # Backend + agents (planner_agent, search_agent, …)
│   └── shared/        # Shared schemas
├── docker-compose.yml
├── run.sh             # local | deploy | deploy-full
└── .env               # Your config (gitignored)
```

---

## License

See repository license file.
