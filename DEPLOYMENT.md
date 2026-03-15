# Perplexity-Style AI Research Assistant — Deployment Guide

This document describes how to run the system **locally with Docker Compose** and then **deploy to Google Cloud** with Terraform.

## Architecture Overview

- **Frontend**: Flutter web — search bar, answer panel, sources list (Perplexity-style citations).
- **Backend API**: FastAPI gateway that orchestrates the agent pipeline.
- **Agents** (each a Cloud Run microservice):
  1. **planner-agent** — Decides how to answer and which tools to use.
  2. **search-agent** — Web search (Google Custom Search or SerpAPI).
  3. **retriever-agent** — RAG with Gemini embeddings (in-memory vector store for demo).
  4. **verifier-agent** — Filters low-quality sources.
  5. **answer-agent** — Gemini 2.0 Flash to synthesize answer with citations.
  6. **reflection-agent** — Second pass to improve clarity.

**Flow:** User question → backend-api → planner → search → retriever → verifier → answer → reflection → response + sources. Queries are logged to BigQuery.

---

## 1. Run Locally with Docker Compose

### Prerequisites

- Docker and Docker Compose
- (Optional) GCP project for Vertex AI / BigQuery: set `GCP_PROJECT` and optionally `SEARCH_API_KEY` in `.env`

### Steps

1. **From the repo root**, create a `.env` file (optional):

   ```bash
   # Optional: for Vertex AI (Gemini) and BigQuery logging
   GCP_PROJECT=your-gcp-project-id
   # Optional: SerpAPI key or Google Custom Search API key for real web search
   SEARCH_API_KEY=your-serpapi-or-cse-key
   ```

2. **Build and run all services:**

   ```bash
   docker compose up --build
   ```

3. **Open the app:**
   - Frontend: **http://localhost:3000**
   - Backend API: **http://localhost:8080**
   - Agent ports (for debugging): 8081–8086

4. **Test:** Type a question in the search bar and submit. You should get an answer and a sources list. Without `GCP_PROJECT` or `SEARCH_API_KEY`, the app still runs with demo/fallback behavior.

---

## 2. Deploy to Google Cloud with Terraform

### Prerequisites

- Google Cloud SDK (`gcloud`) installed and authenticated.
- Terraform >= 1.x.
- A GCP project with billing enabled.

### One-time setup

1. **Set your project and enable APIs:**

   ```bash
   export PROJECT_ID=your-gcp-project-id
   gcloud config set project $PROJECT_ID
   gcloud services enable run.googleapis.com compute.googleapis.com storage.googleapis.com secretmanager.googleapis.com bigquery.googleapis.com aiplatform.googleapis.com
   ```

2. **Configure Terraform variables:**

   Edit `terraform.tfvars`:

   ```hcl
   project_id = "your-gcp-project-id"
   # After building images (step 3), set:
   # artifact_registry_repo = "us-central1-docker.pkg.dev/your-gcp-project-id/perplexity-demo"
   # image_tag = "latest"
   ```

3. **Create Artifact Registry and build/push images:**

   ```bash
   gcloud artifacts repositories create perplexity-demo --repository-format=docker --location=us-central1
   ```

   From the **repo root**, build and push each image (replace `$PROJECT_ID` and `$REGION`):

   ```bash
   export REGION=us-central1
   for name in planner-agent search-agent retriever-agent verifier-agent answer-agent reflection-agent backend-api; do
     dir=services/$(echo $name | sed 's/-/_/g')
     docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/perplexity-demo/${name}:latest -f ${dir}/Dockerfile .
     docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/perplexity-demo/${name}:latest
   done
   ```

   Build and push the **Flutter** frontend (set `API_URL` to your backend Cloud Run URL; use a placeholder if not yet deployed):

   ```bash
   docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/perplexity-demo/frontend:latest \
     -f frontend/Dockerfile \
     --build-arg API_URL=https://backend-api-XXXXXX-uc.a.run.app .
   docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/perplexity-demo/frontend:latest
   ```

4. **Update Terraform with image repo and apply:**

   In `terraform.tfvars`:

   ```hcl
   project_id                = "your-gcp-project-id"
   artifact_registry_repo     = "us-central1-docker.pkg.dev/your-gcp-project-id/perplexity-demo"
   image_tag                 = "latest"
   ```

   Then:

   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

5. **Configure Secret Manager (search API key):**

   ```bash
   gcloud secrets versions add latest --secret=perplexity-secrets --data-file=- <<< "your-serpapi-or-google-cse-key"
   ```

6. **Get the frontend URL:**

   ```bash
   terraform output frontend_url
   # or
   terraform output lb-global-lb-frontend_external_ip
   ```

   Open `https://<external_ip>` (or the URL from `frontend_url`). For production, attach a domain and SSL via the load balancer.

---

## 3. Folder Structure (Reference)

```
.
├── main.tf                 # Terraform: LB, Cloud Run, GCS, BigQuery, Secret Manager
├── variables.tf
├── outputs.tf
├── providers.tf
├── terraform.tfvars
├── docker-compose.yml      # Local run
├── DEPLOYMENT.md           # This file
├── services/
│   ├── shared/
│   │   └── schemas.py      # Pydantic models
│   ├── backend_api/        # FastAPI gateway
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── planner_agent/
│   ├── search_agent/
│   ├── retriever_agent/
│   ├── verifier_agent/
│   ├── answer_agent/
│   └── reflection_agent/
└── frontend/               # Flutter web
    ├── lib/
    │   └── main.dart
    ├── web/
    │   └── index.html
    ├── pubspec.yaml
    ├── nginx.conf
    └── Dockerfile
```

---

## 4. Optional: Run Frontend and Backend Locally (No Docker)

- **Backend (from repo root):**

  ```bash
  export PLANNER_AGENT_URL=http://localhost:8081
  export SEARCH_AGENT_URL=http://localhost:8082
  export RETRIEVER_AGENT_URL=http://localhost:8083
  export VERIFIER_AGENT_URL=http://localhost:8084
  export ANSWER_AGENT_URL=http://localhost:8085
  export REFLECTION_AGENT_URL=http://localhost:8086
  cd services/backend_api && pip install -r requirements.txt && uvicorn main:app --port 8080
  ```

- **Agents:** In separate terminals, run each agent (e.g. `cd services/planner_agent && uvicorn main:app --port 8081`), and so on for 8082–8086.

- **Frontend (Flutter):**

  ```bash
  cd frontend
  flutter pub get
  flutter run -d chrome --web-browser-flag "--disable-web-security"
  ```

  Open http://localhost:3000 (or the port Flutter prints). The app uses `http://localhost:8080` as the API URL by default (override with `--dart-define=API_URL=...` when building).

---

## 5. Troubleshooting

- **CORS:** Backend and agents allow all origins for demo; tighten for production.
- **Cloud Run 403:** Ensure the load balancer has permission to invoke the frontend service (`roles/run.invoker`).
- **Vertex AI / Gemini:** Enable the Vertex AI API and use a region where Gemini 2.0 Flash is available (e.g. `us-central1`).
- **BigQuery:** The backend needs `roles/bigquery.dataEditor` on the dataset; Terraform grants this to the backend service account.
- **Search:** Without `SEARCH_API_KEY`, the search agent returns demo results. Use SerpAPI or Google Custom Search and store the key in Secret Manager.

- **Flutter Docker build:** The frontend image uses `ghcr.io/cirruslabs/flutter:stable`. If the build fails (e.g. Flutter version or disk space), build the Flutter web app locally and serve the output with a simple nginx image:

  ```bash
  cd frontend && flutter build web --dart-define=API_URL=https://your-backend.run.app
  docker build -t frontend -f frontend/Dockerfile.simple .  # optional Dockerfile that only copies build/web
  ```

  Or use a pre-built Flutter SDK Docker image that matches your local Flutter version.
