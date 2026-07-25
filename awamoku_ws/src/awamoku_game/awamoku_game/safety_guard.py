from __future__ import annotations

from math import cos, hypot, isfinite, radians, sin

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

from awamoku_game.ros_utils import clamp, yaw_from_quaternion


class SafetyGuard(Node):
    def __init__(self) -> None:
        super().__init__("safety_guard")
        self._declare_parameters()
        self.game_state = "IDLE"
        self.estop_latched = False
        self.latest_desired = Twist()
        self.last_desired_time = None
        self.front_blocked = False
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0

        self.create_subscription(Twist, "/awamoku/motion/desired_twist", self._on_desired, 10)
        self.create_subscription(String, "/awamoku/game/state", self._on_game_state, 10)
        self.create_subscription(String, "/awamoku/game/command", self._on_command, 10)
        self.create_subscription(LaserScan, "/scan", self._on_scan, 10)
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)
        self.pub = self.create_publisher(Twist, "/cmd_vel", 10)

        publish_hz = float(self.get_parameter("publish_hz").value)
        self.create_timer(1.0 / max(publish_hz, 0.1), self._publish)
        self.get_logger().info("safety_guard started as the only /cmd_vel publisher.")

    def _declare_parameters(self) -> None:
        self.declare_parameter("publish_hz", 15.0)
        self.declare_parameter("max_linear_x_mps", 0.10)
        self.declare_parameter("min_linear_x_mps", 0.0)
        self.declare_parameter("max_angular_z_radps", 1.0)
        self.declare_parameter("desired_timeout_sec", 0.6)
        self.declare_parameter("obstacle_stop_distance_m", 0.25)
        self.declare_parameter("front_angle_deg", 30.0)
        self.declare_parameter("field_radius_m", 3.0)

    def _on_desired(self, msg: Twist) -> None:
        self.latest_desired = msg
        self.last_desired_time = self.get_clock().now()

    def _on_game_state(self, msg: String) -> None:
        self.game_state = msg.data
        if msg.data == "EMERGENCY_STOP":
            self.estop_latched = True

    def _on_command(self, msg: String) -> None:
        command = msg.data.strip().upper()
        if command == "ESTOP":
            self.estop_latched = True
        elif command == "RESET":
            self.estop_latched = False

    def _on_odom(self, msg: Odometry) -> None:
        pose = msg.pose.pose
        self.x = pose.position.x
        self.y = pose.position.y
        self.yaw = yaw_from_quaternion(
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        )

    def _on_scan(self, msg: LaserScan) -> None:
        threshold = float(self.get_parameter("obstacle_stop_distance_m").value)
        front_angle = radians(float(self.get_parameter("front_angle_deg").value))
        blocked = False
        angle = msg.angle_min
        for value in msg.ranges:
            if abs(angle) <= front_angle or abs(abs(angle) - 6.28318530718) <= front_angle:
                if isfinite(value) and msg.range_min <= value <= threshold:
                    blocked = True
                    break
            angle += msg.angle_increment
        self.front_blocked = blocked

    def _publish(self) -> None:
        safe = Twist()
        if self._must_stop():
            self.pub.publish(safe)
            return

        max_linear = float(self.get_parameter("max_linear_x_mps").value)
        min_linear = float(self.get_parameter("min_linear_x_mps").value)
        max_angular = float(self.get_parameter("max_angular_z_radps").value)
        safe.linear.x = clamp(float(self.latest_desired.linear.x), min_linear, max_linear)
        safe.angular.z = clamp(float(self.latest_desired.angular.z), -max_angular, max_angular)

        if self.front_blocked and safe.linear.x > 0.0:
            safe.linear.x = 0.0

        if self._moving_outward(safe.linear.x):
            safe.linear.x = 0.0

        self.pub.publish(safe)

    def _must_stop(self) -> bool:
        if self.estop_latched or self.game_state != "PLAYING":
            return True
        if self.last_desired_time is None:
            return True
        timeout = float(self.get_parameter("desired_timeout_sec").value)
        age = (self.get_clock().now() - self.last_desired_time).nanoseconds / 1_000_000_000.0
        return age > timeout

    def _moving_outward(self, linear_x: float) -> bool:
        field_radius = float(self.get_parameter("field_radius_m").value)
        radius = hypot(self.x, self.y)
        if radius <= field_radius or linear_x <= 0.0:
            return False
        world_vx = cos(self.yaw) * linear_x
        world_vy = sin(self.yaw) * linear_x
        return (self.x * world_vx + self.y * world_vy) > 0.0


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = SafetyGuard()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
