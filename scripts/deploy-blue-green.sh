#!/bin/bash
# Blue-Green Deployment Script for Mai AI
# Usage: ./scripts/deploy-blue-green.sh <environment> <image-tag>

set -euo pipefail

ENVIRONMENT="${1:-staging}"
IMAGE_TAG="${2:-latest}"
NAMESPACE="mai-${ENVIRONMENT}"
COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"
BLUE_SERVICE="mai-ai-blue"
GREEN_SERVICE="mai-ai-green"
NGINX_SERVICE="nginx"
HEALTH_ENDPOINT="/api/health"
MAX_WAIT=300
CHECK_INTERVAL=5

echo "🚀 Starting blue-green deployment to ${ENVIRONMENT}"
echo "Image tag: ${IMAGE_TAG}"
echo "Namespace: ${NAMESPACE}"

# Determine current active color
get_active_color() {
  if docker-compose -f "${COMPOSE_FILE}" ps --services --filter "status=running" | grep -q "${BLUE_SERVICE}"; then
    if docker-compose -f "${COMPOSE_FILE}" exec -T "${BLUE_SERVICE}" curl -sf "http://localhost:8000${HEALTH_ENDPOINT}" >/dev/null 2>&1; then
      echo "blue"
      return
    fi
  fi
  if docker-compose -f "${COMPOSE_FILE}" ps --services --filter "status=running" | grep -q "${GREEN_SERVICE}"; then
    if docker-compose -f "${COMPOSE_FILE}" exec -T "${GREEN_SERVICE}" curl -sf "http://localhost:8000${HEALTH_ENDPOINT}" >/dev/null 2>&1; then
      echo "green"
      return
    fi
  fi
  echo "none"
}

# Determine inactive color
get_inactive_color() {
  local active=$(get_active_color)
  if [[ "${active}" == "blue" ]]; then
    echo "green"
  elif [[ "${active}" == "green" ]]; then
    echo "blue"
  else
    echo "blue"  # Default to blue if none active
  fi
}

ACTIVE_COLOR=$(get_active_color)
INACTIVE_COLOR=$(get_inactive_color)

echo "Current active: ${ACTIVE_COLOR}"
echo "Deploying to: ${INACTIVE_COLOR}"

# Update the inactive service with new image
INACTIVE_SERVICE="mai-ai-${INACTIVE_COLOR}"
echo "Updating ${INACTIVE_SERVICE} with image ${IMAGE_TAG}"

# Update docker-compose with new image
sed -i "s|image:.*${INACTIVE_SERVICE}:.*|image: ${IMAGE_TAG}|g" "${COMPOSE_FILE}"

# Start the new version
echo "Starting ${INACTIVE_SERVICE}..."
docker-compose -f "${COMPOSE_FILE}" up -d --no-deps "${INACTIVE_SERVICE}"

# Wait for health check
echo "Waiting for ${INACTIVE_SERVICE} to become healthy..."
WAITED=0
while [[ ${WAITED} -lt ${MAX_WAIT} ]]; do
  if docker-compose -f "${COMPOSE_FILE}" exec -T "${INACTIVE_SERVICE}" curl -sf "http://localhost:8000${HEALTH_ENDPOINT}" >/dev/null 2>&1; then
    echo "✅ ${INACTIVE_SERVICE} is healthy"
    break
  fi
  sleep ${CHECK_INTERVAL}
  WAITED=$((WAITED + CHECK_INTERVAL))
  echo "  Waited ${WAITED}s..."
done

if [[ ${WAITED} -ge ${MAX_WAIT} ]]; then
  echo "❌ ${INACTIVE_SERVICE} failed to become healthy within ${MAX_WAIT}s"
  docker-compose -f "${COMPOSE_FILE}" logs "${INACTIVE_SERVICE}"
  exit 1
fi

# Run additional verification
echo "Running post-start verification..."
docker-compose -f "${COMPOSE_FILE}" exec -T "${INACTIVE_SERVICE}" python -c "
import requests
r = requests.get('http://localhost:8000/api/health', timeout=5)
assert r.status_code == 200
data = r.json()
assert data.get('status') == 'healthy'
print('Health check passed:', data)
"

# Switch traffic (update nginx config)
echo "Switching traffic to ${INACTIVE_COLOR}..."
NGINX_CONF="nginx.${ENVIRONMENT}.conf"
# Update upstream in nginx config
sed -i "s|server ${BLUE_SERVICE}:8000|server ${INACTIVE_SERVICE}:8000|g" "${NGINX_CONF}"
sed -i "s|server ${GREEN_SERVICE}:8000|server ${INACTIVE_SERVICE}:8000|g" "${NGINX_CONF}"

# Reload nginx
docker-compose -f "${COMPOSE_FILE}" exec -T "${NGINX_SERVICE}" nginx -s reload

# Verify traffic switch
sleep 5
echo "Verifying traffic switch..."
for i in {1..10}; do
  if curl -sf "http://localhost${HEALTH_ENDPOINT}" >/dev/null 2>&1; then
    echo "✅ Traffic successfully switched to ${INACTIVE_COLOR}"
    break
  fi
  sleep 2
done

# Stop old version (after grace period)
echo "Grace period before stopping old version..."
sleep 30

OLD_SERVICE="mai-ai-${ACTIVE_COLOR}"
if [[ "${ACTIVE_COLOR}" != "none" && "${ACTIVE_COLOR}" != "${INACTIVE_COLOR}" ]]; then
  echo "Stopping old version: ${OLD_SERVICE}"
  docker-compose -f "${COMPOSE_FILE}" stop "${OLD_SERVICE}"
  docker-compose -f "${COMPOSE_FILE}" rm -f "${OLD_SERVICE}"
fi

# Cleanup old images
echo "Cleaning up old images..."
docker image prune -f --filter "until=24h"

echo "✅ Blue-green deployment to ${ENVIRONMENT} completed successfully!"
echo "Active version: ${INACTIVE_COLOR} (${IMAGE_TAG})"