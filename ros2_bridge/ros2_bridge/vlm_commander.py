"""VLM Commander Node for ROS2.

Main ROS2 node that connects to Live VLM WebUI, receives navigation commands,
and publishes geometry_msgs/Twist messages to control the robot.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from std_srvs.srv import Trigger, SetBool
import time
import logging
from typing import Optional, Dict, Any

from .command_parser import VLMCommandParser
from .websocket_client import VLMWebSocketClient


class VLMCommanderNode(Node):
    """ROS2 node for VLM-based robot control."""

    def __init__(self):
        """Initialize the VLM Commander node."""
        super().__init__('vlm_commander')

        # Declare parameters
        self.declare_parameter('websocket_url', 'wss://localhost:8090/ws')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('update_rate', 10.0)
        self.declare_parameter('enable_safety_limits', True)
        self.declare_parameter('max_linear_vel', 0.5)
        self.declare_parameter('max_angular_vel', 1.0)
        self.declare_parameter('command_timeout', 2.0)
        self.declare_parameter('execution_mode', 'latest')
        self.declare_parameter('deceleration_time', 1.0)

        # Get parameters
        self.websocket_url = self.get_parameter('websocket_url').value
        self.cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.update_rate = self.get_parameter('update_rate').value
        self.enable_safety_limits = self.get_parameter('enable_safety_limits').value
        self.max_linear_vel = self.get_parameter('max_linear_vel').value
        self.max_angular_vel = self.get_parameter('max_angular_vel').value
        self.command_timeout = self.get_parameter('command_timeout').value
        self.execution_mode = self.get_parameter('execution_mode').value
        self.deceleration_time = self.get_parameter('deceleration_time').value

        # Log configuration
        self.get_logger().info(f"WebSocket URL: {self.websocket_url}")
        self.get_logger().info(f"Command topic: {self.cmd_vel_topic}")
        self.get_logger().info(f"Update rate: {self.update_rate} Hz")
        self.get_logger().info(f"Max velocities: linear={self.max_linear_vel}, angular={self.max_angular_vel}")
        self.get_logger().info(f"Execution mode: {self.execution_mode}")
        self.get_logger().info(f"Deceleration time: {self.deceleration_time}s")

        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        self.status_pub = self.create_publisher(String, '/vlm_bridge/status', 10)
        self.last_cmd_pub = self.create_publisher(Twist, '/vlm_bridge/last_command', 10)

        # Services
        self.emergency_stop_srv = self.create_service(
            Trigger, '/vlm_bridge/emergency_stop', self.emergency_stop_callback
        )
        self.enable_srv = self.create_service(
            SetBool, '/vlm_bridge/enable', self.enable_callback
        )

        # Command parser
        self.parser = VLMCommandParser(
            max_linear_vel=self.max_linear_vel,
            max_angular_vel=self.max_angular_vel,
            clamp_velocities=self.enable_safety_limits,
        )

        # WebSocket client
        self.ws_client = VLMWebSocketClient(
            url=self.websocket_url,
            on_vlm_response=self.on_vlm_response,
        )

        # State variables
        self.enabled = True
        self.emergency_stopped = False
        self.last_command: Optional[Twist] = None
        self.last_command_time = 0.0
        self.current_target_linear = 0.0
        self.current_target_angular = 0.0
        self.current_linear = 0.0
        self.current_angular = 0.0

        # Timer for command execution
        timer_period = 1.0 / self.update_rate
        self.timer = self.create_timer(timer_period, self.timer_callback)

        # Start WebSocket client
        self.ws_client.start()
        self.publish_status("Connecting to VLM WebUI...")

        self.get_logger().info("VLM Commander node initialized")

    def on_vlm_response(self, text: str, metrics: Dict[str, Any]):
        """Callback for VLM responses from WebSocket.

        Args:
            text: VLM response text containing navigation commands
            metrics: Performance metrics from VLM inference
        """
        if not self.enabled or self.emergency_stopped:
            return

        # Parse command
        if self.execution_mode == 'latest':
            # Extract first command
            result = self.parser.parse_single_command(text)
            if result:
                linear_x, angular_z = result
                self.current_target_linear = linear_x
                self.current_target_angular = angular_z
                self.last_command_time = time.time()

                self.get_logger().debug(
                    f"New command: linear_x={linear_x:.3f}, angular_z={angular_z:.3f}"
                )
        else:
            # Sequence mode not implemented yet
            self.get_logger().warning("Sequence mode not yet implemented")

    def timer_callback(self):
        """Timer callback for publishing cmd_vel at fixed rate."""
        if self.emergency_stopped:
            # Publish zero velocity
            self.publish_velocity(0.0, 0.0)
            return

        if not self.enabled:
            # Publish zero velocity when disabled
            self.publish_velocity(0.0, 0.0)
            return

        # Check command timeout
        time_since_command = time.time() - self.last_command_time
        if time_since_command > self.command_timeout and self.last_command_time > 0.0:
            # Gradual deceleration
            self.apply_deceleration(time_since_command - self.command_timeout)
        else:
            # Normal operation - use target velocities
            self.current_linear = self.current_target_linear
            self.current_angular = self.current_target_angular

        # Publish velocity
        self.publish_velocity(self.current_linear, self.current_angular)

        # Update status
        if self.ws_client.is_connected():
            response_age = self.ws_client.get_last_response_age()
            if response_age != float('inf'):
                self.publish_status(f"Connected - Last response: {response_age:.1f}s ago")
            else:
                self.publish_status("Connected - Waiting for VLM response")
        else:
            self.publish_status("Disconnected - Reconnecting...")

    def apply_deceleration(self, overtime: float):
        """Apply gradual deceleration when commands stop.

        Args:
            overtime: Time beyond command_timeout
        """
        if overtime >= self.deceleration_time:
            # Fully stopped
            self.current_linear = 0.0
            self.current_angular = 0.0
        else:
            # Linear deceleration
            factor = 1.0 - (overtime / self.deceleration_time)
            self.current_linear = self.current_target_linear * factor
            self.current_angular = self.current_target_angular * factor

    def publish_velocity(self, linear_x: float, angular_z: float):
        """Publish Twist message to cmd_vel topic.

        Args:
            linear_x: Linear velocity (m/s)
            angular_z: Angular velocity (rad/s)
        """
        msg = Twist()
        msg.linear.x = linear_x
        msg.angular.z = angular_z

        self.cmd_vel_pub.publish(msg)
        self.last_command = msg

        # Also publish to last_command topic
        self.last_cmd_pub.publish(msg)

    def publish_status(self, status: str):
        """Publish status message.

        Args:
            status: Status text
        """
        msg = String()
        msg.data = status
        self.status_pub.publish(msg)

    def emergency_stop_callback(self, request, response):
        """Emergency stop service callback."""
        self.emergency_stopped = True
        self.current_target_linear = 0.0
        self.current_target_angular = 0.0
        self.current_linear = 0.0
        self.current_angular = 0.0

        self.get_logger().warn("EMERGENCY STOP ACTIVATED!")
        self.publish_status("EMERGENCY STOP")

        response.success = True
        response.message = "Emergency stop activated"
        return response

    def enable_callback(self, request, response):
        """Enable/disable service callback."""
        if request.data:
            # Enable
            if self.emergency_stopped:
                response.success = False
                response.message = "Cannot enable while emergency stopped. Restart node to reset."
            else:
                self.enabled = True
                response.success = True
                response.message = "VLM Commander enabled"
                self.get_logger().info("Enabled")
                self.publish_status("Enabled")
        else:
            # Disable
            self.enabled = False
            self.current_target_linear = 0.0
            self.current_target_angular = 0.0
            response.success = True
            response.message = "VLM Commander disabled"
            self.get_logger().info("Disabled")
            self.publish_status("Disabled")

        return response

    def destroy_node(self):
        """Clean up before node destruction."""
        self.get_logger().info("Shutting down VLM Commander...")
        self.ws_client.stop()
        super().destroy_node()


def main(args=None):
    """Main entry point for VLM Commander node."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Initialize ROS2
    rclpy.init(args=args)

    # Create node
    node = VLMCommanderNode()

    try:
        # Spin
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
