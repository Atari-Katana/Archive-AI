#!/bin/bash
#
# Helper script for running stress tests with different profiles
#
# Usage:
#   bash scripts/run-stress-test.sh [quick|normal|extended]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TEST_SCRIPT="$ROOT_DIR/tests/stress/concurrent_test.py"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default profile
PROFILE="${1:-normal}"

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}Archive-AI Stress Test Runner${NC}"
echo -e "${BLUE}=================================================${NC}"
echo

# Configure test based on profile
case "$PROFILE" in
    quick)
        echo -e "${YELLOW}Profile: Quick Test (30s, 5 concurrent)${NC}"
        DURATION=30
        CONCURRENCY=5
        ;;
    normal)
        echo -e "${YELLOW}Profile: Normal Test (5min, 10 concurrent)${NC}"
        DURATION=300
        CONCURRENCY=10
        ;;
    extended)
        echo -e "${YELLOW}Profile: Extended Test (15min, 20 concurrent)${NC}"
        DURATION=900
        CONCURRENCY=20
        ;;
    *)
        echo -e "${YELLOW}Unknown profile: $PROFILE${NC}"
        echo "Valid profiles: quick, normal, extended"
        echo
        echo "Examples:"
        echo "  bash scripts/run-stress-test.sh quick"
        echo "  bash scripts/run-stress-test.sh normal"
        echo "  bash scripts/run-stress-test.sh extended"
        exit 1
        ;;
esac

# Check if services are running
echo
echo "🔍 Checking if Archive-AI services are running..."

if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${YELLOW}✗ Archive-AI not running at http://localhost:8080${NC}"
    echo
    echo "Start services first:"
    echo "  bash go.sh"
    echo
    exit 1
fi

echo -e "${GREEN}✓ Services are running${NC}"
echo

# Run test
echo "🚀 Starting stress test..."
echo

python3 "$TEST_SCRIPT" \
    --url "http://localhost:8080" \
    --concurrency "$CONCURRENCY" \
    --duration "$DURATION" \
    --timeout 30.0

echo
echo -e "${BLUE}=================================================${NC}"
echo -e "${GREEN}Stress test complete!${NC}"
echo -e "${BLUE}=================================================${NC}"
