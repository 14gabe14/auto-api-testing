#!/bin/bash
# Script to collect results from all instances and download from Cloud Storage

set -e

BUCKET_NAME="${1:-}"
if [ -z "$BUCKET_NAME" ]; then
    echo "Usage: $0 <bucket-name>"
    echo "Get bucket name from: terraform output bucket_name"
    exit 1
fi

LOCAL_RESULTS_DIR="./collected-results"

echo "Collecting results from gs://$BUCKET_NAME/results/..."

# Create local directory
mkdir -p "$LOCAL_RESULTS_DIR"

# Download all results
gsutil -m cp -r "gs://$BUCKET_NAME/results/*" "$LOCAL_RESULTS_DIR/" || {
    echo "Warning: Some results may not have been uploaded yet"
}

echo "Results collected in $LOCAL_RESULTS_DIR/"
echo "Structure: $LOCAL_RESULTS_DIR/<tool>/<service>/<run-id>/"

