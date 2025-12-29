#!/bin/bash
set -e

EXTRA_COMPOSE_FILE="docker-compose.awq-7b.yml" ./scripts/start.sh
cd ~/Archive-AI/ui && python3 -m http.server 8888
