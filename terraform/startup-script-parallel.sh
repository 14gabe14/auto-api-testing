#!/bin/bash
set -e

# Log all output
exec > >(tee -a /var/log/llamaresttest-startup.log)
exec 2>&1

echo "=== LlamaRestTest Parallel Startup Script Started at $(date) ==="

# Update system
apt-get update
apt-get upgrade -y

# Install required packages
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    python3 \
    python3-pip \
    python3-venv \
    software-properties-common \
    unzip \
    wget \
    gcc \
    vim

# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Install gcloud CLI for Cloud Storage access
if ! command -v gsutil &> /dev/null; then
    echo "Installing gcloud CLI..."
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
    apt-get update && apt-get install -y google-cloud-sdk
fi

# Install Python dependencies for orchestration
pip3 install docker psutil

# Add user to docker group
usermod -aG docker ubuntu

# Create directories
mkdir -p /home/ubuntu/llamaresttest
mkdir -p /home/ubuntu/llamaresttest/models
mkdir -p /home/ubuntu/llamaresttest/results
mkdir -p /home/ubuntu/.ssh

# Set permissions
chown -R ubuntu:ubuntu /home/ubuntu/llamaresttest
chown -R ubuntu:ubuntu /home/ubuntu/.ssh

# Clone repository if repo_url is provided
if [ -n "${repo_url}" ]; then
    echo "Cloning repository from ${repo_url}..."
    cd /home/ubuntu
    sudo -u ubuntu git clone "${repo_url}" llamaresttest || {
        echo "Failed to clone repository, continuing with manual setup..."
    }
else
    echo "No repository URL provided. Manual setup required."
fi

# Download models from Cloud Storage
if [ -n "${bucket_name}" ] && [ -n "${models_path}" ]; then
    echo "Downloading models from gs://${bucket_name}/${models_path}/..."
    cd /home/ubuntu/llamaresttest
    sudo -u ubuntu gsutil -m cp -r "gs://${bucket_name}/${models_path}/*" ./models/ 2>&1 || {
        echo "Warning: Failed to download models from Cloud Storage. Models may need to be uploaded manually."
    }
fi

# Ensure Docker starts on boot
systemctl enable docker
systemctl start docker

# Wait for Docker to be ready
echo "Waiting for Docker to be ready..."
for i in {1..30}; do
    if docker info > /dev/null 2>&1; then
        echo "Docker is ready"
        break
    fi
    sleep 2
done

# Build Docker images
if [ -d "/home/ubuntu/llamaresttest" ]; then
    echo "Building Docker images..."
    cd /home/ubuntu/llamaresttest
    
    # Build all images non-interactively
    sudo -u ubuntu python3 << 'PYTHON_EOF'
import docker
import os
import sys

DOCKER_CLIENT = docker.from_env()
DOCKER_PREFIX = "llamaresttest-"

def get_apis():
    apis_dir = './apis'
    if not os.path.exists(apis_dir):
        return []
    apis = [d for d in os.listdir(apis_dir) 
            if os.path.isdir(os.path.join(apis_dir, d)) 
            and os.path.exists(os.path.join(apis_dir, d, 'Dockerfile'))
            and d != 'CUSTOM-API']
    return apis

def build_image(name, is_api=True):
    image_name = f"{DOCKER_PREFIX}{name}"
    print(f"\nBuilding {'API' if is_api else 'Tool'}: {name}")
    try:
        image, build_logs = DOCKER_CLIENT.images.build(
            path='.',
            tag=image_name,
            rm=True,
            forcerm=True
        )
        print(f"✓ Successfully built {image_name}")
        return True
    except Exception as e:
        print(f"✗ Failed to build {image_name}: {e}")
        return False

# Build APIs
apis = get_apis()
print(f"Building {len(apis)} API images...")
for api in apis:
    build_image(api, is_api=True)

# Build tool
print("Building tool image...")
build_image('llamaresttest', is_api=False)

print("\nDocker image build complete!")
PYTHON_EOF
fi

# Create experiment runner script
cat > /home/ubuntu/llamaresttest/run-experiment-parallel.sh << 'EXPERIMENT_EOF'
#!/bin/bash
set -e

BUCKET_NAME="${bucket_name}"
RESULTS_PATH="${results_path}"
UPLOAD_RESULTS="${upload_results}"
NUM_RUNS="${num_runs}"

echo "=== Starting parallel experiments at $(date) ==="

cd /home/ubuntu/llamaresttest

# Run parallel experiments
echo "Running experiments with ${NUM_RUNS} run(s) per API/tool combination..."
echo "${NUM_RUNS}" | python3 run_parallel.py || {
    echo "Experiment failed with exit code $?"
    exit 1
}

# Upload results to Cloud Storage if enabled
if [ "$UPLOAD_RESULTS" = "true" ] && [ -n "$BUCKET_NAME" ] && [ -n "$RESULTS_PATH" ]; then
    echo "Uploading results to gs://$BUCKET_NAME/$RESULTS_PATH/..."
    RUN_ID="batch-$(date +%Y%m%d-%H%M%S)"
    gsutil -m cp -r results/* "gs://$BUCKET_NAME/$RESULTS_PATH/$RUN_ID/" 2>&1 || {
        echo "Warning: Failed to upload results to Cloud Storage"
    }
    echo "Results uploaded to gs://$BUCKET_NAME/$RESULTS_PATH/$RUN_ID/"
fi

echo "=== Experiments completed at $(date) ==="
EXPERIMENT_EOF

chmod +x /home/ubuntu/llamaresttest/run-experiment-parallel.sh
chown ubuntu:ubuntu /home/ubuntu/llamaresttest/run-experiment-parallel.sh

# Create systemd service to run experiments
cat > /etc/systemd/system/llamaresttest-parallel.service << EOF
[Unit]
Description=LlamaRestTest Parallel Experiment Runner
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/llamaresttest
Environment="HOME=/home/ubuntu"
ExecStart=/home/ubuntu/llamaresttest/run-experiment-parallel.sh
StandardOutput=journal
StandardError=journal
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable llamaresttest-parallel.service

# Start the experiment service if auto-start is enabled
if [ "${auto_start}" = "true" ]; then
    echo "Auto-starting experiments..."
    systemctl start llamaresttest-parallel.service || {
        echo "Failed to start experiment service"
    }
else
    echo "Auto-start disabled. To start experiments manually, run:"
    echo "  sudo systemctl start llamaresttest-parallel.service"
fi

echo "=== Startup script completed at $(date) ==="
echo "Instance is ready for parallel experiments"

