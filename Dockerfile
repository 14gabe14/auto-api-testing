# Multi-stage build for LlamaRestTest
FROM ubuntu:20.04 as base

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    unzip wget gcc git vim \
    libcurl4-nss-dev tmux \
    mitmproxy curl \
    python3-pip python3-venv \
    maven gradle \
    && rm -rf /var/lib/apt/lists/*

# Install Java 8 and 11
RUN apt-get update \
    && apt-get install -y openjdk-8-jdk openjdk-11-jdk \
    && rm -rf /var/lib/apt/lists/*

# Set up Java environments
ENV JAVA8_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV JAVA11_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV JAVA_HOME=$JAVA11_HOME
ENV PATH=$JAVA_HOME/bin:$PATH

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --upgrade pip \
    && pip install requests schemathesis \
    && pip install -r requirements.txt

# Download and install EvoMaster
RUN wget https://github.com/EMResearch/EvoMaster/releases/download/v1.5.0/evomaster.jar.zip \
    && unzip evomaster.jar.zip \
    && rm evomaster.jar.zip

# Download Jacoco
RUN wget https://repo1.maven.org/maven2/org/jacoco/org.jacoco.agent/0.8.7/org.jacoco.agent-0.8.7-runtime.jar \
    && wget https://repo1.maven.org/maven2/org/jacoco/org.jacoco.cli/0.8.7/org.jacoco.cli-0.8.7-nodeps.jar

# Copy project files
COPY . .

# Create Java environment files
RUN echo "export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64" > java8.env \
    && echo "export PATH=\$JAVA_HOME/bin:\$PATH" >> java8.env \
    && echo "export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64" > java11.env \
    && echo "export PATH=\$JAVA_HOME/bin:\$PATH" >> java11.env

# Build Java services (with proper error handling)
RUN bash -c 'source java8.env && cd services/emb && mvn clean install -DskipTests && mvn dependency:build-classpath -Dmdep.outputFile=cp.txt' || echo "EMB build failed, continuing..."
RUN bash -c 'source java8.env && cd services/genome-nexus && mvn clean install -DskipTests' || echo "Genome-nexus build failed, continuing..."
RUN bash -c 'source java11.env && cd services/youtube && mvn clean install -DskipTests && mvn dependency:build-classpath -Dmdep.outputFile=cp.txt' || echo "YouTube build failed, continuing..."

# Build RestTestGen
RUN bash -c 'source java11.env && cd tool/resttestgen && chmod +x gradlew && ./gradlew install' || echo "RestTestGen build failed, continuing..."

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Activate Python virtual environment\n\
source /app/venv/bin/activate\n\
\n\
# Check if models directory exists and has models\n\
if [ ! -d "/app/models" ] || [ -z "$(ls -A /app/models)" ]; then\n\
    echo "Warning: No models found in /app/models directory."\n\
    echo "Please mount your LlamaREST models to /app/models volume."\n\
else\n\
    # Create symlinks for model files to match expected paths\n\
    find /app/models -name "*ex*.gguf" -exec ln -sf {} /app/ex.gguf \; 2>/dev/null || true\n\
    find /app/models -name "*ipd*.gguf" -exec ln -sf {} /app/ipd.gguf \; 2>/dev/null || true\n\
    echo "Model files linked successfully"\n\
fi\n\
\n\
# Execute the command\n\
exec "$@"\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 9001-9009 8080 50110-50112

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["bash", "-c", "echo 'LlamaRestTest container ready. Run: python3 run.py <tool> <service>' && tail -f /dev/null"]