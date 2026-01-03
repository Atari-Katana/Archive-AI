#!/bin/bash
#
# Helper script for running edge case tests
#
# Usage:
#   bash scripts/run-edge-case-tests.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TEST_SCRIPT="$ROOT_DIR/tests/edge_cases/edge_case_suite.py"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}Archive-AI Edge Case Test Suite${NC}"
echo -e "${BLUE}=================================================${NC}"
echo

# Check if services are running
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

# Run tests
echo "🚀 Starting edge case tests..."
echo

python3 "$TEST_SCRIPT" --url "http://localhost:8080" --timeout 10.0

echo
echo -e "${BLUE}=================================================${NC}"
echo -e "${GREEN}Edge case tests complete!${NC}"
echo -e "${BLUE}=================================================${NC}"
