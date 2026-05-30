"""Launch file for VLM Bridge ROS2 node.

This launch file starts the VLM Commander node with configurable parameters.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """Generate launch description for VLM Bridge."""
    # Declare launch arguments
    websocket_url_arg = DeclareLaunchArgument(
        'websocket_url',
        default_value='wss://localhost:8090/ws',
        description='WebSocket URL for Live VLM WebUI'
    )

    cmd_vel_topic_arg = DeclareLaunchArgument(
        'cmd_vel_topic',
        default_value='/cmd_vel',
        description='Topic to publish velocity commands'
    )

    update_rate_arg = DeclareLaunchArgument(
        'update_rate',
        default_value='10.0',
        description='Command update rate in Hz'
    )

    max_linear_vel_arg = DeclareLaunchArgument(
        'max_linear_vel',
        default_value='0.5',
        description='Maximum linear velocity (m/s)'
    )

    max_angular_vel_arg = DeclareLaunchArgument(
        'max_angular_vel',
        default_value='1.0',
        description='Maximum angular velocity (rad/s)'
    )

    use_config_arg = DeclareLaunchArgument(
        'use_config',
        default_value='false',
        description='Load parameters from config file'
    )

    # Get config file path
    config_file = PathJoinSubstitution([
        FindPackageShare('ros2_bridge'),
        'config',
        'vlm_bridge.yaml'
    ])

    # VLM Commander node
    vlm_commander_node = Node(
        package='ros2_bridge',
        executable='vlm_commander',
        name='vlm_commander',
        output='screen',
        parameters=[
            {
                'websocket_url': LaunchConfiguration('websocket_url'),
                'cmd_vel_topic': LaunchConfiguration('cmd_vel_topic'),
                'update_rate': LaunchConfiguration('update_rate'),
                'max_linear_vel': LaunchConfiguration('max_linear_vel'),
                'max_angular_vel': LaunchConfiguration('max_angular_vel'),
            }
        ],
        # Optionally load from config file
        # parameters=[config_file],  # Uncomment to use config file
    )

    return LaunchDescription([
        websocket_url_arg,
        cmd_vel_topic_arg,
        update_rate_arg,
        max_linear_vel_arg,
        max_angular_vel_arg,
        use_config_arg,
        vlm_commander_node,
    ])
