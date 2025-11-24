#!/bin/bash
set -e

# Log all output
exec > >(tee -a /var/log/llamaresttest-startup.log)
exec 2>&1

echo "=== LlamaRestTest Startup Script Started at $(date) ==="

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
    vim \
    libcurl4-nss-dev \
    tmux \
    maven \
    gradle \
    openjdk-8-jdk \
    openjdk-11-jdk

# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Install Docker Compose (standalone)
DOCKER_COMPOSE_VERSION="${docker_compose_version}"
curl -L "https://github.com/docker/compose/releases/download/v$${DOCKER_COMPOSE_VERSION}/docker-compose-$$(uname -s)-$$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install mitmproxy
pip3 install mitmproxy

# Install gcloud CLI for Cloud Storage access
if ! command -v gsutil &> /dev/null; then
    echo "Installing gcloud CLI..."
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
    apt-get update && apt-get install -y google-cloud-sdk
    # Use application default credentials (already available via service account)
fi

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

# Configure authentication tokens
if [ -n "${omdb_token}" ]; then
    echo "Configuring OMDB token..."
    cd /home/ubuntu/llamaresttest
    if [ -f "services/omdb.py" ]; then
        sudo -u ubuntu sed -i "s/TOKEN_HERE/${omdb_token}/g" services/omdb.py
    fi
fi

if [ -n "${spotify_token}" ]; then
    echo "Configuring Spotify token..."
    cd /home/ubuntu/llamaresttest
    if [ -f "services/spotify.py" ]; then
        sudo -u ubuntu sed -i "s/TOKEN_HERE/${spotify_token}/g" services/spotify.py
    fi
fi

# Create experiment runner script
cat > /home/ubuntu/llamaresttest/run-experiment.sh << EXPERIMENT_EOF
#!/bin/bash
set -e

TOOL_NAME="${tool_name}"
SERVICE_NAME="${service_name}"
BUCKET_NAME="${bucket_name}"
RESULTS_PATH="${results_path}"
UPLOAD_RESULTS="${upload_results}"

echo "=== Starting experiment: \$TOOL_NAME on \$SERVICE_NAME at \$(date) ==="

cd /home/ubuntu/llamaresttest

# Activate Python virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the experiment
echo "Running: python3 run.py \$TOOL_NAME \$SERVICE_NAME"
python3 run.py "\$TOOL_NAME" "\$SERVICE_NAME" || {
    echo "Experiment failed with exit code \$?"
    exit 1
}

# Collect results
if [ -f "collect.py" ]; then
    echo "Collecting results..."
    python3 collect.py || echo "Warning: Result collection failed"
fi

# Upload results to Cloud Storage if enabled
if [ "\$UPLOAD_RESULTS" = "true" ] && [ -n "\$BUCKET_NAME" ] && [ -n "\$RESULTS_PATH" ]; then
    echo "Uploading results to gs://\$BUCKET_NAME/\$RESULTS_PATH/\$TOOL_NAME/\$SERVICE_NAME/..."
    RUN_ID="run-\$(date +%Y%m%d-%H%M%S)"
    gsutil -m cp -r results/* "gs://\$BUCKET_NAME/\$RESULTS_PATH/\$TOOL_NAME/\$SERVICE_NAME/\$RUN_ID/" 2>&1 || {
        echo "Warning: Failed to upload results to Cloud Storage"
    }
    echo "Results uploaded to gs://\$BUCKET_NAME/\$RESULTS_PATH/\$TOOL_NAME/\$SERVICE_NAME/\$RUN_ID/"
fi

echo "=== Experiment completed at \$(date) ==="

# Optionally shut down the instance after completion
sudo shutdown -h +5  # Shutdown in 5 minutes
EXPERIMENT_EOF

chmod +x /home/ubuntu/llamaresttest/run-experiment.sh
chown ubuntu:ubuntu /home/ubuntu/llamaresttest/run-experiment.sh

# Create systemd service to run experiment on boot (if tool and service are configured)
if [ -n "${tool_name}" ] && [ -n "${service_name}" ]; then
    cat > /etc/systemd/system/llamaresttest-experiment.service << EOF
[Unit]
Description=LlamaRestTest Experiment Runner
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/llamaresttest
Environment="HOME=/home/ubuntu"
ExecStart=/home/ubuntu/llamaresttest/run-experiment.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable llamaresttest-experiment.service
    
    # Start the experiment service (non-blocking)
    systemctl start llamaresttest-experiment.service || {
        echo "Failed to start experiment service, will run manually"
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

echo "=== Startup script completed at $(date) ==="
echo "Instance is ready. Tool: ${tool_name}, Service: ${service_name}"
