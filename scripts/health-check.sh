#!/bin/bash
#
# Archive-AI Health Check Script
# Comprehensive health monitoring for all services
#
# Usage:
#   bash scripts/health-check.sh           # Full health check
#   bash scripts/health-check.sh --quick   # Quick check only
#   bash scripts/health-check.sh --watch   # Continuous monitoring
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
QUICK_MODE=false
WATCH_MODE=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --watch)
            WATCH_MODE=true
            shift
            ;;
        *)
            ;;
    esac
done

# Helper functions
print_header() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

check_http_endpoint() {
    local name=$1
    local url=$2
    local timeout=${3:-5}

    if curl -sf --max-time "$timeout" "$url" > /dev/null 2>&1; then
        print_success "$name is healthy"
        return 0
    else
        print_error "$name is not responding"
        return 1
    fi
}

check_http_json() {
    local name=$1
    local url=$2
    local timeout=${3:-5}

    response=$(curl -sf --max-time "$timeout" "$url" 2>&1)
    if [ $? -eq 0 ]; then
        print_success "$name is healthy"
        echo "$response" | python3 -m json.tool 2>/dev/null | head -5 | sed 's/^/    /'
        return 0
    else
        print_error "$name is not responding"
        return 1
    fi
}

check_docker_service() {
    local service=$1

    if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
        # Get container stats
        stats=$(docker stats --no-stream --format "{{.CPUPerc}} CPU, {{.MemUsage}}" "$service" 2>/dev/null)
        print_success "$service container running ($stats)"
        return 0
    else
        print_error "$service container not running"
        return 1
    fi
}

run_health_check() {
    local FAILURES=0

    # Banner
    print_header "Archive-AI v7.5 Health Check"
    date

    # Step 1: Docker Container Status
    print_header "1. Docker Container Status"

    check_docker_service "redis" || FAILURES=$((FAILURES + 1))
    check_docker_service "vorpal" || FAILURES=$((FAILURES + 1))
    check_docker_service "brain" || FAILURES=$((FAILURES + 1))
    check_docker_service "sandbox" || FAILURES=$((FAILURES + 1))
    check_docker_service "voice" || FAILURES=$((FAILURES + 1))
    check_docker_service "librarian" || FAILURES=$((FAILURES + 1))

    # Step 2: Health Endpoints
    print_header "2. Service Health Endpoints"

    check_http_endpoint "Brain" "http://localhost:8080/health" || FAILURES=$((FAILURES + 1))
    check_http_endpoint "Vorpal" "http://localhost:8000/health" || FAILURES=$((FAILURES + 1))
    check_http_endpoint "Sandbox" "http://localhost:8003/health" || FAILURES=$((FAILURES + 1))
    check_http_endpoint "Voice" "http://localhost:8001/health" || FAILURES=$((FAILURES + 1))

    # Redis check
    if docker exec $(docker ps -qf "name=redis") redis-cli ping 2>/dev/null | grep -q "PONG"; then
        print_success "Redis is responding to PING"
    else
        print_error "Redis is not responding to PING"
        FAILURES=$((FAILURES + 1))
    fi

    if [ "$QUICK_MODE" = true ]; then
        print_header "Health Check Summary (Quick Mode)"
        if [ $FAILURES -eq 0 ]; then
            print_success "All services healthy!"
            return 0
        else
            print_error "$FAILURES service(s) failed health check"
            return 1
        fi
    fi

    # Step 3: API Endpoints
    print_header "3. Brain API Endpoints"

    check_http_json "Brain Metrics" "http://localhost:8080/metrics" || FAILURES=$((FAILURES + 1))

    # Step 4: Resource Usage
    print_header "4. Resource Usage"

    # Docker stats
    echo -e "${CYAN}Container Resources:${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" | head -7

    # GPU usage
    if command -v nvidia-smi &> /dev/null; then
        echo -e "\n${CYAN}GPU Usage:${NC}"
        nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader | \
            awk -F', ' '{printf "  %s: %s / %s (%s utilization)\n", $1, $2, $3, $4}'
    else
        print_warning "nvidia-smi not available - skipping GPU check"
    fi

    # Redis memory
    echo -e "\n${CYAN}Redis Memory:${NC}"
    docker exec $(docker ps -qf "name=redis") redis-cli INFO memory 2>/dev/null | \
        grep -E "used_memory_human|maxmemory_human" | \
        sed 's/^/  /'

    # Step 5: Disk Usage
    print_header "5. Disk Usage"

    echo -e "${CYAN}Data Directories:${NC}"
    du -sh data/* 2>/dev/null | sed 's/^/  /' || print_warning "No data directories found"

    # Step 6: Service Logs (errors only)
    print_header "6. Recent Errors in Logs"

    echo -e "${CYAN}Checking for errors in last 50 lines...${NC}"
    ERROR_COUNT=0

    for service in redis vorpal brain sandbox voice librarian; do
        container=$(docker ps -qf "name=$service" 2>/dev/null)
        if [ -n "$container" ]; then
            errors=$(docker logs --tail 50 "$container" 2>&1 | grep -i "error\|exception\|failed" | wc -l)
            if [ "$errors" -gt 0 ]; then
                print_warning "$service has $errors error/warning lines in recent logs"
                ERROR_COUNT=$((ERROR_COUNT + errors))
            fi
        fi
    done

    if [ $ERROR_COUNT -eq 0 ]; then
        print_success "No errors found in recent logs"
    else
        print_warning "Found $ERROR_COUNT error/warning lines across all services"
    fi

    # Step 7: Memory Statistics
    print_header "7. Memory System Status"

    # Get memory count via API
    MEMORY_COUNT=$(curl -sf http://localhost:8080/metrics 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin)['memory_stats']['total_memories'])" 2>/dev/null || echo "unknown")

    if [ "$MEMORY_COUNT" != "unknown" ]; then
        print_success "Total memories stored: $MEMORY_COUNT"
    else
        print_warning "Could not retrieve memory count"
    fi

    # Archive stats (if endpoint exists)
    ARCHIVE_STATS=$(curl -sf http://localhost:8080/admin/archive_stats 2>/dev/null)
    if [ $? -eq 0 ]; then
        ARCHIVE_COUNT=$(echo "$ARCHIVE_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_archived_memories', 0))" 2>/dev/null || echo "0")
        print_info "Archived memories: $ARCHIVE_COUNT"
    fi

    # Step 8: Network Connectivity
    print_header "8. Network Connectivity"

    # Check if services can reach each other
    if docker exec $(docker ps -qf "name=brain") curl -sf http://vorpal:8000/health > /dev/null 2>&1; then
        print_success "Brain can reach Vorpal"
    else
        print_error "Brain cannot reach Vorpal"
        FAILURES=$((FAILURES + 1))
    fi

    if docker exec $(docker ps -qf "name=brain") curl -sf http://sandbox:8000/health > /dev/null 2>&1; then
        print_success "Brain can reach Sandbox"
    else
        print_error "Brain cannot reach Sandbox"
        FAILURES=$((FAILURES + 1))
    fi

    # Step 9: Uptime
    print_header "9. Service Uptime"

    UPTIME=$(curl -sf http://localhost:8080/metrics 2>/dev/null | python3 -c "import sys, json; uptime=json.load(sys.stdin)['uptime_seconds']; hours=int(uptime//3600); mins=int((uptime%3600)//60); print(f'{hours}h {mins}m')" 2>/dev/null || echo "unknown")

    if [ "$UPTIME" != "unknown" ]; then
        print_success "Brain uptime: $UPTIME"
    else
        print_warning "Could not retrieve uptime"
    fi

    # Final Summary
    print_header "Health Check Summary"

    if [ $FAILURES -eq 0 ]; then
        print_success "All checks passed! System is healthy."
        echo ""
        echo "Summary:"
        echo "  ✓ All services running"
        echo "  ✓ All health endpoints responding"
        echo "  ✓ API accessible"
        echo "  ✓ Inter-service communication working"
        echo "  ✓ No critical errors in logs"
        echo ""
        print_success "Archive-AI is operating normally"
        return 0
    else
        print_error "$FAILURES check(s) failed"
        echo ""
        echo "Recommended actions:"
        echo "  1. Check service logs: docker-compose logs -f"
        echo "  2. Restart failed services: docker-compose restart <service>"
        echo "  3. Check DEPLOYMENT.md troubleshooting section"
        echo ""
        return 1
    fi
}

# Watch mode
if [ "$WATCH_MODE" = true ]; then
    print_info "Starting continuous monitoring (Ctrl+C to stop)"
    echo ""
    while true; do
        clear
        run_health_check
        sleep 10
    done
else
    run_health_check
    exit $?
fi
