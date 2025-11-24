# Cloud Storage Bucket Structure

## Bucket Name

The bucket name follows this pattern:
```
{project_id}-llamaresttest
```

**Example**: If your project ID is `my-gcp-project`, the bucket will be:
```
my-gcp-project-llamaresttest
```

**To get the actual bucket name after deployment:**
```bash
terraform output bucket_name
```

## Bucket Structure

```
gs://{bucket-name}/
├── models/                          # You upload models here
│   ├── llamarest-ex-{size}.gguf    # LlamaREST-EX model (required)
│   └── llamarest-ipd-{size}.gguf   # LlamaREST-IPD model (required)
│
└── results/                         # Automatically created by experiments
    ├── {tool-name}/
    │   ├── {service-name}/
    │   │   ├── run-{timestamp}/
    │   │   │   ├── log-{service}.txt
    │   │   │   ├── jacoco{port}.exec
    │   │   │   ├── {port}.csv
    │   │   │   └── res.csv
    │   │   └── run-{timestamp}/
    │   │       └── ...
    │   └── {service-name}/
    │       └── ...
    └── ...
```

## Directory Details

### 1. `models/` Directory (You Must Upload)

**Purpose**: Stores LlamaREST model files that are downloaded to each VM on startup.

**Required Files**:
- **LlamaREST-EX model**: One `.gguf` file (choose size: 2B, 4B, 8B, or 16B)
- **LlamaREST-IPD model**: One `.gguf` file (choose size: 2B, 4B, 8B, or 16B)

**File Naming**:
- The script looks for files matching `*ex*.gguf` and `*ipd*.gguf` patterns
- You can name them anything as long as they contain "ex" and "ipd" in the filename
- Examples:
  - `llamarest-ex-8b.gguf` and `llamarest-ipd-8b.gguf`
  - `ex-model.gguf` and `ipd-model.gguf`
  - `LlamaREST-EX-8B-Q6_K.gguf` and `LlamaREST-IPD-8B-Q6_K.gguf`

**File Sizes** (Q6_K quantization, per README):
- 2B model: ~1-2GB
- 4B model: ~2-3GB
- 8B model: ~4-5GB
- 16B model: ~8-10GB

**Total Size**: ~10GB for both models (if using 8B versions)

**How to Upload**:
```bash
# Get bucket name
BUCKET_NAME=$(terraform output -raw bucket_name)

# Upload models
gsutil -m cp /path/to/your/ex-model.gguf gs://$BUCKET_NAME/models/
gsutil -m cp /path/to/your/ipd-model.gguf gs://$BUCKET_NAME/models/
```

### 2. `results/` Directory (Automatically Created)

**Purpose**: Stores experiment results uploaded from each VM after completion.

**Structure**: `results/{tool}/{service}/run-{timestamp}/`

**Example Paths**:
```
results/
├── llamaresttest/
│   ├── fdic/
│   │   ├── run-20241215-143022/
│   │   │   ├── log-fdic.txt
│   │   │   ├── jacoco9001.exec
│   │   │   ├── 9001.csv
│   │   │   └── res.csv
│   │   └── run-20241215-150530/
│   │       └── ...
│   └── spotify/
│       └── run-20241215-143045/
│           └── ...
├── evomaster/
│   ├── fdic/
│   │   └── run-20241215-143100/
│   │       └── ...
│   └── ...
└── ...
```

**Files in Each Run Directory**:
- `log-{service}.txt`: HTTP request/response logs from mitmproxy
- `jacoco{port}.exec`: Code coverage execution data (binary)
- `{port}.csv`: Code coverage report (CSV format)
- `res.csv`: Aggregated results summary

**Automatic Upload**: Results are uploaded automatically if `upload_results = true` in `terraform.tfvars`.

## What You Need to Do

### Step 1: Download Models

Download from the links in the LlamaRestTest README:
- **LlamaREST-EX**: [2B](https://drive.google.com/file/d/1wNbLSnI85jCiwOwYjwUmoH3ZrnVpv-ne/view?usp=sharing) | [4B](https://drive.google.com/file/d/1y478aEulrICa6xrL9ojgAGBRFzMzLSV_/view?usp=sharing) | [8B](https://drive.google.com/file/d/1GtAZD115FEEVnPKC1M2BYhrJpg1dKx_c/view?usp=sharing) | [16B](https://drive.google.com/file/d/18geN_rmLI6EpNo1IhHZhW3lYaLUCRnxK/view?usp=sharing)
- **LlamaREST-IPD**: [2B](https://drive.google.com/file/d/1X3yRZ9urjY2qhqqQLJXk7-fm1CI4145q/view?usp=sharing) | [4B](https://drive.google.com/file/d/1G16vQtvg1dZfVPoxMCq9ifm73NQCnOqJ/view?usp=sharing) | [8B](https://drive.google.com/file/d/1xVm--UmUXuns7LRbm5Bvdhx5ZCMQ_Uaz/view?usp=sharing) | [16B](https://drive.google.com/file/d/18Jraekj5_M-CZ9B9PtEfMPdvcJwhJqVx/view?usp=sharing)

**Recommendation**: Use 8B models for good balance of quality and size (~5GB each).

### Step 2: Deploy Terraform

```bash
terraform apply
```

This creates the bucket (empty except for `models/.gitkeep` placeholder).

### Step 3: Upload Models

```bash
# Get the bucket name
BUCKET_NAME=$(terraform output -raw bucket_name)
echo "Bucket name: $BUCKET_NAME"

# Upload your models (replace paths with your actual file paths)
gsutil -m cp /path/to/LlamaREST-EX-8B.gguf gs://$BUCKET_NAME/models/
gsutil -m cp /path/to/LlamaREST-IPD-8B.gguf gs://$BUCKET_NAME/models/

# Verify upload
gsutil ls gs://$BUCKET_NAME/models/
```

### Step 4: Verify Structure

```bash
# List bucket contents
gsutil ls -r gs://$BUCKET_NAME/

# Should show:
# gs://{bucket}/models/.gitkeep
# gs://{bucket}/models/your-ex-model.gguf
# gs://{bucket}/models/your-ipd-model.gguf
```

## Important Notes

1. **Model Files Are Required**: Without models in the bucket, experiments will fail when trying to use `llamaresttest` tools.

2. **Results Are Optional**: If `upload_results = false`, results stay on VMs and are not uploaded.

3. **Bucket Naming**: The bucket name includes a random suffix, so you must use `terraform output bucket_name` to get the exact name.

4. **Permissions**: The service account has `storage.admin` role, so VMs can read models and write results automatically.

5. **Cost**: 
   - Storage: ~$0.02/GB/month for models
   - Results: Minimal (typically <1GB total)
   - Network egress: Free within same region

## Example Workflow

```bash
# 1. Deploy infrastructure
terraform apply

# 2. Get bucket name
export BUCKET_NAME=$(terraform output -raw bucket_name)

# 3. Upload models (one-time setup)
gsutil -m cp ~/Downloads/LlamaREST-EX-8B-Q6_K.gguf gs://$BUCKET_NAME/models/
gsutil -m cp ~/Downloads/LlamaREST-IPD-8B-Q6_K.gguf gs://$BUCKET_NAME/models/

# 4. Run experiments (VMs will download models automatically)

# 5. Collect results
./collect-results.sh $BUCKET_NAME
```

