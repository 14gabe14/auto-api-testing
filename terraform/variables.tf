variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "instance_name" {
  description = "Name of the compute instance"
  type        = string
  default     = "llamaresttest-instance"
}

variable "machine_type" {
  description = "Machine type for the instance"
  type        = string
  default     = "n1-standard-24" # 32 vCPUs, 120GB RAM - for parallel execution (each run needs 16 CPUs + 32GB RAM)
  # Alternatives: n1-standard-64 (64 vCPUs, 240GB) for 4 concurrent experiments
  #               n1-standard-96 (96 vCPUs, 360GB) for 6 concurrent experiments
}

variable "disk_size" {
  description = "Boot disk size in GB"
  type        = number
  default     = 100 
}

variable "ssh_user" {
  description = "SSH username"
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key file (leave empty to use GCP's default SSH key management)"
  type        = string
  default     = ""
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key file"
  type        = string
  default     = "~/.ssh/id_rsa"
}

variable "instance_count" {
  description = "Number of instances to create (set to 1 for single-VM parallel execution)"
  type        = number
  default     = 1
}

variable "repo_url" {
  description = "Git repository URL for LlamaRestTest"
  type        = string
  default     = ""
}

variable "experiment_configs" {
  description = "List of experiment configurations (tool, service pairs) for parallel execution"
  type = list(object({
    tool    = string
    service = string
  }))
  default = []
}

variable "default_tool" {
  description = "Default tool name if experiment_configs not provided"
  type        = string
  default     = "llamaresttest"
}

variable "default_service" {
  description = "Default service name if experiment_configs not provided"
  type        = string
  default     = "fdic"
}

variable "omdb_token" {
  description = "OMDB API token (optional, can be set via Secret Manager)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "spotify_token" {
  description = "Spotify API token (optional, can be set via Secret Manager)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "storage_bucket_name" {
  description = "Name of existing Cloud Storage bucket (e.g., 'my-experiment')"
  type        = string
  default     = "my-experiment"
}

variable "models_path" {
  description = "Path within bucket where models are stored (e.g., 'LlamaRestTest')"
  type        = string
  default     = "LlamaRestTest"
}

variable "results_path" {
  description = "Path within bucket where results will be stored"
  type        = string
  default     = "llamaresttest-results"
}

variable "upload_results" {
  description = "Whether to upload results to Cloud Storage after experiment"
  type        = bool
  default     = true
}

variable "disk_type" {
  description = "Boot disk type. pd-standard is cheaper, pd-ssd is faster"
  type        = string
  default     = "pd-ssd" # Cheaper option, pd-ssd costs ~2x more
}

variable "num_runs_per_combination" {
  description = "Number of experiment runs per API/tool combination"
  type        = number
  default     = 1
}

variable "auto_start_experiments" {
  description = "Automatically start experiments on VM boot"
  type        = bool
  default     = false
}
