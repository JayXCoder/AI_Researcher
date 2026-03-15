# Secrets and Configuration — All in .env

**This repo is safe to push to public GitHub.** All secrets and environment-specific config live in `.env`, which is gitignored and never committed.

## Setup

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and set at least:
   - `GCP_PROJECT` — your Google Cloud project ID
   - `GOOGLE_CX` — Google Programmable Search Engine ID (from your search embed: `cx=...`)
   - `GOOGLE_APPLICATION_CREDENTIALS` — path to your GCP service account JSON key file
   - `SEARCH_API_KEY` — Custom Search API key (GCP Console → Credentials → Create API key; enable Custom Search API) or SerpAPI key

3. **Never commit `.env`** or your `*.json` key file. Add key filenames to `.gitignore` if needed.

## What goes in .env

| Variable                         | Used by                                 | Required                  |
| -------------------------------- | --------------------------------------- | ------------------------- |
| `GCP_PROJECT`                    | Terraform, Docker, run.sh               | Yes (for deploy)          |
| `GOOGLE_CX`                      | search-agent (Programmable Search)      | Yes (for real search)     |
| `GOOGLE_APPLICATION_CREDENTIALS` | gcloud / Terraform auth                 | Yes (for deploy)          |
| `SEARCH_API_KEY`                 | search-agent (Custom Search or SerpAPI) | For real search           |
| `ARTIFACT_REGISTRY_REPO`         | Terraform (after building images)       | Optional                  |
| `IMAGE_TAG`                      | Terraform                               | Optional (default latest) |

## Real answers and real search

- **Answers:** The app uses Vertex AI (Gemini). Enable the **Vertex AI API** for your project (`gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT`) and ensure `GOOGLE_APPLICATION_CREDENTIALS` points to a key with Vertex AI access. Without this you get credential or “model not found” errors.
- **Search:** For real web results instead of “Demo result 1/2”, set **`SEARCH_API_KEY`** in `.env` (and **`GOOGLE_CX`** for Google Custom Search). Create an API key in GCP Console, enable **Custom Search API**, and add the key to `.env`.

## How it works

- **Docker Compose** reads `GCP_PROJECT`, `GOOGLE_CX`, `SEARCH_API_KEY` from `.env`.
- **run.sh** sources `.env` and exports `TF_VAR_project_id`, `TF_VAR_google_cx`, `TF_VAR_secret_search_api_key`, etc., so Terraform never needs secrets in `terraform.tfvars`.
- **terraform.tfvars** contains only placeholders; real values come from `.env` when you run `./run.sh deploy` or `./run.sh deploy-full`.
