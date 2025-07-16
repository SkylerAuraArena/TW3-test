#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════════
# TW3 Setup Script - Automated Docker Environment Deployment
# ═══════════════════════════════════════════════════════════════════════════════
# Description: Automated setup for TW3 chat application with Docker containers
# Version: 1.0.0
# Author: SkylerAuraArena
# ═══════════════════════════════════════════════════════════════════════════════

# Load environment variables from .env file
set -a
if [[ -f ".env" ]]; then
  source .env
  echo "Environment variables loaded from .env"
else
  echo "WARNING: No .env file found, using default environment"
fi
set +a

# Exit immediately if a command exits with a non-zero status
set -e

# Enable debugging if DEBUG environment variable is set
if [[ "${DEBUG:-false}" == "true" ]]; then
  set -x
  echo "Debug mode enabled"
fi

# ───── Configuration et logging ─────────────────────────────────────────────
LOG_FILE="setup.log"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# Reset log file with header
cat > "$LOG_FILE" << EOF
═══════════════════════════════════════════════════════════════════════════════
TW3 Setup Log - Started at $TIMESTAMP
═══════════════════════════════════════════════════════════════════════════════
EOF

# Redirect output to both console and log file
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Starting TW3 environment setup..."
echo "All output logged to: $LOG_FILE"

# ───── Configuration des ressources Docker ─────────────────────────────────
NETWORK_NAME="${DOCKER_NETWORK:-tw3_network}"
VOLUME_NAME="${DOCKER_VOLUME:-tw3_data_volume}"
LOG_DIR="logs"

# Images Docker avec configuration flexible
DOCKER_IMAGES=(
  "tw3_backend:${VERSION:-1.0}:docker/images/backend/Dockerfile"
  "tw3_frontend:${VERSION:-1.0}:docker/images/frontend/Dockerfile"
)

# Configuration des ports (overrideable via environment)
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

echo "Configuration:"
echo "   Network: $NETWORK_NAME"
echo "   Volume: $VOLUME_NAME"
echo "   Backend Port: $BACKEND_PORT"
echo "   Frontend Port: $FRONTEND_PORT"
echo "   Images to build: ${#DOCKER_IMAGES[@]}"

# ───── Fonctions utilitaires améliorées ─────────────────────────────────────

# Fonction pour afficher les messages avec timestamps
log_message() {
  local level=$1
  local message=$2
  local timestamp=$(date "+%H:%M:%S")
  
  case $level in
    "INFO")  echo "[$timestamp] INFO: $message" ;;
    "SUCCESS") echo "[$timestamp] SUCCESS: $message" ;;
    "WARNING") echo "[$timestamp] WARNING: $message" ;;
    "ERROR") echo "[$timestamp] ERROR: $message" ;;
    *) echo "[$timestamp] $message" ;;
  esac
}

# Function to check if a Docker network exists
check_network_exists() {
  docker network ls --format '{{.Name}}' | grep -wq "$NETWORK_NAME"
}

# Function to check if a Docker volume exists
check_volume_exists() {
  docker volume ls --format '{{.Name}}' | grep -wq "$VOLUME_NAME"
}

# Fonction pour vérifier les prérequis
check_prerequisites() {
  log_message "INFO" "Checking prerequisites..."
  
  # Vérifier Docker
  if ! command -v docker &> /dev/null; then
    log_message "ERROR" "Docker is not installed or not in PATH"
    exit 1
  fi
  
  # Vérifier Docker Compose
  if ! command -v docker-compose &> /dev/null; then
    log_message "ERROR" "Docker Compose is not installed or not in PATH"
    exit 1
  fi
  
  # Vérifier que Docker daemon est en cours d'exécution
  if ! docker info &> /dev/null; then
    log_message "ERROR" "Docker daemon is not running"
    exit 1
  fi
  
  # Vérifier les fichiers requis
  local required_files=("docker/docker-compose.yml" "docker/images/backend/Dockerfile" "docker/images/frontend/Dockerfile")
  for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
      log_message "ERROR" "Required file not found: $file"
      exit 1
    fi
  done
  
  log_message "SUCCESS" "All prerequisites checked successfully"
}

# Function to build Docker images if they don't exist
build_docker_image() {
  local image_name=$1
  local dockerfile_path=$2
  local start_time=$(date +%s)

  if ! docker images | grep -w "${image_name%:*}" | grep -w "${image_name#*:}" > /dev/null; then
    log_message "INFO" "Building Docker image '$image_name'..."
    
    if docker image build -t "$image_name" -f "$dockerfile_path" .; then
      local end_time=$(date +%s)
      local duration=$((end_time - start_time))
      log_message "SUCCESS" "Docker image '$image_name' built successfully in ${duration}s"
    else
      log_message "ERROR" "Failed to build Docker image '$image_name'"
      exit 1
    fi
  else
    log_message "INFO" "Docker image '$image_name' already exists. Skipping build."
  fi
}

# Fonction de nettoyage en cas d'interruption
cleanup() {
  log_message "WARNING" "Setup interrupted. Cleaning up..."
  # Optionnel: nettoyer les ressources partiellement créées
  exit 1
}

# Piège pour nettoyer en cas d'interruption
trap cleanup INT TERM

# ═══════════════════════════════════════════════════════════════════════════════
# DÉMARRAGE DU PROCESSUS DE SETUP
# ═══════════════════════════════════════════════════════════════════════════════

# 0. Vérification des prérequis
check_prerequisites

# 1. Create Docker network if necessary
log_message "INFO" "Checking for Docker network '$NETWORK_NAME'..."
if check_network_exists; then
  log_message "INFO" "Docker network '$NETWORK_NAME' already exists."
else
  log_message "INFO" "Creating Docker network '$NETWORK_NAME'..."
  if docker network create "$NETWORK_NAME"; then
    log_message "SUCCESS" "Docker network '$NETWORK_NAME' created successfully."
  else
    log_message "ERROR" "Failed to create Docker network '$NETWORK_NAME'"
    exit 1
  fi
fi

# 2. Create Docker volume if necessary
log_message "INFO" "Checking for Docker volume '$VOLUME_NAME'..."
if check_volume_exists; then
  log_message "INFO" "Docker volume '$VOLUME_NAME' already exists."
else
  log_message "INFO" "Creating Docker volume '$VOLUME_NAME'..."
  if docker volume create --name "$VOLUME_NAME"; then
    log_message "SUCCESS" "Docker volume '$VOLUME_NAME' created successfully."
  else
    log_message "ERROR" "Failed to create Docker volume '$VOLUME_NAME'"
    exit 1
  fi
fi

# 3. Build Docker images
log_message "INFO" "Building Docker images if necessary..."
for image_entry in "${DOCKER_IMAGES[@]}"; do
  image_name=$(echo "$image_entry" | cut -d':' -f1,2)
  dockerfile_path=$(echo "$image_entry" | cut -d':' -f3-)
  build_docker_image "$image_name" "$dockerfile_path"
done

# 4. Start Docker Compose
log_message "INFO" "Starting Docker Compose..."
if docker-compose -f docker/docker-compose.yml up --build --remove-orphans; then
  log_message "SUCCESS" "Docker Compose started successfully."
  log_message "INFO" "TW3 environment is now running!"
  log_message "INFO" "   Frontend: http://localhost:$FRONTEND_PORT"
  log_message "INFO" "   Backend API: http://localhost:$BACKEND_PORT"
  log_message "INFO" "   API Docs: http://localhost:$BACKEND_PORT/docs"
else
  log_message "ERROR" "Failed to start Docker Compose"
  exit 1
fi