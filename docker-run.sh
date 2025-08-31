#!/bin/bash

# Simple bash wrapper for LlamaRestTest Docker experiments

set -e

# Default values
MODELS_DIR="./models"
RESULTS_DIR="./results"
BUILD=false

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS] TOOL SERVICE"
    echo ""
    echo "Run LlamaRestTest experiments in Docker"
    echo ""
    echo "TOOL options:"
    echo "  arat-rl, arat-nlp, evomaster, resttestgen, schemathesis,"
    echo "  llamaresttest, llamaresttest-ipd, llamaresttest-ex, tcases"
    echo ""
    echo "SERVICE options:"
    echo "  fdic, genome-nexus, language-tool, ocvn, ohsome,"
    echo "  omdb, rest-countries, spotify, youtube"
    echo ""
    echo "OPTIONS:"
    echo "  --models-dir DIR    Directory containing models (default: ./models)"
    echo "  --results-dir DIR   Directory for results (default: ./results)"
    echo "  --build            Force rebuild of Docker image"
    echo "  --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 llamaresttest fdic"
    echo "  $0 --build evomaster spotify"
    echo "  $0 --models-dir /path/to/models llamaresttest youtube"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --models-dir)
            MODELS_DIR="$2"
            shift 2
            ;;
        --results-dir)
            RESULTS_DIR="$2"
            shift 2
            ;;
        --build)
            BUILD=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        -*)
            echo "Unknown option $1"
            show_help
            exit 1
            ;;
        *)
            if [ -z "$TOOL" ]; then
                TOOL="$1"
            elif [ -z "$SERVICE" ]; then
                SERVICE="$1"
            else
                echo "Too many arguments"
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

# Check required arguments
if [ -z "$TOOL" ] || [ -z "$SERVICE" ]; then
    echo "Error: TOOL and SERVICE are required"
    show_help
    exit 1
fi

# Validate tool
case $TOOL in
    arat-rl|arat-nlp|evomaster|resttestgen|schemathesis|llamaresttest|llamaresttest-ipd|llamaresttest-ex|tcases)
        ;;
    *)
        echo "Error: Invalid tool '$TOOL'"
        show_help
        exit 1
        ;;
esac

# Validate service
case $SERVICE in
    fdic|genome-nexus|language-tool|ocvn|ohsome|omdb|rest-countries|spotify|youtube)
        ;;
    *)
        echo "Error: Invalid service '$SERVICE'"
        show_help
        exit 1
        ;;
esac

# Create directories
mkdir -p "$MODELS_DIR" "$RESULTS_DIR"

# Check for models if using llama tools
if [[ $TOOL == *"llama"* ]]; then
    if [ ! "$(ls -A "$MODELS_DIR"/*.gguf 2>/dev/null)" ]; then
        echo "Warning: No .gguf model files found in $MODELS_DIR"
        echo "Please download LlamaREST models and place them in the models directory"
    fi
fi

# Build if requested
if [ "$BUILD" = true ]; then
    echo "Building Docker image..."
    docker-compose build
fi

# Start services
echo "Starting services..."
docker-compose up -d

# Run experiment
echo "Running $TOOL on $SERVICE..."
docker exec llamaresttest bash -c "source venv/bin/activate && python3 run.py $TOOL $SERVICE"

# Collect results
echo "Collecting results..."
docker exec llamaresttest bash -c "source venv/bin/activate && python3 collect.py"

echo "Experiment completed! Results are in $RESULTS_DIR"