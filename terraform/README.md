# Terraform Configuration for LlamaRestTest on GCP

This Terraform configuration creates GCP Compute Engine instances to run LlamaRestTest experiments in parallel, ensuring scientific accuracy through complete isolation between runs.

## Prerequisites

1. **GCP Account**: You need a GCP project with billing enabled
2. **Terraform**: Install Terraform >= 1.0
3. **GCP CLI**: Install and configure `gcloud` CLI
4. **SSH Keys**: Generate SSH key pair if you don't have one

## Setup

### 1. Authenticate with GCP

```bash
gcloud auth login
gcloud auth application-default login
```

### 2. Set up Terraform variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set your project ID:
```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"
zone       = "us-central1-a"
```

### 3. Initialize Terraform

```bash
terraform init
```

### 4. Review the plan

```bash
terraform plan
```

### 5. Apply the configuration

```bash
terraform apply
```

This will create:
- One or more GCP Compute Engine instances (n1-standard-8 by default)
- Cloud Storage bucket for models and results
- Service account with necessary permissions
- Firewall rules for SSH and LlamaRestTest ports
- Startup script that installs dependencies, runs experiments, and uploads results

## Parallelization Support

This configuration supports running multiple experiments in parallel, with each experiment running on its own isolated VM instance. This ensures:
- **Scientific Accuracy**: Complete isolation between experiments
- **No Port Conflicts**: Each instance has its own network namespace
- **Reproducibility**: Identical environments across all instances
- **Scalability**: Run as many experiments in parallel as your quota/budget allows

## After Deployment

### Automatic Execution

If you configured `repo_url`, `tool_name`, and `service_name` in `terraform.tfvars`, experiments will run automatically on startup. You can monitor progress via:

```bash
# SSH into an instance
gcloud compute ssh llamaresttest-instance-1 --zone=us-central1-a

# Check experiment status
sudo journalctl -u llamaresttest-experiment.service -f

# Or check the startup log
sudo tail -f /var/log/llamaresttest-startup.log
```

### Manual Execution (if automatic setup not configured)

1. **SSH into the instance**
```bash
# Get instance IP from terraform output
terraform output instance_ips

# SSH into first instance
gcloud compute ssh llamaresttest-instance-1 --zone=us-central1-a
```

2. **Upload LlamaRestTest code** (if not using Git)

**Option A: Clone from Git** (recommended)
```bash
cd /home/ubuntu
git clone <your-repo-url> llamaresttest
cd llamaresttest
```

**Option B: Upload via SCP**
```bash
# From your local machine
gcloud compute scp --recurse /path/to/LlamaRestTest llamaresttest-instance-1:~/llamaresttest --zone=us-central1-a
```

3. **Upload model files to Cloud Storage** (recommended)
```bash
# From your local machine
BUCKET_NAME=$(terraform output -raw bucket_name)
gsutil -m cp -r /path/to/models/* gs://$BUCKET_NAME/models/
```

4. **Run experiments manually**
```bash
cd ~/llamaresttest
./run-experiment.sh
```

### Collecting Results

Results are automatically uploaded to Cloud Storage. To download all results:

```bash
BUCKET_NAME=$(terraform output -raw bucket_name)
./collect-results.sh $BUCKET_NAME
```

Or manually:
```bash
gsutil -m cp -r gs://$BUCKET_NAME/results/* ./collected-results/
```

## Configuration Options

### Parallel Execution

To run multiple experiments in parallel, configure `experiment_configs` in `terraform.tfvars`:

```hcl
instance_count = 5

experiment_configs = [
  {
    tool    = "llamaresttest"
    service = "fdic"
  },
  {
    tool    = "llamaresttest"
    service = "spotify"
  },
  {
    tool    = "evomaster"
    service = "fdic"
  },
  {
    tool    = "evomaster"
    service = "spotify"
  },
  {
    tool    = "resttestgen"
    service = "fdic"
  },
]
```

Or use the helper script to generate all combinations:
```bash
export GCP_PROJECT_ID="your-project"
export REPO_URL="https://github.com/your-org/LlamaRestTest.git"
./launch-parallel.sh
terraform apply
```

### Machine Type

Edit `variables.tf` or `terraform.tfvars` to change the machine type:
```hcl
machine_type = "n1-standard-16"  # 16 vCPUs, 60GB RAM
```

Recommended machine types:
- `n1-standard-8` (8 vCPUs, 30GB RAM) - **Minimum recommended** (based on DeepREST's per-container allocation of 16GB RAM + 8 CPUs, but LlamaRestTest runs services on host with less overhead)
- `n1-standard-16` (16 vCPUs, 60GB RAM) - **Recommended** for reliable execution (original experiments used 64GB RAM MacBook, but that ran all services simultaneously)
- `n1-highmem-8` (8 vCPUs, 52GB RAM) - Good alternative if you need more memory but fewer CPUs
- `n1-standard-4` (4 vCPUs, 15GB RAM) - **Not recommended** (likely insufficient for Java services + tools)

**Note**: The original LlamaRestTest experiments were run on an M1 MacBook Pro with 64GB RAM, but that machine ran ALL services simultaneously (`run_service.py all`). Since our parallelization approach runs one tool/service combination per instance, `n1-standard-8` should be sufficient, but `n1-standard-16` provides more headroom and is recommended for production runs.

### Disk Size

Adjust disk size in `terraform.tfvars`:
```hcl
disk_size = 40  # 40GB (default, increase if needed)
```

### Region/Zone

Change region/zone in `terraform.tfvars`:
```hcl
region = "us-east1"
zone   = "us-east1-b"
```

## Cost Estimation

### Per Instance (1 hour runtime)
- `n1-standard-8`: ~$0.04-0.05/hour (~$2-3 for 1 hour experiment)
- `n1-standard-16`: ~$0.08-0.10/hour (~$4-5 for 1 hour experiment)
- Disk (40GB SSD): ~$0.007/hour (one-time cost if kept)
- Network: Minimal (mostly internal)

### Example: 54 Parallel Experiments
- 54 instances × n1-standard-8 × 1 hour = ~$2-3 total
- Storage: ~$10/month (if instances are kept)
- **Total for 1 hour of parallel execution**: ~$2-3

**Cost Optimization Tips**:
1. Use preemptible instances (80% cost reduction): Add `preemptible = true` to instance config
2. Delete instances after experiments complete
3. Use smaller machine types if experiments don't require full resources
4. Stop instances when not in use:
```bash
# Stop all instances
for instance in $(terraform output -json instance_names | jq -r '.[]'); do
    gcloud compute instances stop $instance --zone=us-central1-a
done
```

## Cleanup

To destroy all resources:
```bash
terraform destroy
```

## Troubleshooting

### SSH Connection Issues

1. Check firewall rules:
```bash
gcloud compute firewall-rules list
```

2. Verify SSH key is correct:
```bash
gcloud compute instances describe llamaresttest-instance --zone=us-central1-a
```

### Docker Not Starting

Check startup script logs:
```bash
sudo cat /var/log/llamaresttest-startup.log
```

### Port Conflicts

If you need to change ports, modify:
- `docker-compose.yml` in the LlamaRestTest directory
- Firewall rules in `main.tf`

## Next Steps

1. **Upload Models to Cloud Storage**:
   ```bash
   BUCKET_NAME=$(terraform output -raw bucket_name)
   gsutil -m cp -r /path/to/your/models/*.gguf gs://$BUCKET_NAME/models/
   ```

2. **Configure Authentication Tokens** (if needed):
   - Set `omdb_token` and `spotify_token` in `terraform.tfvars`
   - Or use Secret Manager for better security

3. **Test Single Instance First**:
   - Start with `instance_count = 1` to verify setup
   - Check logs and results before scaling up

4. **Scale to Parallel Execution**:
   - Use `launch-parallel.sh` to generate configurations
   - Gradually increase `instance_count`
   - Monitor costs and quotas

5. **Collect Results**:
   ```bash
   BUCKET_NAME=$(terraform output -raw bucket_name)
   ./collect-results.sh $BUCKET_NAME
   ```

## Scientific Accuracy

This setup ensures scientific accuracy through:
- **Isolation**: Each experiment runs on a separate VM
- **Reproducibility**: Identical environments (same image, same setup)
- **Consistency**: Same models, same duration (1 hour), same resources
- **No Interference**: No port conflicts, no resource contention

See `PARALLELIZATION_ANALYSIS.md` and `ISSUES_AND_FIXES.md` for detailed analysis.

