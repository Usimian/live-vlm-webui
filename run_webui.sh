#!/bin/bash
# Start Live VLM WebUI in Docker
# This script runs the locally built container with GPU support

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

CONTAINER_NAME="live-vlm-webui"
IMAGE_NAME="live-vlm-webui:local"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Live VLM WebUI Startup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}Container '${CONTAINER_NAME}' already exists${NC}"

    # Check if it's running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${GREEN}✓ Container is already running${NC}"
        echo ""
        echo -e "${GREEN}Access the WebUI at: https://localhost:8090${NC}"
        exit 0
    else
        echo -e "${YELLOW}Starting existing container...${NC}"
        docker start ${CONTAINER_NAME}
        sleep 2

        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo -e "${GREEN}✓ Container started successfully${NC}"
            echo ""
            echo -e "${GREEN}========================================${NC}"
            echo -e "${GREEN}Access the WebUI at: https://localhost:8090${NC}"
            echo -e "${GREEN}========================================${NC}"
            echo ""
            echo -e "${YELLOW}Useful commands:${NC}"
            echo -e "  View logs:   ${GREEN}docker logs -f ${CONTAINER_NAME}${NC}"
            echo -e "  Stop:        ${GREEN}docker stop ${CONTAINER_NAME}${NC}"
            echo -e "  Restart:     ${GREEN}docker restart ${CONTAINER_NAME}${NC}"
            exit 0
        else
            echo -e "${RED}✗ Failed to start container${NC}"
            exit 1
        fi
    fi
fi

# Check if image exists
if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${IMAGE_NAME}$"; then
    echo -e "${RED}✗ Image '${IMAGE_NAME}' not found${NC}"
    echo -e "${YELLOW}Build the image first with:${NC}"
    echo -e "  ${GREEN}docker build -f docker/Dockerfile -t ${IMAGE_NAME} .${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found image: ${IMAGE_NAME}${NC}"
echo ""

# Start new container
echo -e "${YELLOW}Starting new container...${NC}"
docker run -d \
  --name ${CONTAINER_NAME} \
  --network host \
  --privileged \
  --gpus all \
  ${IMAGE_NAME}

# Wait for container to start
sleep 2

# Check if container is running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${GREEN}✓ Container started successfully${NC}"
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Live VLM WebUI is Running${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${GREEN}🌐 Access the WebUI at:${NC}"
    echo -e "   ${GREEN}https://localhost:8090${NC}"
    echo ""
    echo -e "${YELLOW}📋 Useful commands:${NC}"
    echo -e "   View logs:        ${GREEN}docker logs -f ${CONTAINER_NAME}${NC}"
    echo -e "   Stop container:   ${GREEN}docker stop ${CONTAINER_NAME}${NC}"
    echo -e "   Restart:          ${GREEN}docker restart ${CONTAINER_NAME}${NC}"
    echo -e "   Remove:           ${GREEN}docker stop ${CONTAINER_NAME} && docker rm ${CONTAINER_NAME}${NC}"
    echo ""
    echo -e "${YELLOW}💡 Tips:${NC}"
    echo -e "   - Accept the SSL certificate warning in your browser"
    echo -e "   - Select 'Robot Navigation (ROS)' prompt for robot control"
    echo -e "   - Use ROS2 bridge to connect to your robot"
    echo ""
else
    echo -e "${RED}✗ Container failed to start${NC}"
    echo -e "${YELLOW}Check logs with: docker logs ${CONTAINER_NAME}${NC}"
    exit 1
fi
