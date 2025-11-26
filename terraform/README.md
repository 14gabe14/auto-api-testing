# Terraform Configuration for LlamaRestTest Parallel Execution on GCP

This Terraform configuration creates a single GCP Compute Engine instance to run LlamaRestTest experiments in parallel using Docker containers, similar to DeepREST's architecture.

## Architecture

- **Single VM**: One powerful VM (n1-standard-24 or larger) runs all experiments
- **Docker Containers**: Each service and tool runs in isolated Docker containers
- **Dynamic Resource Allocation**: Experiments run concurrently with resource checking
- **DeepREST Services**: Uses pre-built DeepREST service Docker images
- **LlamaRestTest Tool**: Custom Docker container with LLM models

## Prerequisites

1. **GCP Account**: You need a GCP project with billing enabled
2. **Terraform**: Install Terraform >= 1.0
3. **GCP CLI**: Install and configure `gcloud` CLI
4. **LLM Models**: Upload LlamaREST models to Cloud Storage (see below)

## Setup

### 1. Authenticate with GCP

```bash
gcloud auth login
gcloud auth application-default login
```

### 2. Upload Models to Cloud Storage

Before deploying, upload your LlamaREST models:

```bash
# Set your bucket name
BUCKET_NAME="my-experiment"  # Your existing bucket
MODELS_PATH="LlamaRestTest"  # Path within bucket

# Upload models
gsutil cp ex.gguf ipd.gguf gs://$BUCKET_NAME/$MODELS_PATH/
```

### 3. Set up Terraform variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"
zone       = "us-central1-a"

# Single VM for parallel execution
instance_count = 1
machine_type   = "n1-standard-24"  # 24 vCPUs, 90GB RAM
disk_size      = 100               # GB for Docker images

# Repository
repo_url = "https://github.com/your-username/LlamaRestTest.git"

# Cloud Storage (existing bucket)
storage_bucket_name = "my-experiment"
models_path         = "LlamaRestTest"
results_path        = "llamaresttest-results"

# Parallel execution
num_runs_per_combination = 1  # Runs per API/tool combo
auto_start_experiments   = false  # Manual start recommended

# Upload results
upload_results = true
```

### 4. Initialize Terraform

```bash
terraform init
```

### 5. Review the plan

```bash
terraform plan
```

### 6. Apply the configuration

```bash
terraform apply
```

This will create:
- One GCP Compute Engine instance (n1-standard-24 by default)
- Service account with necessary permissions
- Firewall rules for SSH
- Startup script that installs Docker, builds images, and sets up experiments

## After Deployment

### Automatic Execution (Optional)

If `auto_start_experiments = true`, experiments start automatically on VM boot.

### Manual Execution (Recommended)

1. **SSH into the instance**:
```bash
gcloud compute ssh llamaresttest-instance --zone=us-central1-a
```

2. **Start experiments**:
```bash
cd /home/ubuntu/llamaresttest
python3 run_parallel.py
# Enter number of runs when prompted (e.g., 1-20)
```

3. **Monitor progress**:
```bash
# Check Docker containers
docker ps

# Check systemd service logs
sudo journalctl -u llamaresttest-parallel.service -f

# Check startup logs
sudo tail -f /var/log/llamaresttest-startup.log

# Check results
ls -la /home/ubuntu/llamaresttest/results/
```

### Collecting Results

Results are automatically uploaded to Cloud Storage if `upload_results = true`. Download locally:

```bash
# From terraform directory
./collect-results.sh
```

Or manually:
```bash
BUCKET_NAME=$(terraform output -raw storage_bucket_name)
RESULTS_PATH=$(terraform output -raw results_path)
gsutil -m cp -r gs://$BUCKET_NAME/$RESULTS_PATH/* ./collected-results/
```

## Configuration Options

### Machine Type

Each experiment requires **16 CPUs + 32GB RAM** (matching DeepREST):
- API container: 8 CPUs, 16GB RAM
- Tool container: 8 CPUs, 16GB RAM

**Recommended VM sizes**:
- **n1-standard-24** (24 vCPUs, 90GB RAM): 1 concurrent experiment (default)
- **n1-standard-32** (32 vCPUs, 120GB RAM): 2 concurrent experiments
- **n1-standard-64** (64 vCPUs, 240GB RAM): 4 concurrent experiments
- **n1-standard-96** (96 vCPUs, 360GB RAM): 6 concurrent experiments

Edit `terraform.tfvars`:
```hcl
machine_type = "n1-standard-32"  # For 2 concurrent experiments
```

### Number of Runs

Set how many times to run each API/tool combination:

```hcl
num_runs_per_combination = 10  # 10 runs per combination
```

### Auto-Start

Automatically start experiments on VM boot:

```hcl
auto_start_experiments = true
```

**Note**: Manual start is recommended for first-time setup to monitor the build process.

### Disk Size

Adjust for Docker images and models:

```hcl
disk_size = 100  # GB (default, increase if needed)
```

## Resource Allocation

### Per Experiment Run
- **API Container**: 8 CPUs, 16GB RAM
- **Tool Container**: 8 CPUs, 16GB RAM
- **Total**: 16 CPUs, 32GB RAM per run

### Resource Checking
The orchestration script waits for **14 free CPUs** before launching a new experiment, ensuring sufficient resources.

### Concurrent Execution

On a 24 vCPU VM:
- **Realistic**: 1 concurrent experiment (16 CPUs allocated, 8 CPUs free)
- **With CPU overcommitment**: 1-2 concurrent (Docker allows CPU overcommitment)

For true parallel execution, use larger VMs:
- **n1-standard-32**: 2 concurrent experiments
- **n1-standard-64**: 4 concurrent experiments

## Cost Estimation

### Per Hour (us-central1)
- **n1-standard-24**: ~$0.95/hour (~$684/month)
- **n1-standard-32**: ~$1.52/hour (~$1,095/month)
- **n1-standard-64**: ~$3.04/hour (~$2,189/month)
- **Preemptible** (70% savings):
  - n1-standard-24: ~$0.285/hour (~$205/month)
  - n1-standard-32: ~$0.456/hour (~$328/month)

### Example: 11 Experiments (11 APIs × 1 tool × 1 run)
- **Sequential on n1-standard-24**: ~11 hours × $0.95 = **~$10.45**
- **Parallel on n1-standard-64** (4 concurrent): ~3 hours × $3.04 = **~$9.12**

**Cost Optimization Tips**:
1. Use preemptible instances (70% cost reduction)
2. Delete VM after experiments complete
3. Use appropriate machine size for your concurrency needs
4. Stop VM when not in use: `gcloud compute instances stop llamaresttest-instance --zone=us-central1-a`

## Available Services

The system uses DeepREST's pre-built service Docker images:
- blog
- features-service
- genome-nexus
- languagetool
- market
- ncs
- person-controller
- project-tracking-system
- restcountries
- scs
- user-management

## Available Tools

- llamaresttest (with LlamaREST-EX and LlamaREST-IPD models)

## Troubleshooting

### Docker Images Not Building

```bash
# SSH into instance
gcloud compute ssh llamaresttest-instance --zone=us-central1-a

# Check Docker status
sudo systemctl status docker

# Rebuild images manually
cd /home/ubuntu/llamaresttest
python3 build.py
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
```

### Models Not Found

```bash
# Check models directory
ls -la /home/ubuntu/llamaresttest/models/

# Re-download models
cd /home/ubuntu/llamaresttest
gsutil -m cp -r gs://my-experiment/LlamaRestTest/* ./models/
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

## Next Steps

1. **Test Locally First** (optional):
   ```bash
   # Build Docker images locally
   python3 build.py

   # Test single experiment
   python3 run_parallel.py
```

2. **Deploy to GCP**:
```bash
   cd terraform
   terraform apply
```

3. **Monitor First Run**:
```bash
   gcloud compute ssh llamaresttest-instance --zone=us-central1-a
   sudo tail -f /var/log/llamaresttest-startup.log
```

4. **Scale Up**:
   - Increase `num_runs_per_combination` for more repetitions
   - Use larger machine type for more concurrent experiments

## Scientific Accuracy

This setup ensures scientific accuracy through:
- **Isolation**: Each experiment runs in separate Docker containers
- **Reproducibility**: Identical environments (same Docker images)
- **Consistency**: Same models, same duration (1 hour), same resources
- **Resource Management**: Dynamic allocation prevents interference

## Documentation

- **Parallel Execution Guide**: See `../PARALLEL_EXECUTION.md` for detailed usage
- **Bucket Structure**: See `BUCKET_STRUCTURE.md` for Cloud Storage details
- **Resource Requirements**: See `RESOURCE_REQUIREMENTS.md` for sizing guidance
