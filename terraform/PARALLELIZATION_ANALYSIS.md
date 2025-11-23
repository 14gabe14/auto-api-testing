# Parallelization Analysis: DeepREST vs LlamaRestTest

## Key Differences in Environment Setup

### DeepREST Architecture
- **Isolation**: Each experiment run uses separate Docker containers (API container + Tool container)
- **Port Management**: Dynamic port allocation (random ports 10000-60000) per run
- **Parallelization**: Threading-based with resource checking (32GB RAM, 14 CPUs per run)
- **Resource Allocation**: 
  - API container: 16GB RAM, 8 CPUs
  - Tool container: 16GB RAM, 8 CPUs
- **Execution Model**: Each run is completely isolated in its own containers
- **Results**: Stored in `./results/{api}/{tool}/{run}/` with SQLite DB and coverage files
- **Duration**: 1 hour (60 minutes) per run
- **Network**: Tool containers use `network_mode='host'` to access API containers

### LlamaRestTest Architecture
- **Isolation**: Services run in tmux sessions on the host system
- **Port Management**: Fixed ports (9001-9009) for services
- **Parallelization**: Sequential execution (one tool/service at a time)
- **Resource Allocation**: All services run on the same host
- **Execution Model**: 
  - All services started at once via `run_service.py all`
  - Waits 300 seconds (5 minutes) for services to start
  - Runs tool for 1 hour (3600 seconds)
  - Uses Jacoco for code coverage
- **Results**: Stored in `results/` directory with log files and coverage data
- **Duration**: 1 hour per experiment
- **Network**: Services run on localhost with proxy ports

## Critical Issues for Parallelization

### 1. Port Conflicts
- **Problem**: LlamaRestTest uses fixed ports (9001-9009), so multiple instances would conflict
- **Solution**: Each VM instance needs to run only ONE tool/service combination, OR use port remapping

### 2. Service Dependencies
- **Problem**: Some services require MongoDB (genome-nexus), Java environments, etc.
- **Solution**: Each instance must have all dependencies installed

### 3. Model Files
- **Problem**: LlamaREST models need to be available on each instance
- **Solution**: Use Cloud Storage bucket to store models, download on startup

### 4. Result Collection
- **Problem**: Results are stored locally on each instance
- **Solution**: Upload results to Cloud Storage after experiment completion

### 5. Authentication Tokens
- **Problem**: OMDB and Spotify require tokens that need to be configured
- **Solution**: Store tokens in Secret Manager or environment variables

## Parallelization Strategy for GCP

### Approach: One VM per Experiment Run
This ensures:
- **Isolation**: Each experiment runs in complete isolation
- **No Port Conflicts**: Each VM has its own network namespace
- **Scientific Accuracy**: Identical conditions for each run
- **Scalability**: Can run N experiments in parallel (limited by quota/budget)

### Resource Requirements per Instance
Based on DeepREST's requirements and LlamaRestTest's needs:
- **Machine Type**: `n1-standard-8` (8 vCPUs, 30GB RAM) minimum
- **Disk**: 100GB SSD (for models, code, results)
- **Network**: Standard tier sufficient

### Execution Flow
1. **Instance Creation**: Terraform creates N instances (one per experiment)
2. **Startup Script**: 
   - Installs dependencies (Docker, Java, Python, etc.)
   - Downloads LlamaRestTest code from Git
   - Downloads models from Cloud Storage
   - Configures authentication tokens
   - Runs the specific experiment (tool + service)
3. **Experiment Execution**:
   - Starts services for the specific service
   - Runs the tool for 1 hour
   - Collects results
4. **Result Upload**: Uploads results to Cloud Storage
5. **Instance Cleanup**: Optionally shuts down after completion

## Scientific Accuracy Considerations

### Ensuring Reproducibility
1. **Identical Environments**: All instances use the same base image and setup
2. **Isolation**: No interference between parallel runs
3. **Consistent Timing**: All runs execute for exactly 1 hour
4. **Resource Allocation**: Same resources per instance
5. **Model Versions**: Same model files used across all instances

### Potential Issues
1. **Network Variability**: Different instances may have different network conditions
   - **Mitigation**: Use same region/zone, same network tier
2. **Timing Variations**: Startup times may vary
   - **Mitigation**: Ensure services are fully started before tool execution
3. **Resource Contention**: If multiple instances on same physical host
   - **Mitigation**: Use preemptible instances or ensure adequate resources

## Implementation Plan

### Phase 1: Single Instance Setup
- Fix current terraform to properly set up one instance
- Test experiment execution end-to-end

### Phase 2: Parallelization
- Create terraform module for multiple instances
- Implement Cloud Storage integration
- Add result collection script

### Phase 3: Automation
- Create script to launch N experiments
- Implement monitoring/status checking
- Add cleanup automation

