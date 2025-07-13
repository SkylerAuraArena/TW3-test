# Load environment variables from .env file
set -a
source .env
set +a

#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Redirect all output to setup.log and reset the log file at each launch
LOG_FILE="setup.log"
> "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

# Variables
NETWORK_NAME="tw3_network"
VOLUME_NAME="tw3_data_volume"
LOG_DIR="logs"
DOCKER_IMAGES=(
  "tw3_backend:1.0:docker/images/backend/Dockerfile"
  "tw3_frontend:1.0:docker/images/frontend/Dockerfile"
)

# Function to check if a Docker network exists
check_network_exists() {
  docker network ls --format '{{.Name}}' | grep -wq "$NETWORK_NAME"
}

# Function to check if a Docker volume exists
check_volume_exists() {
  docker volume ls --format '{{.Name}}' | grep -wq "$VOLUME_NAME"
}

# Function to build Docker images if they don't exist
build_docker_image() {
  local image_name=$1
  local dockerfile_path=$2

  if ! docker images | grep -w "${image_name%:*}" | grep -w "${image_name#*:}" > /dev/null; then
    echo "Building Docker image '$image_name'..."
    docker image build -t "$image_name" -f "$dockerfile_path" .
    echo "Docker image '$image_name' built successfully."
  else
    echo "Docker image '$image_name' already exists. Skipping build."
  fi
}

# 1. Create Docker network if necessary
echo "Checking for Docker network '$NETWORK_NAME'..."
if check_network_exists; then
  echo "Docker network '$NETWORK_NAME' already exists."
else
  echo "Creating Docker network '$NETWORK_NAME'..."
  docker network create "$NETWORK_NAME"
  echo "Docker network '$NETWORK_NAME' created successfully."
fi

# 2. Create Docker volume if necessary
echo "Checking for Docker volume '$VOLUME_NAME'..."
if check_volume_exists; then
  echo "Docker volume '$VOLUME_NAME' already exists."
else
  echo "Creating Docker volume '$VOLUME_NAME'..."
  docker volume create --name "$VOLUME_NAME"
  echo "Docker volume '$VOLUME_NAME' created successfully."
fi

# 3. Build Docker images
echo "Building Docker images if necessary..."
for image_entry in "${DOCKER_IMAGES[@]}"; do
  image_name=$(echo "$image_entry" | cut -d':' -f1,2)
  dockerfile_path=$(echo "$image_entry" | cut -d':' -f3-)
  build_docker_image "$image_name" "$dockerfile_path"
done

# 4. Start Docker Compose
echo "Starting Docker Compose..."
docker-compose -f docker/docker-compose.yml up --build --remove-orphans
echo "Docker Compose started successfully."