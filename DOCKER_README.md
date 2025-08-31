# Docker Setup for LlamaRestTest

This Docker setup makes it easy to run LlamaRestTest experiments without manually installing all dependencies.

## Quick Start

### 1. Prerequisites
- Docker and Docker Compose installed
- LlamaREST model files (download from the links in README.md)

### 2. Setup
```bash
# Clone the repository
git clone <repository-url>
cd LlamaRestTest

# Create models directory and place your .gguf model files there
mkdir -p models
# Copy your LlamaREST-EX and LlamaREST-IPD .gguf files to models/

# Build the Docker image
docker-compose build
```

### 3. Run Experiments

#### Option A: Using Makefile (Simplest)
```bash
# Setup models directory
make setup-models
# Place your .gguf files in models/

# Run example experiment
make run-example

# Run custom experiments
make run TOOL=llamaresttest SERVICE=fdic
make run TOOL=evomaster SERVICE=spotify

# Other useful commands
make build    # Build Docker image
make up       # Start services
make down     # Stop services
make logs     # View logs
make shell    # Get container shell
make clean    # Clean up everything
```

#### Option B: Using the Python wrapper
```bash
# Run a specific tool on a specific service
python3 docker-run.py llamaresttest fdic

# Available tools: arat-rl, arat-nlp, evomaster, resttestgen, schemathesis, llamaresttest, llamaresttest-ipd, llamaresttest-ex, tcases
# Available services: fdic, genome-nexus, language-tool, ocvn, ohsome, omdb, rest-countries, spotify, youtube

# Force rebuild and run
python3 docker-run.py --build llamaresttest spotify

# Specify custom directories
python3 docker-run.py --models-dir ./my-models --results-dir ./my-results evomaster youtube
```

#### Option C: Using the Bash wrapper
```bash
# Run experiments using the bash script
./docker-run.sh llamaresttest fdic
./docker-run.sh --build evomaster spotify
./docker-run.sh --models-dir ./my-models llamaresttest youtube
```

#### Option D: Using Docker Compose directly
```bash
# Start all services
docker-compose up -d

# Run experiment in the container
docker exec -it llamaresttest bash
# Inside container:
source venv/bin/activate
python3 run.py llamaresttest fdic

# Collect results
python3 collect.py
```

### 4. Authentication Setup

For OMDB and Spotify services, you need to set up authentication tokens:

```bash
# Edit the token files in the running container
docker exec -it llamaresttest bash
# Inside container, edit:
# services/omdb.py - replace TOKEN_HERE with your OMDB token
# services/spotify.py - replace TOKEN_HERE with your Spotify token
```

### 5. Collect Results

Results are automatically collected and stored in the `results/` directory (or your specified results directory).

```bash
# View results
cat results/res.csv
```

## Directory Structure

```
LlamaRestTest/
├── models/           # Place your .gguf model files here
├── results/          # Experiment results will be stored here
├── Dockerfile        # Docker image definition
├── docker-compose.yml # Service orchestration
├── docker-run.py     # Simplified experiment runner
└── DOCKER_README.md  # This file
```

## Troubleshooting

### Common Issues

1. **No models found**: Make sure you've downloaded the LlamaREST models and placed them in the `models/` directory.

2. **Port conflicts**: If you have services running on ports 9001-9009, stop them or modify the port mappings in `docker-compose.yml`.

3. **Memory issues**: The experiments require significant memory. Ensure Docker has access to at least 8GB RAM.

4. **Permission issues**: On Linux, you might need to run Docker commands with `sudo` or add your user to the docker group.

### Viewing Logs

```bash
# View container logs
docker-compose logs llamaresttest

# View specific service logs
docker exec -it llamaresttest tail -f services/default.log
```

### Debugging

```bash
# Get a shell in the container
docker exec -it llamaresttest bash

# Check running processes
docker exec -it llamaresttest ps aux

# Check tmux sessions
docker exec -it llamaresttest tmux list-sessions
```

## Advanced Usage

### Custom Model Paths
If your models are in a different location:
```bash
python3 docker-run.py --models-dir /path/to/your/models llamaresttest fdic
```

### Running Multiple Experiments
```bash
# Run multiple experiments in sequence
for service in fdic spotify youtube; do
    python3 docker-run.py llamaresttest $service
done
```

### Cleanup
```bash
# Stop all services
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove the built image
docker rmi llamaresttest_llamaresttest
```