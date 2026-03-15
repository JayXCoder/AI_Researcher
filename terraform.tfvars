# All secrets and config live in .env (never commit .env). This file uses placeholders only.
# run.sh sources .env and exports TF_VAR_project_id, TF_VAR_google_cx, TF_VAR_secret_search_api_key for Terraform.

# Placeholders; real values come from .env via run.sh (or set TF_VAR_* yourself)
project_id = "YOUR_GCP_PROJECT_ID"
google_cx   = "YOUR_GOOGLE_CX"

# After ./run.sh deploy-full, set in .env: ARTIFACT_REGISTRY_REPO, IMAGE_TAG (run.sh uses these for Terraform)
# artifact_registry_repo = "us-central1-docker.pkg.dev/YOUR_PROJECT/perplexity-demo"
# image_tag = "latest"
