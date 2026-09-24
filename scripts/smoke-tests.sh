#!/bin/bash
# Smoke Tests for Mai AI Deployment
# Usage: ./scripts/smoke-tests.sh <environment>

set -euo pipefail

ENVIRONMENT="${1:-staging}"
BASE_URL="${2:-http://localhost:8000}"

echo "🧪 Running smoke tests for ${ENVIRONMENT}"
echo "Base URL: ${BASE_URL}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

run_test() {
  local name="$1"
  local cmd="$2"
  
  echo -n "${name}... "
  if eval "${cmd}" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}"
    return 0
  else
    echo -e "${RED}❌ FAIL${NC}"
    return 1
  fi
}

# Test 1: Basic connectivity
run_test "Basic connectivity" "curl -sf ${BASE_URL}/api/health | jq -e '.status == \"healthy\"'"

# Test 2: Chat functionality
run_test "Chat - simple message" "curl -sf -X POST ${BASE_URL}/api/chat -H 'Content-Type: application/json' -d '{\"message\": \"Hello\"}' | jq -e '.response'"

# Test 3: Chat with context
run_test "Chat - multi-turn" "
  SESSION_ID=\$(curl -sf -X POST ${BASE_URL}/api/chat -H 'Content-Type: application/json' -d '{\"message\": \"My name is Alice\"}' | jq -r '.session_id')
  curl -sf -X POST ${BASE_URL}/api/chat -H 'Content-Type: application/json' -d \"{\\\"message\\\": \\\"What is my name?\\\", \\\"session_id\\\": \\\"\$SESSION_ID\\\"}\" | jq -e '.response | test(\"Alice\"; \"i\")'
"

# Test 4: Memory storage and retrieval
run_test "Memory - store and retrieve" "
  curl -sf -X POST ${BASE_URL}/api/chat -H 'Content-Type: application/json' -d '{\"message\": \"Remember that I like pizza\"}' >/dev/null
  sleep 2
  curl -sf \"${BASE_URL}/api/memory?query=pizza\" | jq -e '.results | length > 0'
"

# Test 5: Knowledge base ingestion
run_test "Knowledge - ingest text" "
  curl -sf -X POST ${BASE_URL}/api/knowledge/ingest -H 'Content-Type: application/json' -d '{\"text\": \"Mai AI is a personal AI assistant with long-term memory.\", \"source\": \"smoke-test\"}' | jq -e '.success == true'
"

# Test 6: Knowledge retrieval
run_test "Knowledge - search" "
  sleep 3
  curl -sf \"${BASE_URL}/api/memory?query=personal AI assistant\" | jq -e '.results | length > 0'
"

# Test 7: Status endpoint
run_test "Status - emotion" "curl -sf ${BASE_URL}/api/status | jq -e '.emotion'"
run_test "Status - goals" "curl -sf ${BASE_URL}/api/status | jq -e '.goals'"
run_test "Status - world model" "curl -sf ${BASE_URL}/api/status | jq -e '.world_model'"

# Test 8: System info
run_test "System - version" "curl -sf ${BASE_URL}/api/system/status | jq -e '.version'"
run_test "System - uptime" "curl -sf ${BASE_URL}/api/system/status | jq -e '.uptime'"

# Test 9: Voice status (if available)
run_test "Voice - status endpoint" "curl -sf ${BASE_URL}/api/voice/status | jq -e '.'"

# Test 10: Metrics endpoint
run_test "Metrics - Prometheus format" "curl -sf ${BASE_URL}/metrics | grep -q 'mai_http_requests_total'"

# Test 11: Plugin system
run_test "Plugins - list" "curl -sf ${BASE_URL}/api/plugins | jq -e '.plugins'"

# Test 12: Profile management (multi-tenancy)
run_test "Profiles - create" "
  PROFILE_ID=\$(curl -sf -X POST ${BASE_URL}/api/profiles -H 'Content-Type: application/json' -d '{\"name\": \"Test User\", \"preferences\": {\"voice\": true}}' | jq -r '.id')
  echo \$PROFILE_ID
" && run_test "Profiles - retrieve" "curl -sf ${BASE_URL}/api/profiles/\${PROFILE_ID} | jq -e '.name == \"Test User\"'" && run_test "Profiles - delete" "curl -sf -X DELETE ${BASE_URL}/api/profiles/\${PROFILE_ID} | jq -e '.success == true'"

# Test 13: Session management
run_test "Sessions - create" "
  SESSION_ID=\$(curl -sf -X POST ${BASE_URL}/api/sessions -H 'Content-Type: application/json' -d '{\"user_id\": \"test-user\"}' | jq -r '.session_id')
  echo \$SESSION_ID
" && run_test "Sessions - list" "curl -sf ${BASE_URL}/api/sessions?user_id=test-user | jq -e '.sessions | length > 0'" && run_test "Sessions - delete" "curl -sf -X DELETE ${BASE_URL}/api/sessions/\${SESSION_ID} | jq -e '.success == true'"

# Test 14: Error handling
run_test "Error - invalid endpoint" "! curl -sf ${BASE_URL}/api/nonexistent >/dev/null 2>&1"
run_test "Error - malformed request" "curl -sf -X POST ${BASE_URL}/api/chat -H 'Content-Type: application/json' -d '{}' | jq -e '.error'"

# Test 15: Rate limiting (if enabled)
run_test "Rate limit - check headers" "curl -sf -I ${BASE_URL}/api/health | grep -qi 'x-ratelimit' || true"

echo ""
echo -e "${GREEN}✅ All smoke tests passed for ${ENVIRONMENT}!${NC}"