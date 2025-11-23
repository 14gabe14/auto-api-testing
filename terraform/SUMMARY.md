# Summary: LlamaRestTest GCP Parallelization

## Overview

This Terraform configuration enables parallel execution of LlamaRestTest experiments on GCP with scientific accuracy. Each experiment runs on an isolated VM instance, ensuring reproducibility and eliminating interference between runs.

## Key Differences: DeepREST vs LlamaRestTest

### DeepREST
- Uses Docker containers for isolation
- Dynamic port allocation (10000-60000)
- Threading-based parallelization with resource checking
- Each run: 16GB RAM + 8 CPUs per container

### LlamaRestTest
- Uses tmux sessions on host
- Fixed ports (9001-9009)
- Sequential execution (one at a time)
- All services run on same host

## Solution: One VM per Experiment

**Why this approach?**
- ✅ Complete isolation (no port conflicts, no resource contention)
- ✅ Scientific accuracy (identical conditions per run)
- ✅ Scalability (run N experiments in parallel)
- ✅ Reproducibility (same environment, same models)

## What Was Fixed

1. **Added Parallelization Support**
   - `instance_count` variable to create multiple instances
   - `experiment_configs` to specify tool/service pairs
   - Each instance runs one experiment automatically

2. **Cloud Storage Integration**
   - Bucket for models (centralized distribution)
   - Bucket for results (automatic collection)
   - Proper IAM permissions

3. **Complete Startup Script**
   - Installs all dependencies (Java, Python, Docker, etc.)
   - Clones repository from Git
   - Downloads models from Cloud Storage
   - Configures authentication tokens
   - Runs experiment automatically
   - Uploads results to Cloud Storage

4. **Fixed IAM Permissions**
   - Changed from overly broad `compute.admin` to specific roles
   - `storage.admin` for Cloud Storage access
   - `compute.instanceAdmin.v1` for instance management

5. **Result Collection**
   - Automatic upload to Cloud Storage
   - Helper script to download all results
   - Organized by tool/service/run-id

## Files Created/Modified

### Modified
- `main.tf` - Added parallelization, Cloud Storage, proper IAM
- `variables.tf` - Added experiment configuration variables
- `startup-script.sh` - Complete automation of experiment execution
- `terraform.tfvars.example` - Updated with new options
- `README.md` - Comprehensive documentation

### Created
- `PARALLELIZATION_ANALYSIS.md` - Detailed analysis of differences
- `ISSUES_AND_FIXES.md` - Issues found and how they were fixed
- `launch-parallel.sh` - Helper script to generate experiment configs
- `collect-results.sh` - Helper script to download results
- `SUMMARY.md` - This file

## Quick Start

1. **Configure variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your project ID, repo URL, tokens
   ```

2. **Upload models** (after first apply):
   ```bash
   BUCKET_NAME=$(terraform output -raw bucket_name)
   gsutil -m cp -r /path/to/models/*.gguf gs://$BUCKET_NAME/models/
   ```

3. **Deploy**:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

4. **Collect results**:
   ```bash
   BUCKET_NAME=$(terraform output -raw bucket_name)
   ./collect-results.sh $BUCKET_NAME
   ```

## Example: Running 54 Experiments in Parallel

```bash
# Generate configurations for all tool/service combinations
export GCP_PROJECT_ID="your-project"
export REPO_URL="https://github.com/your-org/LlamaRestTest.git"
./launch-parallel.sh

# Review and apply
terraform plan
terraform apply

# Wait for experiments to complete (~1 hour)
# Then collect results
BUCKET_NAME=$(terraform output -raw bucket_name)
./collect-results.sh $BUCKET_NAME
```

## Cost Estimate

For 54 parallel experiments (9 services × 6 tools):
- **Runtime**: ~$2-3 for 1 hour of execution
- **Storage**: ~$10/month (if instances kept)
- **Total**: ~$2-3 per experiment batch

Use preemptible instances to reduce costs by 80%.

## Scientific Accuracy Guarantees

1. **Isolation**: Each experiment on separate VM
2. **Reproducibility**: Same base image, same setup script
3. **Consistency**: Same models from Cloud Storage
4. **Timing**: All runs execute for exactly 1 hour
5. **Resources**: Same machine type per instance

## Next Steps

1. Test with single instance first
2. Verify models are accessible from Cloud Storage
3. Test authentication token configuration
4. Gradually scale to parallel execution
5. Monitor costs and adjust machine types as needed

## Troubleshooting

See `README.md` for detailed troubleshooting. Common issues:
- Models not found: Upload to Cloud Storage bucket
- Authentication failures: Check token configuration
- Experiments not starting: Check startup logs
- Results not uploading: Check IAM permissions

