# Resource Requirements Analysis

## Evidence-Based Requirements

### Original LlamaRestTest Setup
- **Machine**: M1 MacBook Pro with 64GB RAM
- **Usage**: Ran ALL services simultaneously via `run_service.py all`
- **Execution**: Sequential (one tool/service combination at a time)
- **Note**: The 64GB was for running all 9 services at once, not for a single experiment

### DeepREST Comparison
- **Per Experiment**: 
  - API container: 16GB RAM, 8 CPUs
  - Tool container: 16GB RAM, 8 CPUs
  - **Total per experiment**: 32GB RAM, 16 CPUs
- **Parallel Execution Check**: Requires 32GB RAM + 14 CPUs available before starting new run
- **Recommended System**: 16 cores, 24GB RAM (for running multiple parallel experiments)

### Our Parallelization Approach
- **One VM per experiment**: Each instance runs ONE tool/service combination
- **Services**: Only the specific service needed (not all services)
- **Isolation**: Complete isolation between experiments

## Recommended Machine Types

### Minimum: `n1-standard-8` (8 vCPUs, 30GB RAM)
**Rationale**:
- Based on DeepREST's per-container allocation (16GB + 8 CPUs)
- LlamaRestTest runs services on host (less overhead than containers)
- Only one service runs per instance (not all 9 services)
- **Risk**: May be tight for memory-intensive services or tools

### Recommended: `n1-standard-16` (16 vCPUs, 60GB RAM)
**Rationale**:
- Provides comfortable headroom (2x minimum)
- Matches DeepREST's total allocation per experiment (32GB RAM, 16 CPUs)
- Handles memory spikes from Java services, model loading, etc.
- **Best for**: Production runs, reliability

### Alternative: `n1-highmem-8` (8 vCPUs, 52GB RAM)
**Rationale**:
- Good if memory is the constraint, not CPU
- Sufficient for most tools that aren't CPU-intensive
- **Best for**: Memory-heavy workloads

### Not Recommended: `n1-standard-4` (4 vCPUs, 15GB RAM)
**Rationale**:
- Likely insufficient for Java services (genome-nexus, language-tool, youtube)
- May struggle with model loading (LlamaREST models)
- **Risk**: Out of memory errors, slow execution

## Actual Resource Usage (Estimated)

Per experiment instance:
- **Base OS + Docker**: ~2-4GB RAM
- **Java Service** (if applicable): ~4-8GB RAM
  - genome-nexus: ~4-6GB
  - language-tool: ~6-8GB
  - youtube: ~2-4GB
- **Tool Execution**: ~2-4GB RAM
  - llamaresttest: ~2-4GB (model loading)
  - evomaster: ~2-3GB
  - resttestgen: ~1-2GB
  - schemathesis: ~1GB
- **Python Services/Proxies**: ~500MB-1GB
- **Buffer**: ~4-8GB for spikes

**Total Estimated**: 15-25GB RAM per instance

## Recommendation

**Start with `n1-standard-8`** for testing, but **use `n1-standard-16`** for production runs to ensure reliability and handle resource spikes.

## Cost Comparison

For 1 hour of execution:
- `n1-standard-8`: ~$0.04-0.05/hour
- `n1-standard-16`: ~$0.08-0.10/hour
- **Difference**: ~$0.04-0.05 per instance per hour

For 54 parallel experiments:
- `n1-standard-8`: ~$2.16-2.70
- `n1-standard-16`: ~$4.32-5.40
- **Difference**: ~$2.16-2.70 total

The extra cost for `n1-standard-16` is minimal compared to the reliability benefit.

