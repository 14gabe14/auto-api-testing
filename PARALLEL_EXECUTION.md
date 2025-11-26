# LlamaRestTest Parallel Execution Guide

This guide explains how to run LlamaRestTest experiments in parallel on a single GCP VM using Docker containers, similar to DeepREST's architecture.

## Architecture Overview

### Key Changes from Original Design

**Original LlamaRestTest:**
- Multiple VMs (one per experiment)
- All services run directly on host via tmux
- One tool + all 9 services per VM

**New Parallel Design:**
- Single powerful VM (24 vCPUs, 90GB RAM)
- Each service in its own Docker container
- Each tool in its own Docker container
- Dynamic resource allocation based on CPU usage
- Multiple experiments run concurrently on one VM

### Resource Allocation

- **Per experiment run**: 16 CPUs (8 for API, 8 for tool), 32GB RAM (matching DeepREST)
- **24 vCPU VM**: Can run 1 concurrent experiment (need more CPUs for parallel execution)
- **Resource checking**: Waits for 14 free CPUs before launching new experiment

## Prerequisites

1. **GCP Account** with billing enabled
2. **Terraform** installed locally
3. **LLM Models** uploaded to Cloud Storage:
   ```bash
   gsutil cp ex.gguf ipd.gguf gs://my-experiment/LlamaRestTest/
   ```
4. **DeepREST Services** copied to `./services/` (already done)
5. **Infrastructure files** from DeepREST (already copied)

## Important: VM Size Recommendation

**Each experiment requires 16 CPUs + 32GB RAM** (matching DeepREST's allocation):
- API container: 8 CPUs, 16GB RAM
- Tool container: 8 CPUs, 16GB RAM

**Recommended VM sizes**:
- **n1-standard-32** (32 vCPUs, 120GB RAM): 2 concurrent experiments - **DEFAULT**
- **n1-standard-64** (64 vCPUs, 240GB RAM): 4 concurrent experiments
- **n1-standard-96** (96 vCPUs, 360GB RAM): 6 concurrent experiments

**Note**: The default `n1-standard-24` is too small for true parallel execution. Update `machine_type` in `terraform.tfvars` to at least `n1-standard-32`.

## Directory Structure

```
LlamaRestTest/
├── apis/                    # Service Dockerfiles (from DeepREST)
│   ├── blog/
│   ├── features-service/
│   ├── genome-nexus/
│   ├── languagetool/
│   ├── market/
│   ├── ncs/
│   ├── person-controller/
│   ├── project-tracking-system/
│   ├── restcountries/
│   ├── scs/
│   └── user-management/
├── tools/
│   └── llamaresttest/
│       └── Dockerfile       # LlamaRestTest tool container
├── infrastructure/          # Jacoco + mitmproxy (from DeepREST)
├── build.py                 # Build all Docker images
├── run_parallel.py          # Parallel orchestration script
└── terraform/
    ├── main.tf
    ├── variables.tf
    ├── terraform.tfvars
    └── startup-script-parallel.sh
```

## Setup Steps

### 1. Configure Terraform

Edit `terraform/terraform.tfvars`:

```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"
zone       = "us-central1-a"

# Single VM configuration
instance_count = 1
machine_type   = "n1-standard-24"  # 24 vCPUs, 90GB RAM
disk_size      = 100               # GB for Docker images

# Repository
repo_url = "https://github.com/your-username/LlamaRestTest.git"

# Cloud Storage
storage_bucket_name = "my-experiment"
models_path         = "LlamaRestTest"
results_path        = "llamaresttest-results"

# Parallel execution
num_runs_per_combination = 1  # Runs per API/tool combo
auto_start_experiments   = false  # Manual start recommended

# Upload results
upload_results = true
```

### 2. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

This will:
1. Create a single n1-standard-24 VM
2. Install Docker and dependencies
3. Clone your repository
4. Download models from Cloud Storage
5. Build all Docker images (APIs + tool)
6. Set up systemd service for experiments

### 3. Start Experiments

#### Option A: Manual Start (Recommended)

SSH into the VM:
```bash
gcloud compute ssh llamaresttest-instance --zone=us-central1-a
```

Start experiments:
```bash
cd /home/ubuntu/llamaresttest
python3 run_parallel.py
# Enter number of runs when prompted
```

#### Option B: Auto-Start

Set `auto_start_experiments = true` in terraform.tfvars and re-apply:
```bash
terraform apply
```

Experiments will start automatically on VM boot.

### 4. Monitor Progress

Check experiment logs:
```bash
# System logs
sudo journalctl -u llamaresttest-parallel.service -f

# Startup logs
sudo tail -f /var/log/llamaresttest-startup.log

# Check running containers
docker ps

# Check results
ls -la /home/ubuntu/llamaresttest/results/
```

### 5. Collect Results

Results are automatically uploaded to Cloud Storage if `upload_results = true`.

Download results locally:
```bash
gsutil -m cp -r gs://my-experiment/llamaresttest-results/batch-* ./results/
```

## Local Development

### Build Docker Images Locally

```bash
# Build all images
python3 build.py
# Select option 1 (All images)

# Build specific API
python3 build.py
# Select option 4, then choose API

# Build tool only
python3 build.py
# Select option 3
```

### Run Experiments Locally

```bash
# Ensure Docker is running
docker info

# Run parallel experiments
python3 run_parallel.py
# Enter number of runs when prompted
```

### Test Single Experiment

```bash
# Start an API container
docker run -d --name test-api \
  -e API=blog -e TOOL=llamaresttest -e RUN=test-run \
  -p 9090:9090 \
  -v $(pwd)/results:/results \
  llamaresttest-blog

# Start tool container
docker run -d --name test-tool \
  -e API=blog -e TOOL=llamaresttest -e RUN=test-run \
  --network host \
  llamaresttest-llamaresttest

# Check logs
docker logs test-api
docker logs test-tool

# Stop containers
docker stop test-api test-tool
docker rm test-api test-tool
```

## Resource Management

### CPU Allocation

The orchestration script (`run_parallel.py`) checks CPU usage before launching new experiments:

```python
REQUIRED_CPUS = 14  # Need 14 free CPUs
available_cpus = (1 - (psutil.cpu_percent() / 100)) * psutil.cpu_count()
```

- Waits for 14 free CPUs before launching
- Each experiment allocates 16 CPUs (8 API + 8 tool)
- Actual usage may be lower, allowing more concurrent runs with CPU overcommitment

### Memory Allocation

- API container: 16GB limit
- Tool container: 16GB limit
- Total per experiment: 32GB
- 90GB VM can support ~2 experiments (with overhead)

### Concurrent Experiments

On a 24 vCPU VM:
- **Realistic**: 1 concurrent experiment (16 CPUs allocated, 8 CPUs free)
- **With CPU overcommitment**: 1-2 concurrent experiments (Docker allows CPU overcommitment)

**Recommendation**: Use **n1-standard-32** (32 vCPUs, 120GB RAM) or larger for true parallel execution:
- **n1-standard-32**: 2 concurrent experiments
- **n1-standard-64**: 4 concurrent experiments
- **n1-standard-96**: 6 concurrent experiments

## Troubleshooting

### Docker Images Not Building

```bash
# Check Docker status
sudo systemctl status docker

# Rebuild specific image
cd /home/ubuntu/llamaresttest
python3 build.py

# Check Docker logs
sudo journalctl -u docker -n 100
```

### Experiments Not Starting

```bash
# Check systemd service
sudo systemctl status llamaresttest-parallel.service

# View service logs
sudo journalctl -u llamaresttest-parallel.service -n 100

# Check resource availability
python3 -c "import psutil; print(f'CPUs: {psutil.cpu_count()}, RAM: {psutil.virtual_memory().available / (1024**3):.1f}GB')"
```

### Container Failures

```bash
# List all containers
docker ps -a

# Check container logs
docker logs <container-name>

# Remove failed containers
docker rm $(docker ps -a -q -f status=exited)

# Check disk space
df -h
```

### Models Not Found

```bash
# Check models directory
ls -la /home/ubuntu/llamaresttest/models/

# Re-download models
cd /home/ubuntu/llamaresttest
gsutil -m cp -r gs://my-experiment/LlamaRestTest/* ./models/

# Verify model files
find ./models -name "*.gguf"
```

## Cost Optimization

### VM Costs (us-central1)

- **n1-standard-24**: ~$0.95/hour (~$684/month)
- **Preemptible**: ~$0.285/hour (~$205/month, 70% savings)

### Storage Costs

- **Cloud Storage**: $0.020/GB/month
- **Persistent Disk (pd-standard)**: $0.040/GB/month

### Recommendations

1. Use preemptible VMs for non-critical experiments
2. Delete VM when not in use: `terraform destroy`
3. Use `pd-standard` instead of `pd-ssd` (50% cheaper)
4. Compress results before uploading to Cloud Storage

## Comparison with Original Design

| Aspect | Original (Multi-VM) | New (Parallel) |
|--------|-------------------|----------------|
| VMs per experiment | 1 | 1 (shared) |
| Services | tmux on host | Docker containers |
| Tools | tmux on host | Docker containers |
| Isolation | VM-level | Container-level |
| Resource usage | Fixed per VM | Dynamic allocation |
| Scalability | Horizontal (more VMs) | Vertical (bigger VM) |
| Cost | Higher (many VMs) | Lower (one VM) |
| Setup time | Fast (parallel) | Slower (sequential on one VM) |

## Next Steps

1. **Validate Results**: Compare parallel vs. original execution
2. **Optimize Resources**: Tune CPU/RAM allocation per container
3. **Add More Tools**: Extend beyond LlamaRestTest
4. **Implement Preemption Handling**: Auto-restart on preemptible VM termination
5. **Add Result Processing**: Automated analysis and visualization

## References

- DeepREST Architecture: `../deeprest-artifact/run.py`
- Original LlamaRestTest: `../terraform/PARALLELIZATION_ANALYSIS.md`
- Resource Requirements: `../terraform/RESOURCE_REQUIREMENTS.md`

