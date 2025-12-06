#! /bin/bash

SERVICE="$1"
PORT="$2"
SPEC_PATH="$3"

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$ROOT_DIR/../.." && pwd)"

API_DIR="$ROOT_DIR/apis/experiment-api"
SPEC_DIR="$API_DIR/specifications"
DICT_DIR="$API_DIR/dictionaries"

PY_VENV="$PROJECT_ROOT/venv/bin/activate"
JAVA_ENV="$PROJECT_ROOT/java11.env"

RUN_MAX_SECONDS=${RUN_MAX_SECONDS:-3600}
PY_MAX_SECONDS=${DEEPREST_MAX_SECONDS:-3500}

if [ -z "$SERVICE" ] || [ -z "$PORT" ] || [ -z "$SPEC_PATH" ]; then
    echo "Usage: $0 <service> <port> <spec-path>"
    exit 1
fi

if [ ! -f "$SPEC_PATH" ]; then
    echo "Specification not found at $SPEC_PATH"
    exit 1
fi

cleanup() {
    kill "$PY_PID" 2>/dev/null || true
    kill "$JAVA_PID" 2>/dev/null || true
    pkill -P "$PY_PID" 2>/dev/null || true
    pkill -P "$JAVA_PID" 2>/dev/null || true
    rm -f "$ROOT_DIR/j2p" "$ROOT_DIR/p2j"
}
trap cleanup EXIT

# Prepare environment
rm -rf "$API_DIR"
mkdir -p "$SPEC_DIR" "$DICT_DIR"

cp "$SPEC_PATH" "$SPEC_DIR/${SERVICE}-openapi.json"

DICT_SOURCE="$PROJECT_ROOT/specs/dictionaries/${SERVICE}-llm.json"
if [ -f "$DICT_SOURCE" ]; then
    cp "$DICT_SOURCE" "$DICT_DIR/llm.json"
fi

cat > "$API_DIR/api-config.yml" <<EOF
specificationFileName: ${SERVICE}-openapi.json
host: http://localhost:${PORT}
EOF

cat > "$SPEC_DIR/api-config.yml" <<EOF
specificationFileName: ${SERVICE}-openapi.json
host: http://localhost:${PORT}
EOF

rm -f "$ROOT_DIR/j2p" "$ROOT_DIR/p2j"
mkfifo "$ROOT_DIR/j2p" 2>/dev/null || true
mkfifo "$ROOT_DIR/p2j" 2>/dev/null || true

# Activate envs
if [ -f "$PY_VENV" ]; then
    # shellcheck source=/dev/null
    source "$PY_VENV"
fi

if [ -f "$JAVA_ENV" ]; then
    # shellcheck source=/dev/null
    . "$JAVA_ENV"
fi

end=$((SECONDS + RUN_MAX_SECONDS))

PY_TIMEOUT_CMD=()
if [ "$PY_MAX_SECONDS" -gt 0 ] 2>/dev/null; then
    PY_TIMEOUT_CMD=(timeout "$PY_MAX_SECONDS")
fi

(
    cd "$ROOT_DIR" || exit 1
    timeout "$RUN_MAX_SECONDS" java -jar resttestgen.jar -l WARN
) &
JAVA_PID=$!

(
    cd "$ROOT_DIR" || exit 1
    DEEPREST_PIPES_DIR="$ROOT_DIR" \
    DEEPREST_MAX_SECONDS="$PY_MAX_SECONDS" \
    "${PY_TIMEOUT_CMD[@]}" python deeprest.py
) &
PY_PID=$!

while [ $SECONDS -lt $end ]; do
    if ! kill -0 "$PY_PID" 2>/dev/null && ! kill -0 "$JAVA_PID" 2>/dev/null; then
        break
    fi
    sleep 5
done
