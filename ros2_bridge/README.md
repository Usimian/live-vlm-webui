# ROS2 Bridge for Live VLM WebUI

A ROS2 package that bridges the [Live VLM WebUI](https://github.com/Usimian/live-vlm-webui) to robot control by receiving vision-based navigation commands from a Vision Language Model and publishing them as `geometry_msgs/Twist` messages.

## Overview

This bridge connects your robot to AI-powered vision analysis:
1. **Live VLM WebUI** analyzes camera feed and generates navigation commands
2. **ROS2 Bridge** parses commands and publishes to `/cmd_vel`
3. **Your Robot** executes the movement commands

## Features

- ✅ WebSocket connection to Live VLM WebUI
- ✅ Automatic reconnection on disconnect
- ✅ Command parsing for multiple VLM output formats
- ✅ Safety velocity limits with clamping
- ✅ Gradual deceleration when commands stop
- ✅ Emergency stop service
- ✅ Enable/disable service
- ✅ Status monitoring topics
- ✅ Configurable update rate
- ✅ Support for both ws:// and wss:// connections

## Requirements

- **ROS2**: Humble (LTS) on Ubuntu 22.04
- **Python**: 3.10+
- **Dependencies**:
  - `rclpy`
  - `geometry_msgs`
  - `std_msgs`
  - `std_srvs`
  - `websocket-client`

## Installation

### 1. Clone the Repository

```bash
cd ~/ros2_ws/src
git clone https://github.com/Usimian/live-vlm-webui.git
```

### 2. Install Python Dependencies

```bash
pip install websocket-client
```

### 3. Build the ROS2 Package

```bash
cd ~/ros2_ws
colcon build --packages-select ros2_bridge
source install/setup.bash
```

## Usage

### Quick Start

1. **Start the Live VLM WebUI** (in Docker or natively):
   ```bash
   docker run -d --name live-vlm-webui \
     --network host --privileged --gpus all \
     live-vlm-webui:local
   ```

2. **Launch the ROS2 Bridge**:
   ```bash
   ros2 launch ros2_bridge vlm_bridge.launch.py
   ```

3. **Open the WebUI** and select a robot navigation prompt:
   - Go to `https://localhost:8090`
   - Select "Robot Navigation (Simple)" or "Robot Navigation (ROS)"
   - Point camera at the scene

4. **Monitor the commands**:
   ```bash
   # View cmd_vel commands
   ros2 topic echo /cmd_vel

   # View bridge status
   ros2 topic echo /vlm_bridge/status
   ```

### Launch Parameters

Customize the bridge behavior with launch arguments:

```bash
ros2 launch ros2_bridge vlm_bridge.launch.py \
  websocket_url:=wss://localhost:8090/ws \
  cmd_vel_topic:=/cmd_vel \
  update_rate:=10.0 \
  max_linear_vel:=0.5 \
  max_angular_vel:=1.0
```

### Configuration File

Edit `config/vlm_bridge.yaml` to set default parameters:

```yaml
/**:
  ros__parameters:
    websocket_url: "wss://localhost:8090/ws"
    cmd_vel_topic: "/cmd_vel"
    update_rate: 10.0
    max_linear_vel: 0.5
    max_angular_vel: 1.0
    command_timeout: 2.0
    deceleration_time: 1.0
    execution_mode: "latest"
```

## ROS2 Interfaces

### Published Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/cmd_vel` | `geometry_msgs/Twist` | Velocity commands for robot |
| `/vlm_bridge/status` | `std_msgs/String` | Connection and operation status |
| `/vlm_bridge/last_command` | `geometry_msgs/Twist` | Echo of last published command |

### Services

| Service | Type | Description |
|---------|------|-------------|
| `/vlm_bridge/emergency_stop` | `std_srvs/Trigger` | Emergency stop (stops robot immediately) |
| `/vlm_bridge/enable` | `std_srvs/SetBool` | Enable/disable command execution |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `websocket_url` | string | `wss://localhost:8090/ws` | WebSocket URL for VLM WebUI |
| `cmd_vel_topic` | string | `/cmd_vel` | Topic to publish velocity commands |
| `update_rate` | double | `10.0` | Command update rate (Hz) |
| `enable_safety_limits` | bool | `true` | Enforce velocity limits |
| `max_linear_vel` | double | `0.5` | Maximum linear velocity (m/s) |
| `max_angular_vel` | double | `1.0` | Maximum angular velocity (rad/s) |
| `command_timeout` | double | `2.0` | Time before deceleration starts (s) |
| `deceleration_time` | double | `1.0` | Time to decelerate to stop (s) |
| `execution_mode` | string | `latest` | Command execution mode (`latest` or `sequence`) |

## Safety Features

### Velocity Limits
- Linear velocity clamped to `[-max_linear_vel, +max_linear_vel]`
- Angular velocity clamped to `[-max_angular_vel, +max_angular_vel]`
- Out-of-range commands are logged and clamped

### Command Timeout
- Robot decelerates if no new commands within `command_timeout` seconds
- Gradual deceleration over `deceleration_time` (smooth stop)
- Prevents runaway if VLM connection drops

### Emergency Stop
- Service call immediately stops the robot
- Cannot be re-enabled (requires node restart)
- Use for safety-critical situations

```bash
ros2 service call /vlm_bridge/emergency_stop std_srvs/srv/Trigger
```

### Enable/Disable
- Temporarily disable command execution
- Publishes zero velocity when disabled
- Can be re-enabled

```bash
# Disable
ros2 service call /vlm_bridge/enable std_srvs/srv/SetBool "{data: false}"

# Enable
ros2 service call /vlm_bridge/enable std_srvs/srv/SetBool "{data: true}"
```

## Command Formats

The bridge parses two formats from VLM output:

### Format 1: Simple Navigation
```
linear_x=0.3, angular_z=0.0 # Move forward
linear_x=0.2, angular_z=0.1 # Turn right
```

### Format 2: Timestamped (Advanced)
```
T=0.0s: linear.x=0.25, angular.z=0.00 # Hallway clear
T=0.1s: linear.x=0.25, angular.z=0.05 # Slight left turn
T=0.2s: linear.x=0.20, angular.z=0.10 # Continue turning
```

## Execution Modes

### Latest Mode (Default)
- Executes the **first valid command** from each VLM response
- Best for **reactive navigation** and obstacle avoidance
- VLM continuously analyzes scene and updates commands

### Sequence Mode (Future)
- Executes all **timestamped commands** in order
- Best for **planned trajectory** following
- Not yet implemented

## Troubleshooting

### Bridge Can't Connect to WebUI

**Problem**: `WebSocket closed` or connection errors

**Solutions**:
1. Check WebUI is running: `docker ps | grep live-vlm-webui`
2. Verify URL matches WebUI address
3. For SSL issues, try `ws://` instead of `wss://`
4. Check firewall/network settings

### No Commands Being Published

**Problem**: Bridge connected but no `/cmd_vel` messages

**Solutions**:
1. Check VLM is generating output: Monitor WebUI interface
2. Verify robot navigation prompt is selected
3. Check bridge logs: `ros2 topic echo /vlm_bridge/status`
4. Ensure camera feed is active

### Robot Moving Erratically

**Problem**: Unexpected or jerky movements

**Solutions**:
1. Reduce `update_rate` (try 5 Hz instead of 10 Hz)
2. Increase `command_timeout` for smoother transitions
3. Adjust `max_linear_vel` and `max_angular_vel` for your robot
4. Check VLM is generating consistent commands

### SSL Certificate Errors

**Problem**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solutions**:
1. The bridge disables SSL verification for self-signed certificates
2. Use `ws://` instead of `wss://` for testing
3. Install proper SSL certificates on WebUI server

## Testing

### Test Command Parser
```bash
cd ~/ros2_ws/src/live-vlm-webui/ros2_bridge
python3 -m ros2_bridge.command_parser
```

### Test WebSocket Client
```bash
python3 -m ros2_bridge.websocket_client
```

### Monitor Topics
```bash
# Terminal 1: Monitor cmd_vel
ros2 topic echo /cmd_vel

# Terminal 2: Monitor status
ros2 topic echo /vlm_bridge/status

# Terminal 3: Monitor last command
ros2 topic echo /vlm_bridge/last_command
```

### Test with Robot Simulator

Use with TurtleBot3 in Gazebo:

```bash
# Terminal 1: Launch Gazebo simulation
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py

# Terminal 2: Launch VLM Bridge
ros2 launch ros2_bridge vlm_bridge.launch.py

# Terminal 3: Monitor /cmd_vel
ros2 topic echo /cmd_vel
```

## Architecture

```
┌─────────────────────┐
│  Live VLM WebUI     │
│  (Vision Analysis)  │
└──────────┬──────────┘
           │ WebSocket (wss://localhost:8090/ws)
           │ {"type": "vlm_response", "text": "linear_x=0.2..."}
           ↓
┌─────────────────────┐
│  VLM WebSocket      │
│  Client             │
└──────────┬──────────┘
           │ Callback
           ↓
┌─────────────────────┐
│  Command Parser     │
│  (Regex extraction) │
└──────────┬──────────┘
           │ (linear_x, angular_z)
           ↓
┌─────────────────────┐
│  VLM Commander Node │
│  (ROS2)             │
└──────────┬──────────┘
           │ geometry_msgs/Twist
           ↓
┌─────────────────────┐
│  Robot / Simulator  │
│  (/cmd_vel topic)   │
└─────────────────────┘
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

Apache 2.0 - See [LICENSE](../LICENSE) file

## Acknowledgments

- Built for [Live VLM WebUI](https://github.com/nvidia-ai-iot/live-vlm-webui) by NVIDIA AI-IOT
- Designed for ROS2 Humble (LTS)
- Tested on Ubuntu 22.04 with custom robot hardware

## Support

For issues and questions:
- **Bridge Issues**: [GitHub Issues](https://github.com/Usimian/live-vlm-webui/issues)
- **VLM WebUI**: [Original Repository](https://github.com/nvidia-ai-iot/live-vlm-webui)
- **ROS2 Help**: [ROS Discourse](https://discourse.ros.org/)
