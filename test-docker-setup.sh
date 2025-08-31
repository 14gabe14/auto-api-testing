#!/bin/bash

# Test script to validate Docker setup without running Docker daemon

echo "=== Testing LlamaRestTest Docker Setup ==="
echo

# Test 1: Check if all required files exist
echo "1. Checking required files..."
required_files=(
    "Dockerfile"
    "docker-compose.yml"
    "docker-run.py"
    "docker-run.sh"
    "Makefile"
    "DOCKER_README.md"
    "requirements.txt"
    "run.py"
    "services/run_service.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file exists"
    else
        echo "  ✗ $file missing"
        exit 1
    fi
done

# Test 2: Check docker-compose syntax
echo
echo "2. Validating docker-compose.yml syntax..."
if docker-compose config > /dev/null 2>&1; then
    echo "  ✓ docker-compose.yml syntax is valid"
else
    echo "  ✗ docker-compose.yml has syntax errors"
    exit 1
fi

# Test 3: Test Python script
echo
echo "3. Testing Python wrapper script..."
if python3 docker-run.py --help > /dev/null 2>&1; then
    echo "  ✓ Python script works correctly"
else
    echo "  ✗ Python script has errors"
    exit 1
fi

# Test 4: Test bash script
echo
echo "4. Testing bash wrapper script..."
if bash docker-run.sh --help > /dev/null 2>&1; then
    echo "  ✓ Bash script works correctly"
else
    echo "  ✗ Bash script has errors"
    exit 1
fi

# Test 5: Test Makefile
echo
echo "5. Testing Makefile..."
if make help > /dev/null 2>&1; then
    echo "  ✓ Makefile works correctly"
else
    echo "  ✗ Makefile has errors"
    exit 1
fi

# Test 6: Test argument validation
echo
echo "6. Testing argument validation..."
if python3 docker-run.py invalid-tool fdic 2>&1 | grep -q "invalid choice"; then
    echo "  ✓ Python script validates arguments correctly"
else
    echo "  ✗ Python script argument validation failed"
    exit 1
fi

if bash docker-run.sh invalid-tool fdic 2>&1 | grep -q "Invalid tool"; then
    echo "  ✓ Bash script validates arguments correctly"
else
    echo "  ✗ Bash script argument validation failed"
    exit 1
fi

# Test 7: Check directory creation
echo
echo "7. Testing directory creation..."
if make setup-models > /dev/null 2>&1 && [ -d "models" ]; then
    echo "  ✓ Models directory creation works"
else
    echo "  ✗ Models directory creation failed"
    exit 1
fi

echo
echo "=== All tests passed! Docker setup is ready to use. ==="
echo
echo "To use the Docker setup:"
echo "1. Start Docker daemon"
echo "2. Place your .gguf model files in the models/ directory"
echo "3. Run: make run-example"
echo "   or: python3 docker-run.py llamaresttest fdic"
echo "   or: bash docker-run.sh llamaresttest fdic"