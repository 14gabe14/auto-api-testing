#! /bin/bash

SERVICE="youtube"
PORT=9009

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SPEC_PATH="$PROJECT_ROOT/specs/openapi_json/${SERVICE}.json"

"$SCRIPT_DIR/../run_tool.sh" "$SERVICE" "$PORT" "$SPEC_PATH"
