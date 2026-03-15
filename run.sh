#!/usr/bin/env bash
# Run the Perplexity-style AI Research Assistant locally or deploy to GCP.
# Usage:
#   ./run.sh local        - Start all services with Docker Compose (default)
#   ./run.sh deploy       - Deploy to GCP (Terraform + optional build/push images)
#   ./run.sh deploy-full  - Deploy and build/push all Docker images to Artifact Registry

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if present (for local and for TF_VAR_* in deploy)
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

export GCP_PROJECT="${GCP_PROJECT:-}"
export SEARCH_API_KEY="${SEARCH_API_KEY:-}"
export GOOGLE_CX="${GOOGLE_CX:-}"
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-}"
export ARTIFACT_REGISTRY_REPO="${ARTIFACT_REGISTRY_REPO:-}"
export IMAGE_TAG="${IMAGE_TAG:-latest}"

# ---------- Local: Docker Compose ----------
run_local() {
  if ! docker info &>/dev/null; then
    echo "Error: Docker is not running. Start Docker Desktop (or the Docker daemon) and try again."
    exit 1
  fi
  echo "Starting all services locally (Docker Compose)..."
  echo "  Frontend: http://localhost:3000"
  echo "  Backend:  http://localhost:8080"
  echo ""
  docker compose up --build
}

# ---------- Deploy: Terraform (and optional images) ----------
run_deploy() {
  local do_build="${1:-no}"

  if [ -z "$GCP_PROJECT" ]; then
    if [ -n "$project_id" ]; then
      GCP_PROJECT="$project_id"
    fi
  fi
  if [ -z "$GCP_PROJECT" ]; then
    echo "Error: GCP project ID required. Set GCP_PROJECT in .env or project_id in terraform.tfvars"
    exit 1
  fi

  echo "Using GCP project: $GCP_PROJECT"

  # All Terraform inputs from .env (safe for public repo)
  export TF_VAR_project_id="$GCP_PROJECT"
  export TF_VAR_google_cx="$GOOGLE_CX"
  if [ -n "$SEARCH_API_KEY" ]; then
    export TF_VAR_secret_search_api_key="$SEARCH_API_KEY"
  else
    echo "Warning: SEARCH_API_KEY not set in .env. Search will use placeholder."
  fi
  [ -n "$ARTIFACT_REGISTRY_REPO" ] && export TF_VAR_artifact_registry_repo="$ARTIFACT_REGISTRY_REPO"
  [ -n "$IMAGE_TAG" ] && export TF_VAR_image_tag="$IMAGE_TAG"

  # Ensure gcloud is authenticated and project is set
  if ! gcloud config get-value project &>/dev/null; then
    echo "Error: gcloud not configured. Run: gcloud auth login && gcloud config set project $GCP_PROJECT"
    exit 1
  fi
  gcloud config set project "$GCP_PROJECT" 2>/dev/null || true

  echo "Enabling required APIs..."
  gcloud services enable run.googleapis.com compute.googleapis.com storage.googleapis.com \
    secretmanager.googleapis.com bigquery.googleapis.com aiplatform.googleapis.com \
    artifactregistry.googleapis.com --project="$GCP_PROJECT"

  echo "Running Terraform init..."
  terraform init -input=false

  echo "Running Terraform plan..."
  terraform plan -out=tfplan -input=false

  echo "Apply? (yes/no)"
  read -r confirm
  if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
  fi
  terraform apply -input=false tfplan
  rm -f tfplan

  if [ "$do_build" = "yes" ]; then
    build_and_push_images
  else
    echo "Skipping image build. To build and push images, run: ./run.sh deploy-full"
    echo "Then set ARTIFACT_REGISTRY_REPO (and IMAGE_TAG) in .env and run terraform apply again."
  fi
}

# Build and push all images to Artifact Registry
build_and_push_images() {
  local project_id="${GCP_PROJECT}"
  local region="${REGION:-us-central1}"
  local repo_name="${ARTIFACT_REPO_NAME:-perplexity-demo}"
  local repo="${region}-docker.pkg.dev/${project_id}/${repo_name}"

  echo "Creating Artifact Registry repository (if missing)..."
  gcloud artifacts repositories describe "$repo_name" --location="$region" --project="$project_id" 2>/dev/null \
    || gcloud artifacts repositories create "$repo_name" --repository-format=docker --location="$region" --project="$project_id"

  echo "Building and pushing images (this may take a while)..."
  local backend_url
  backend_url=$(terraform output -raw backend-api-gateway_service_uri 2>/dev/null || echo "http://localhost:8080")

  for name in planner-agent search-agent retriever-agent verifier-agent answer-agent reflection-agent backend-api; do
    local dir="services/$(echo "$name" | sed 's/-/_/g')"
    echo "  Building $name..."
    docker build -t "${repo}/${name}:latest" -f "${dir}/Dockerfile" .
    echo "  Pushing $name..."
    docker push "${repo}/${name}:latest"
  done

  echo "  Building frontend (API_URL=$backend_url)..."
  docker build -t "${repo}/frontend:latest" -f frontend/Dockerfile --build-arg "API_URL=$backend_url" .
  echo "  Pushing frontend..."
  docker push "${repo}/frontend:latest"

  echo ""
  echo "Done. Add to .env:"
  echo "  ARTIFACT_REGISTRY_REPO=${repo}"
  echo "  IMAGE_TAG=latest"
  echo "Then run: ./run.sh deploy (or terraform apply -input=false)"
}

# ---------- Main ----------
case "${1:-local}" in
  local)
    run_local
    ;;
  deploy)
    run_deploy no
    ;;
  deploy-full)
    run_deploy yes
    ;;
  *)
    echo "Usage: $0 {local|deploy|deploy-full}"
    echo "  local        - Docker Compose up (default)"
    echo "  deploy       - Terraform apply only"
    echo "  deploy-full  - Terraform apply + build and push all images"
    exit 1
    ;;
esac
