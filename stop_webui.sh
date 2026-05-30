#!/bin/bash
# Stop Live VLM WebUI container

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

CONTAINER_NAME="live-vlm-webui"

echo -e "${YELLOW}Stopping Live VLM WebUI...${NC}"

# Check if container exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    # Check if it's running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker stop ${CONTAINER_NAME}
        echo -e "${GREEN}✓ Container stopped${NC}"
    else
        echo -e "${YELLOW}Container is not running${NC}"
    fi
else
    echo -e "${RED}Container '${CONTAINER_NAME}' does not exist${NC}"
    exit 1
fi
