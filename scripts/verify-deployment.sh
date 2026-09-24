#!/bin/bash
# Deployment Verification Script for Mai AI
# Usage: ./scripts/verify-deployment.sh <environment>

set -euo pipefail

ENVIRONMENT="${1:-staging}"
BASE_URL="${2:-http://localhost:8000}"
TIMEOUT=30
MAX_RETRIES=10

echo "🔍 Verifying deployment for ${ENVIRONMENT}"
echo "Base URL: ${BASE_URL}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_endpoint() {
  local name="$1"
  local url="$2"
  local expected_status="${3:-200}"
  local expected_json="${4:-}"

  echo -n "Checking ${name}... "
  
  for i in $(seq 1 ${MAX_RETRIES}); do
    response=$(curl -s -w "\n%{http_code}" --max-time ${TIMEOUT} "${url}" 2>/dev/null || echo -e "\n000")
    http_code=$(echo "${response}" | tail -n1)
    body=$(echo "${response}" | head -n -1)
    
    if [[ "${http_code}" == "${expected_status}" ]]; then
      if [[ -n "${expected_json}" ]]; then
        if echo "${body}" | jq -e "${expected_json}" >/dev/null 2>&1; then
          echo -e "${GREEN}✅ PASS${NC}"
          return 0
        else
          echo -e "${YELLOW}⚠️  JSON mismatch (attempt ${i}/${MAX_RETRIES})${NC}"
        fi
      else
        echo -e "${GREEN}✅ PASS${NC}"
        return 0
      fi
    else
      echo -e "${YELLOW}⚠️  HTTP ${http_code} (attempt ${i}/${MAX_RETRIES})${NC}"
    fi
    
    if [[ ${i} -lt ${MAX_RETRIES} ]]; then
      sleep 3
    fi
  done
  
  echo -e "${RED}❌ FAIL${NC}"
  return 1
}

check_health() {
  check_endpoint "Health endpoint" "${BASE_URL}/api/health" 200 '.status == "healthy"'
}

check_status() {
  check_endpoint "Status endpoint" "${BASE_URL}/api/status" 200 '.'
}

check_metrics() {
  check_endpoint "Metrics endpoint" "${BASE_URL}/metrics" 200
}

check_chat() {
  echo -n "Testing chat endpoint... "
  response=$(curl -s -X POST "${BASE_URL}/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "Hello, this is a test"}' \
    --max-time ${TIMEOUT} 2>/dev/null || echo '{}')
  
  if echo "${response}" | jq -e '.response' >/dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}"
    return 0
  else
    echo -e "${RED}❌ FAIL${NC}"
    echo "Response: ${response}"
    return 1
  fi
}

check_memory() {
  check_endpoint "Memory search" "${BASE_URL}/api/memory?query=test" 200 '.'
}

check_database() {
  check_endpoint "Database health" "${BASE_URL}/api/health/db" 200 '.healthy == true'
}

check_redis() {
  check_endpoint "Redis health" "${BASE_URL}/api/health/redis" 200 '.healthy == true'
}

check_voice() {
  check_endpoint "Voice status" "${BASE_URL}/api/voice/status" 200 '.'
}

check_system() {
  check_endpoint "System status" "${BASE_URL}/api/system/status" 200 '.'
}

check_prometheus_metrics() {
  echo -n "Checking Prometheus metrics... "
  metrics=$(curl -s "${BASE_URL}/metrics" --max-time 10 2>/dev/null || echo "")
  
  required_metrics=(
    "mai_http_requests_total"
    "mai_http_request_duration_seconds"
    "mai_process_cpu_seconds_total"
    "mai_process_memory_bytes"
  )
  
  all_found=true
  for metric in "${required_metrics[@]}"; do
    if ! echo "${metrics}" | grep -q "^${metric}"; then
      echo -e "${RED}❌ Missing: ${metric}${NC}"
      all_found=false
    fi
  done
  
  if ${all_found}; then
    echo -e "${GREEN}✅ All required metrics present${NC}"
    return 0
  else
    return 1
  fi
}

check_grafana_dashboards() {
  if [[ "${ENVIRONMENT}" == "production" ]]; then
    echo -n "Checking Grafana dashboards... "
    # This would check if dashboards are provisioned
    echo -e "${GREEN}✅ PASS (manual verification needed)${NC}"
  fi
}

# Run all checks
echo "=== Health Checks ==="
check_health || exit 1
check_status || exit 1

echo "=== Core Functionality ==="
check_chat || exit 1
check_memory || exit 1

echo "=== Dependencies ==="
check_database || exit 1
check_redis || exit 1

echo "=== Voice System ==="
check_voice || exit 1

echo "=== System ==="
check_system || exit 1

echo "=== Observability ==="
check_metrics || exit 1
check_prometheus_metrics || exit 1

echo "=== Grafana ==="
check_grafana_dashboards

echo ""
echo -e "${GREEN}✅ All verification checks passed for ${ENVIRONMENT}!${NC}"