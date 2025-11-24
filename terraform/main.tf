terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Service account for the VM
resource "google_service_account" "llamaresttest" {
  account_id   = "llamaresttest-sa"
  display_name = "LlamaRestTest Service Account"
}

# Grant necessary permissions
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.llamaresttest.email}"
}

resource "google_project_iam_member" "compute_instance_admin" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.llamaresttest.email}"
}

# Use existing Cloud Storage bucket for models and results
# Bucket is assumed to already exist (e.g., "my-experiment")
# Models should be in: gs://{bucket_name}/LlamaRestTest/
# Results will be stored in: gs://{bucket_name}/llamaresttest-results/

# Compute instance(s) - supports both single and multiple instances
resource "google_compute_instance" "llamaresttest" {
  count        = var.instance_count
  name         = var.instance_count == 1 ? var.instance_name : "${var.instance_name}-${count.index + 1}"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2004-lts"
      size  = var.disk_size
      type  = var.disk_type # pd-standard is cheaper, pd-ssd is faster
    }
  }

  network_interface {
    network = "default"
    access_config {
      # Ephemeral public IP
    }
  }

  service_account {
    email  = google_service_account.llamaresttest.email
    scopes = ["cloud-platform"]
  }

  metadata = var.ssh_public_key_path != "" ? {
    ssh-keys = "${var.ssh_user}:${try(file(var.ssh_public_key_path), "")}"
  } : {}

  metadata_startup_script = templatefile("${path.module}/startup-script.sh", {
    docker_compose_version = "2.24.0"
    project_id             = var.project_id
    bucket_name            = var.storage_bucket_name
    models_path            = var.models_path
    results_path           = var.results_path
    repo_url               = var.repo_url
    tool_name              = length(var.experiment_configs) > count.index ? var.experiment_configs[count.index].tool : var.default_tool
    service_name           = length(var.experiment_configs) > count.index ? var.experiment_configs[count.index].service : var.default_service
    omdb_token             = var.omdb_token
    spotify_token          = var.spotify_token
    upload_results         = var.upload_results
  })

  tags = ["llamaresttest"]

  allow_stopping_for_update = true
}

# Firewall rule for SSH
resource "google_compute_firewall" "ssh" {
  name    = "allow-ssh-llamaresttest"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["llamaresttest"]
}

# Firewall rules for service ports (9001-9009, 8080, 27018, 50110-50112)
resource "google_compute_firewall" "llamaresttest_ports" {
  name    = "allow-llamaresttest-ports"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["9001", "9002", "9003", "9004", "9005", "9006", "9007", "9008", "9009", "8080", "27018", "50110", "50111", "50112"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["llamaresttest"]
}

# Output the instance IPs
output "instance_ips" {
  value       = [for instance in google_compute_instance.llamaresttest : instance.network_interface[0].access_config[0].nat_ip]
  description = "Public IP addresses of the LlamaRestTest instances"
}

output "instance_names" {
  value       = [for instance in google_compute_instance.llamaresttest : instance.name]
  description = "Names of the created instances"
}

output "ssh_commands" {
  value       = [for instance in google_compute_instance.llamaresttest : "ssh -i ${var.ssh_private_key_path} ${var.ssh_user}@${instance.network_interface[0].access_config[0].nat_ip}"]
  description = "SSH commands to connect to the instances"
}

output "bucket_name" {
  value       = var.storage_bucket_name
  description = "Cloud Storage bucket name being used"
}

output "models_path" {
  value       = "gs://${var.storage_bucket_name}/${var.models_path}"
  description = "Cloud Storage path for models"
}

output "results_path" {
  value       = "gs://${var.storage_bucket_name}/${var.results_path}/"
  description = "Cloud Storage path for results"
}

