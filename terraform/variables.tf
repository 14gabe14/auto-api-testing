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
  default     = "n1-standard-8" # 8 vCPUs, 30GB RAM - minimum recommended (original experiments used 64GB RAM but ran all services simultaneously)
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
  description = "Path to SSH public key file"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key file"
  type        = string
  default     = "~/.ssh/id_rsa"
}

variable "instance_count" {
  description = "Number of instances to create (for parallelization)"
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

variable "upload_results" {
  description = "Whether to upload results to Cloud Storage after experiment"
  type        = bool
  default     = true
}

variable "force_destroy_bucket" {
  description = "Whether to force destroy the bucket on terraform destroy"
  type        = bool
  default     = false
}

