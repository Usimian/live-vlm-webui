#!/bin/bash
# Start Live VLM WebUI and ROS2 Bridge together
# This script runs both the Docker container and the ROS2 node

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Live VLM WebUI + ROS2 Bridge${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if ROS2 is sourced
if [ -z "$ROS_DISTRO" ]; then
    echo -e "${YELLOW}⚠️  ROS2 environment not sourced${NC}"
    echo -e "${YELLOW}Attempting to source ROS2 Humble...${NC}"

    if [ -f "/opt/ros/humble/setup.bash" ]; then
        source /opt/ros/humble/setup.bash
        echo -e "${GREEN}✓ Sourced /opt/ros/humble/setup.bash${NC}"
    else
        echo -e "${RED}✗ ROS2 Humble not found at /opt/ros/humble${NC}"
        echo -e "${YELLOW}Please install ROS2 Humble or source it manually:${NC}"
        echo -e "  ${GREEN}source /opt/ros/humble/setup.bash${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ ROS2 Distribution: ${ROS_DISTRO}${NC}"

# Check if ros2_bridge directory exists
if [ ! -d "${SCRIPT_DIR}/ros2_bridge" ]; then
    echo -e "${RED}✗ ros2_bridge directory not found at ${SCRIPT_DIR}/ros2_bridge${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found ros2_bridge package${NC}"

# Install Python dependencies
echo -e "${YELLOW}Checking Python dependencies...${NC}"
if ! python3 -c "import websocket" 2>/dev/null; then
    echo -e "${YELLOW}Installing websocket-client...${NC}"
    pip3 install --user websocket-client
fi

if ! python3 -c "import rclpy" 2>/dev/null; then
    echo -e "${YELLOW}Installing rclpy...${NC}"
    pip3 install --user rclpy
fi

echo -e "${GREEN}✓ Python dependencies OK${NC}"

# Add ros2_bridge to PYTHONPATH
export PYTHONPATH="${SCRIPT_DIR}/ros2_bridge:${PYTHONPATH}"

echo ""

# Start WebUI container
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Step 1: Starting WebUI Container${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

CONTAINER_NAME="live-vlm-webui"
IMAGE_NAME="live-vlm-webui:local"

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    # Check if it's running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${GREEN}✓ WebUI container already running${NC}"
    else
        echo -e "${YELLOW}Starting existing container...${NC}"
        docker start ${CONTAINER_NAME}
        sleep 2

        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo -e "${GREEN}✓ Container started${NC}"
        else
            echo -e "${RED}✗ Failed to start container${NC}"
            exit 1
        fi
    fi
else
    # Check if image exists
    if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${IMAGE_NAME}$"; then
        echo -e "${RED}✗ Image '${IMAGE_NAME}' not found${NC}"
        echo -e "${YELLOW}Build the image first with:${NC}"
        echo -e "  ${GREEN}docker build -f docker/Dockerfile -t ${IMAGE_NAME} .${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Starting new container...${NC}"
    docker run -d \
      --name ${CONTAINER_NAME} \
      --network host \
      --privileged \
      --gpus all \
      ${IMAGE_NAME}

    sleep 2

    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${GREEN}✓ Container started${NC}"
    else
        echo -e "${RED}✗ Container failed to start${NC}"
        echo -e "${YELLOW}Check logs: docker logs ${CONTAINER_NAME}${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Step 2: Starting ROS2 Bridge${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Wait a moment for WebUI to be fully ready
echo -e "${YELLOW}Waiting for WebUI to initialize...${NC}"
sleep 3

echo -e "${YELLOW}Launching VLM bridge node...${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  🚀 System Running${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}🌐 WebUI:${NC}         https://localhost:8090"
echo -e "${GREEN}🤖 ROS2 Bridge:${NC}   vlm_commander node"
echo -e "${GREEN}📡 Publishing:${NC}    /cmd_vel (geometry_msgs/Twist)"
echo ""
echo -e "${YELLOW}📋 Monitor commands:${NC}"
echo -e "   ${GREEN}ros2 topic echo /cmd_vel${NC}"
echo -e "   ${GREEN}ros2 topic echo /vlm_bridge/status${NC}"
echo -e "   ${GREEN}docker logs -f ${CONTAINER_NAME}${NC}"
echo ""
echo -e "${YELLOW}💡 In WebUI:${NC}"
echo -e "   1. Select 'Robot Navigation (ROS)' prompt"
echo -e "   2. Point camera at scene"
echo -e "   3. Watch commands publish to /cmd_vel"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop...${NC}"
echo ""

# Run the ROS2 node directly with Python
cd "${SCRIPT_DIR}/ros2_bridge"
python3 -m ros2_bridge.vlm_commander
