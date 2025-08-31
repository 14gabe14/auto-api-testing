# LlamaRestTest Docker Makefile

.PHONY: help build up down clean run-example logs shell

# Default target
help:
	@echo "LlamaRestTest Docker Commands:"
	@echo ""
	@echo "  make build          - Build the Docker image"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make clean          - Stop services and remove containers/volumes"
	@echo "  make run-example    - Run example experiment (llamaresttest on fdic)"
	@echo "  make logs           - Show container logs"
	@echo "  make shell          - Get shell access to container"
	@echo ""
	@echo "Custom runs:"
	@echo "  make run TOOL=evomaster SERVICE=spotify"
	@echo "  make run TOOL=llamaresttest SERVICE=youtube"
	@echo ""
	@echo "Available tools: arat-rl, arat-nlp, evomaster, resttestgen,"
	@echo "                 schemathesis, llamaresttest, llamaresttest-ipd,"
	@echo "                 llamaresttest-ex, tcases"
	@echo ""
	@echo "Available services: fdic, genome-nexus, language-tool, ocvn,"
	@echo "                    ohsome, omdb, rest-countries, spotify, youtube"

# Build the Docker image
build:
	docker-compose build

# Start services
up:
	docker-compose up -d
	@echo "Services started. Use 'make logs' to view logs."

# Stop services
down:
	docker-compose down

# Clean up everything
clean:
	docker-compose down -v
	docker system prune -f

# Run example experiment
run-example: up
	@echo "Running example: llamaresttest on fdic service..."
	docker exec llamaresttest bash -c "source venv/bin/activate && python3 run.py llamaresttest fdic"
	docker exec llamaresttest bash -c "source venv/bin/activate && python3 collect.py"
	@echo "Example completed! Check results/ directory."

# Run custom experiment
run: up
	@if [ -z "$(TOOL)" ] || [ -z "$(SERVICE)" ]; then \
		echo "Usage: make run TOOL=<tool> SERVICE=<service>"; \
		echo "Example: make run TOOL=llamaresttest SERVICE=fdic"; \
		exit 1; \
	fi
	@echo "Running $(TOOL) on $(SERVICE)..."
	docker exec llamaresttest bash -c "source venv/bin/activate && python3 run.py $(TOOL) $(SERVICE)"
	docker exec llamaresttest bash -c "source venv/bin/activate && python3 collect.py"
	@echo "Experiment completed! Check results/ directory."

# Show logs
logs:
	docker-compose logs -f llamaresttest

# Get shell access
shell: up
	docker exec -it llamaresttest bash

# Setup models directory
setup-models:
	@mkdir -p models
	@echo "Models directory created at ./models"
	@echo "Please download LlamaREST model files and place them in this directory."
	@echo "Download links are available in README.md"