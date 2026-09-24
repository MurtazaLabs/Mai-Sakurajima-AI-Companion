#!/bin/bash
# Rollback Script for Mai AI
# Usage: ./scripts/rollback.sh <environment> [revision]

set -euo pipefail

ENVIRONMENT="${1:-staging}"
REVISION="${2:-}"
COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"
BLUE_SERVICE="mai-ai-blue"
GREEN_SERVICE="mai-ai-green"
NGINX_SERVICE="nginx"
HEALTH_ENDPOINT="/api/health"

echo "🔄 Initiating rollback for ${ENVIRONMENT}"
if [[ -n "${REVISION}" ]]; then
  echo "Target revision: ${REVISION}"
else
  echo "Rolling back to previous version"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get current active color
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

ACTIVE_COLOR=$(get_active_color)
INACTIVE_COLOR=$([[ "${ACTIVE_COLOR}" == "blue" ]] && echo "green" || echo "blue")

echo "Current active: ${ACTIVE_COLOR}"
echo "Rollback target: ${INACTIVE_COLOR}"

# If revision specified, use that image
if [[ -n "${REVISION}" ]]; then
  INACTIVE_SERVICE="mai-ai-${INACTIVE_COLOR}"
  echo "Updating ${INACTIVE_SERVICE} to revision ${REVISION}"
  sed -i "s|image:.*${INACTIVE_SERVICE}:.*|image: ${REVISION}|g" "${COMPOSE_FILE}"
  docker-compose -f "${COMPOSE_FILE}" up -d --no-deps "${INACTIVE_SERVICE}"
else
  # Just start the inactive service (should have previous image)
  INACTIVE_SERVICE="mai-ai-${INACTIVE_COLOR}"
  echo "Starting previous version: ${INACTIVE_SERVICE}"
  docker-compose -f "${COMPOSE_FILE}" up -d --no-deps "${INACTIVE_SERVICE}"
fi

# Wait for health
echo "Waiting for ${INACTIVE_SERVICE} to become healthy..."
WAITED=0
MAX_WAIT=180
while [[ ${WAITED} -lt ${MAX_WAIT} ]]; do
  if docker-compose -f "${COMPOSE_FILE}" exec -T "${INACTIVE_SERVICE}" curl -sf "http://localhost:8000${HEALTH_ENDPOINT}" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ ${INACTIVE_SERVICE} is healthy${NC}"
    break
  fi
  sleep 5
  WAITED=$((WAITED + 5))
done

if [[ ${WAITED} -ge ${MAX_WAIT} ]]; then
  echo -e "${RED}❌ Rollback failed: ${INACTIVE_SERVICE} did not become healthy${NC}"
  exit 1
fi

# Switch traffic
echo "Switching traffic to ${INACTIVE_COLOR}..."
NGINX_CONF="nginx.${ENVIRONMENT}.conf"
sed -i "s|server ${BLUE_SERVICE}:8000|server ${INACTIVE_SERVICE}:8000|g" "${NGINX_CONF}"
sed -i "s|server ${GREEN_SERVICE}:8000|server ${INACTIVE_SERVICE}:8000|g" "${NGINX_CONF}"
docker-compose -f "${COMPOSE_FILE}" exec -T "${NGINX_SERVICE}" nginx -s reload

# Verify
sleep 5
if curl -sf "http://localhost${HEALTH_ENDPOINT}" >/dev/null 2>&1; then
  echo -e "${GREEN}✅ Traffic switched successfully${NC}"
else
  echo -e "${RED}❌ Traffic switch failed${NC}"
  exit 1
fi

# Stop problematic version
echo "Stopping problematic version: ${ACTIVE_COLOR}"
OLD_SERVICE="mai-ai-${ACTIVE_COLOR}"
if [[ "${ACTIVE_COLOR}" != "none" ]]; then
  docker-compose -f "${COMPOSE_FILE}" stop "${OLD_SERVICE}"
  docker-compose -f "${COMPOSE_FILE}" rm -f "${OLD_SERVICE}"
fi

# Log rollback event
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") ROLLBACK ${ENVIRONMENT} from ${ACTIVE_COLOR} to ${INACTIVE_COLOR} ${REVISION:-previous}" >> rollback.log

echo -e "${GREEN}✅ Rollback completed successfully!${NC}"
echo "Active version is now: ${INACTIVE_COLOR}"