"""Command parser for VLM navigation output.

Parses text output from Live VLM WebUI containing robot navigation commands
and extracts velocity commands (linear_x, angular_z) for robot control.
"""

import re
from typing import List, Tuple, Optional
import logging


logger = logging.getLogger(__name__)


class VLMCommandParser:
    """Parser for VLM navigation command output."""

    def __init__(
        self,
        max_linear_vel: float = 0.5,
        max_angular_vel: float = 1.0,
        clamp_velocities: bool = True,
    ):
        """Initialize the command parser.

        Args:
            max_linear_vel: Maximum allowed linear velocity (m/s)
            max_angular_vel: Maximum allowed angular velocity (rad/s)
            clamp_velocities: If True, clamp values to safe ranges. If False, reject invalid commands.
        """
        self.max_linear_vel = max_linear_vel
        self.max_angular_vel = max_angular_vel
        self.clamp_velocities = clamp_velocities

        # Regex patterns for different command formats
        # Format 1: linear_x=0.3, angular_z=0.0 # reason
        self.pattern_simple = re.compile(
            r'linear[_.]x\s*=\s*([-+]?\d*\.?\d+)\s*,\s*angular[_.]z\s*=\s*([-+]?\d*\.?\d+)',
            re.IGNORECASE
        )

        # Format 2: T=0.0s: linear.x=0.20, angular.z=0.00 # reason
        self.pattern_timestamped = re.compile(
            r'T\s*=\s*([-+]?\d*\.?\d+)s?\s*:\s*linear[_.]x\s*=\s*([-+]?\d*\.?\d+)\s*,\s*angular[_.]z\s*=\s*([-+]?\d*\.?\d+)',
            re.IGNORECASE
        )

    def parse(self, text: str) -> List[Tuple[Optional[float], float, float]]:
        """Parse VLM output text to extract navigation commands.

        Args:
            text: VLM output text containing navigation commands

        Returns:
            List of tuples (timestamp, linear_x, angular_z)
            timestamp is None for non-timestamped commands
            Returns empty list if no valid commands found
        """
        commands = []

        # Try timestamped format first
        timestamped_matches = self.pattern_timestamped.findall(text)
        if timestamped_matches:
            for match in timestamped_matches:
                timestamp = float(match[0])
                linear_x = float(match[1])
                angular_z = float(match[2])

                # Validate and optionally clamp
                linear_x, angular_z, valid = self._validate_command(linear_x, angular_z)
                if valid:
                    commands.append((timestamp, linear_x, angular_z))

            if commands:
                logger.info(f"Parsed {len(commands)} timestamped commands")
                return commands

        # Try simple format
        simple_matches = self.pattern_simple.findall(text)
        if simple_matches:
            for match in simple_matches:
                linear_x = float(match[0])
                angular_z = float(match[1])

                # Validate and optionally clamp
                linear_x, angular_z, valid = self._validate_command(linear_x, angular_z)
                if valid:
                    commands.append((None, linear_x, angular_z))

            if commands:
                logger.info(f"Parsed {len(commands)} simple commands")
                return commands

        logger.warning("No valid navigation commands found in VLM output")
        return []

    def _validate_command(
        self, linear_x: float, angular_z: float
    ) -> Tuple[float, float, bool]:
        """Validate and optionally clamp velocity command.

        Args:
            linear_x: Linear velocity (m/s)
            angular_z: Angular velocity (rad/s)

        Returns:
            Tuple of (clamped_linear_x, clamped_angular_z, is_valid)
        """
        original_linear = linear_x
        original_angular = angular_z

        # Check if values are within safe ranges
        linear_valid = abs(linear_x) <= self.max_linear_vel
        angular_valid = abs(angular_z) <= self.max_angular_vel

        if not (linear_valid and angular_valid):
            if self.clamp_velocities:
                # Clamp to safe ranges
                linear_x = max(
                    -self.max_linear_vel, min(self.max_linear_vel, linear_x)
                )
                angular_z = max(
                    -self.max_angular_vel, min(self.max_angular_vel, angular_z)
                )
                logger.warning(
                    f"Clamped velocities: linear_x {original_linear:.3f} → {linear_x:.3f}, "
                    f"angular_z {original_angular:.3f} → {angular_z:.3f}"
                )
                return linear_x, angular_z, True
            else:
                # Reject invalid command
                logger.error(
                    f"Rejected invalid command: linear_x={original_linear:.3f} "
                    f"(max={self.max_linear_vel}), angular_z={original_angular:.3f} "
                    f"(max={self.max_angular_vel})"
                )
                return linear_x, angular_z, False

        return linear_x, angular_z, True

    def parse_single_command(self, text: str) -> Optional[Tuple[float, float]]:
        """Parse VLM output and return the first valid command.

        Useful for "latest" execution mode where we only need one command.

        Args:
            text: VLM output text containing navigation commands

        Returns:
            Tuple of (linear_x, angular_z) or None if no valid command found
        """
        commands = self.parse(text)
        if commands:
            # Return first command (ignore timestamp)
            return (commands[0][1], commands[0][2])
        return None


def main():
    """Test the command parser with sample inputs."""
    parser = VLMCommandParser()

    # Test simple format
    simple_text = """
    Scene: A hallway with doors on both sides.

    Navigation Commands:
    1. linear_x=0.4, angular_z=0.0 # Move forward
    2. linear_x=0.3, angular_z=0.1 # Turn right
    3. linear_x=0.2, angular_z=0.0 # Continue forward
    """
    print("Testing simple format:")
    commands = parser.parse(simple_text)
    for cmd in commands:
        print(f"  Timestamp={cmd[0]}, linear_x={cmd[1]:.2f}, angular_z={cmd[2]:.2f}")

    print()

    # Test timestamped format
    timestamped_text = """
    T=0.0s: linear.x=0.25, angular.z=0.00 # Hallway clear
    T=0.1s: linear.x=0.25, angular.z=0.05 # Slight left turn
    T=0.2s: linear.x=0.20, angular.z=0.10 # Continue turning
    T=0.3s: linear.x=0.15, angular.z=0.00 # Reduce speed
    """
    print("Testing timestamped format:")
    commands = parser.parse(timestamped_text)
    for cmd in commands:
        print(f"  Timestamp={cmd[0]:.1f}s, linear_x={cmd[1]:.2f}, angular_z={cmd[2]:.2f}")

    print()

    # Test single command extraction
    print("Testing single command extraction:")
    cmd = parser.parse_single_command(simple_text)
    if cmd:
        print(f"  First command: linear_x={cmd[0]:.2f}, angular_z={cmd[1]:.2f}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
