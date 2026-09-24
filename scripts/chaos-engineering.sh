#!/bin/bash
# Chaos Engineering Experiments for Mai AI
# Usage: ./scripts/chaos-engineering.sh

set -euo pipefail

ENVIRONMENT="${1:-staging}"
COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"
BASE_URL="http://localhost:8000"
RESULTS_DIR="chaos-results/$(date +%Y%m%d-%H%M%S)"

mkdir -p "${RESULTS_DIR}"

echo "🧪 Starting Chaos Engineering Experiments"
echo "Environment: ${ENVIRONMENT}"
echo "Results: ${RESULTS_DIR}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

run_experiment() {
  local name="$1"
  local description="$2"
  local command="$3"
  local validation="$4"
  local cleanup="$5"
  
  echo ""
  echo "========================================"
  echo "Experiment: ${name}"
  echo "Description: ${description}"
  echo "========================================"
  
  local start_time=$(date +%s)
  local result_file="${RESULTS_DIR}/${name// /_}.json"
  
  # Record start
  cat > "${result_file}" <<EOF
{
  "name": "${name}",
  "description": "${description}",
  "start_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "status": "running"
}
EOF
  
  # Run chaos injection
  echo "Injecting chaos..."
  eval "${command}" || true
  
  # Wait for system to react
  echo "Waiting for system reaction..."
  sleep 30
  
  # Validate
  echo "Validating system behavior..."
  if eval "${validation}" > "${result_file}.validation" 2>&1; then
    local status="passed"
    echo -e "${GREEN}✅ Experiment passed${NC}"
  else
    local status="failed"
    echo -e "${RED}❌ Experiment failed${NC}"
  fi
  
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  
  # Record results
  cat > "${result_file}" <<EOF
{
  "name": "${name}",
  "description": "${description}",
  "start_time": "$(date -u -d @${start_time} +"%Y-%m-%dT%H:%M:%SZ")",
  "end_time": "$(date -u -d @${end_time} +"%Y-%m-%dT%H:%M:%SZ")",
  "duration_seconds": ${duration},
  "status": "${status}",
  "validation_output": $(cat "${result_file}.validation" | jq -Rs .)
}
EOF
  
  # Cleanup
  echo "Cleaning up..."
  eval "${cleanup}" || true
  
  # Wait between experiments
  sleep 60
}

# Experiment 1: Kill primary service
run_experiment \
  "kill_primary_service" \
  "Kill the active Mai AI service and verify failover" \
  "
    ACTIVE=\$(docker-compose -f ${COMPOSE_FILE} ps --services --filter status=running | grep mai-ai | head -1)
    docker-compose -f ${COMPOSE_FILE} kill \${ACTIVE}
  " \
  "
    sleep 10
    curl -sf ${BASE_URL}/api/health | jq -e '.status == \"healthy\"'
  " \
  "
    docker-compose -f ${COMPOSE_FILE} up -d
  "

# Experiment 2: Network latency
run_experiment \
  "network_latency" \
  "Add 500ms latency to all network traffic" \
  "
    docker-compose -f ${COMPOSE_FILE} exec -T mai-ai-blue tc qdisc add dev eth0 root netem delay 500ms 2>/dev/null || true
    docker-compose -f ${COMPOSE_FILE} exec -T mai-ai-green tc qdisc add dev eth0 root netem delay 500ms 2>/dev/null || true
  " \
  "
    # Should still respond within timeout
    curl --max-time 10 -sf ${BASE_URL}/api/health | jq -e '.status == \"healthy\"'
  " \
  "
    docker-compose -f ${COMPOSE_FILE} exec -T mai-ai-blue tc qdisc del dev eth0 root 2>/dev/null || true
    docker-compose -f ${COMPOSE_FILE} exec -T mai-ai-green tc qdisc del dev eth0 root 2>/dev/null || true
  "

# Experiment 3: CPU pressure
run_experiment \
  "cpu_pressure" \
  "Consume 90% CPU on host" \
  "
    docker run -d --rm --cpus=3.6 --name chaos-cpu progrium/stress --cpu 4 --timeout 120s
  " \
  "
    # System should still respond (maybe slower)
    curl --max-time 30 -sf ${BASE_URL}/api/health | jq -e '.status == \"healthy\"'
  " \
  "
    docker kill chaos-cpu 2>/dev/null || true
  "

# Experiment 4: Memory pressure
run_experiment \
  "memory_pressure" \
  "Consume 80% available memory" \
  "
    docker run -d --rm --memory=3g --name chaos-mem progrium/stress --vm 2 --vm-bytes 1500M --timeout 120s
  " \
  "
    curl --max-time 30 -sf ${BASE_URL}/api/health | jq -e '.status == \"healthy\"'
  " \
  "
    docker kill chaos-mem 2>/dev/null || true
  "

# Experiment 5: Database connection failure
run_experiment \
  "database_failure" \
  "Block database connections" \
  "
    docker-compose -f ${COMPOSE_FILE} exec -T postgres psql -U mai -c 'SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = \"mai\" AND pid <> pg_backend_pid();'
  " \
  "
    # Should handle gracefully (may return degraded status)
    curl --max-time 10 -sf ${BASE_URL}/api/health | jq -e '.'
  " \
  "
    docker-compose -f ${COMPOSE_FILE} restart postgres
    sleep 15
  "

# Experiment 6: Redis connection failure
run_experiment \
  "redis_failure" \
  "Block Redis connections" \
  "
    docker-compose -f ${COMPOSE_FILE} exec -T redis redis-cli CLIENT KILL TYPE normal
  " \
  "
    curl --max-time 10 -sf ${BASE_URL}/api/health | jq -e '.'
  " \
  "
    docker-compose -f ${COMPOSE_FILE} restart redis
    sleep 10
  "

# Experiment 7: Disk full
run_experiment \
  "disk_full" \
  "Fill disk to 95% capacity" \
  "
    docker-compose -f ${COMPOSE_FILE} exec -T mai-ai-blue dd if=/dev/zero of=/tmp/fill bs=1M count=2000 2>/dev/null || true
  " \
  "
    curl --max-time 10 -sf ${BASE_URL}/api/health | jq -e '.status == \"healthy\"'
  " \
  "
    docker-compose -f ${COMPOSE_FILE} exec -T mai-ai-blue rm -f /tmp/fill
  "

# Experiment 8: Clock skew
run_experiment \
  "clock_skew" \
  "Skew system clock by 5 minutes" \
  "
    docker-compose -f ${COMPOSE_FILE} exec -T mai-ai-blue date -s \"@\$((\$(date +%s) + 300))\" 2>/dev/null || true
  " \
  "
    curl --max-time 10 -sf ${BASE_URL}/api/health | jq -e '.'
  " \
  "
    docker-compose -f ${COMPOSE_FILE} exec -T mai-ai-blue hwclock -s 2>/dev/null || true
    docker-compose -f ${COMPOSE_FILE} restart mai-ai-blue
  "

# Experiment 9: Dependency cascade failure
run_experiment \
  "dependency_cascade" \
  "Simultaneous failure of multiple dependencies" \
  "
    docker-compose -f ${COMPOSE_FILE} stop postgres redis
  " \
  "
    # Should return degraded but not crash
    curl --max-time 15 -sf ${BASE_URL}/api/health | jq -e '.'
  " \
  "
    docker-compose -f ${COMPOSE_FILE} start postgres redis
    sleep 20
  "

# Experiment 10: High request load
run_experiment \
  "high_load" \
  "Sustained high request load" \
  "
    for i in {1..100}; do
      curl -sf ${BASE_URL}/api/health >/dev/null &
    done
    wait
  " \
  "
    # Should handle load without errors
    curl --max-time 5 -sf ${BASE_URL}/api/health | jq -e '.status == \"healthy\"'
  " \
  "
    # No cleanup needed
    true
  "

# Generate summary report
echo ""
echo "========================================"
echo "Generating Summary Report"
echo "========================================"

cat > "${RESULTS_DIR}/summary.json" <<EOF
{
  "environment": "${ENVIRONMENT}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "experiments": [
EOF

first=true
for f in "${RESULTS_DIR}"/*.json; do
  if [[ -f "${f}" && "${f}" != "${RESULTS_DIR}/summary.json" ]]; then
    if ${first}; then
      first=false
    else
      echo "," >> "${RESULTS_DIR}/summary.json"
    fi
    cat "${f}" >> "${RESULTS_DIR}/summary.json"
  fi
done

cat >> "${RESULTS_DIR}/summary.json" <<EOF
  ]
}
EOF

# Count results
TOTAL=$(ls "${RESULTS_DIR}"/*.json 2>/dev/null | grep -v summary | wc -l)
PASSED=$(grep -l '"status": "passed"' "${RESULTS_DIR}"/*.json 2>/dev/null | grep -v summary | wc -l)
FAILED=$((TOTAL - PASSED))

echo ""
echo "========================================"
echo "CHAOS ENGINEERING SUMMARY"
echo "========================================"
echo "Total experiments: ${TOTAL}"
echo -e "Passed: ${GREEN}${PASSED}${NC}"
echo -e "Failed: ${RED}${FAILED}${NC}"
echo "Results saved to: ${RESULTS_DIR}"

if [[ ${FAILED} -gt 0 ]]; then
  echo -e "${RED}⚠️  Some experiments failed - review results${NC}"
  exit 1
else
  echo -e "${GREEN}✅ All experiments passed${NC}"
  exit 0
fi