#!/bin/bash
# Script to collect results from all instances and download from Cloud Storage

set -e

# Get results path from terraform output
RESULTS_PATH=$(terraform output -raw results_path 2>/dev/null || echo "")

if [ -z "$RESULTS_PATH" ]; then
    echo "Error: Could not get results path from terraform output"
    echo "Make sure you've run 'terraform apply' and are in the terraform directory"
    exit 1
fi

LOCAL_RESULTS_DIR="./collected-results"

echo "Collecting results from $RESULTS_PATH..."

# Create local directory
mkdir -p "$LOCAL_RESULTS_DIR"

# Download all results
gsutil -m cp -r "${RESULTS_PATH}*" "$LOCAL_RESULTS_DIR/" || {
    echo "Warning: Some results may not have been uploaded yet"
}

echo "Results collected in $LOCAL_RESULTS_DIR/"
echo "Structure: $LOCAL_RESULTS_DIR/<tool>/<service>/<run-id>/"

