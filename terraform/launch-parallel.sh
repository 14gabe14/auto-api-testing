#!/bin/bash
# Script to launch multiple parallel LlamaRestTest experiments on GCP

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="${GCP_REGION:-us-central1}"
ZONE="${GCP_ZONE:-us-central1-a}"
TOOLS=("llamaresttest" "evomaster" "resttestgen" "schemathesis" "tcases" "arat-rl")
SERVICES=("fdic" "genome-nexus" "language-tool" "ocvn" "ohsome" "omdb" "rest-countries" "spotify" "youtube")
REPO_URL="${REPO_URL:-}"
OMDB_TOKEN="${OMDB_TOKEN:-}"
SPOTIFY_TOKEN="${SPOTIFY_TOKEN:-}"

# Generate experiment configurations
EXPERIMENTS=()
for tool in "${TOOLS[@]}"; do
    for service in "${SERVICES[@]}"; do
        EXPERIMENTS+=("{\"tool\":\"$tool\",\"service\":\"$service\"}")
    done
done

# Create terraform.tfvars with experiment configurations
cat > terraform.tfvars << EOF
project_id = "$PROJECT_ID"
region     = "$REGION"
zone       = "$ZONE"
instance_count = ${#EXPERIMENTS[@]}
repo_url   = "$REPO_URL"
omdb_token = "$OMDB_TOKEN"
spotify_token = "$SPOTIFY_TOKEN"
upload_results = true

experiment_configs = [
$(printf '  %s,\n' "${EXPERIMENTS[@]}" | sed '$s/,$//')
]
EOF

echo "Generated terraform.tfvars with ${#EXPERIMENTS[@]} experiment configurations"
echo "Run 'terraform apply' to create ${#EXPERIMENTS[@]} instances"

