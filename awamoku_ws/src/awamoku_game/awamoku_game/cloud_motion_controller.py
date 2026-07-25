from __future__ import annotations

from math import atan2, cos, hypot, sin

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String

from awamoku_game.ros_utils import clamp, normalize_angle, yaw_from_quaternion


class CloudMotionController(Node):
    def __init__(self) -> None:
        super().__init__("cloud_motion_controller")
        self._declare_parameters()
        self.game_state = "IDLE"
        self.cloud_state = "DRIFT"
        self.target_team = "NONE"
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.wind_index = 0

        self.create_subscription(String, "/awamoku/game/state", self._on_game_state, 10)
        self.create_subscription(String, "/awamoku/cloud/state", self._on_cloud_state, 10)
        self.create_subscription(String, "/awamoku/cloud/target_team", self._on_target_team, 10)
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)
        self.pub = self.create_publisher(Twist, "/awamoku/motion/desired_twist", 10)

        publish_hz = float(self.get_parameter("publish_hz").value)
        self.create_timer(1.0 / max(publish_hz, 0.1), self._publish)
        self.get_logger().info("cloud_motion_controller started.")

    def _declare_parameters(self) -> None:
        self.declare_parameter("publish_hz", 15.0)
        self.declare_parameter("linear_speed_mps", 0.16)
        self.declare_parameter("panic_linear_speed_mps", 0.14)
        self.declare_parameter("angular_speed_gain", 1.4)
        self.declare_parameter("max_angular_speed_radps", 1.1)
        self.declare_parameter("drift_tangent_weight", 0.55)
        self.declare_parameter("restore_weight", 0.75)
        self.declare_parameter("attract_weight", 0.80)
        self.declare_parameter("wind_weight", 0.08)
        self.declare_parameter("wind_period_sec", 4.0)
        self.declare_parameter("lane_radius_m", 1.0)
        self.declare_parameter("comfort_orbit_radius_m", 1.25)
        self.declare_parameter("comfort_orbit_tangent_weight", 0.70)
        self.declare_parameter("comfort_orbit_restore_weight", 1.00)
        self.declare_parameter("red_team_x", 2.5)
        self.declare_parameter("red_team_y", 0.0)
        self.declare_parameter("white_team_x", -2.5)
        self.declare_parameter("white_team_y", 0.0)
        self.declare_parameter("center_x", 0.0)
        self.declare_parameter("center_y", 0.0)

    def _on_game_state(self, msg: String) -> None:
        self.game_state = msg.data

    def _on_cloud_state(self, msg: String) -> None:
        self.cloud_state = msg.data

    def _on_target_team(self, msg: String) -> None:
        self.target_team = msg.data

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

    def _publish(self) -> None:
        twist = Twist()
        if self.game_state != "PLAYING":
            self.pub.publish(twist)
            return

        vx, vy, speed = self._desired_vector()
        magnitude = hypot(vx, vy)
        if magnitude < 1e-6:
            self.pub.publish(twist)
            return

        desired_heading = atan2(vy, vx)
        heading_error = normalize_angle(desired_heading - self.yaw)
        max_omega = float(self.get_parameter("max_angular_speed_radps").value)
        omega_gain = float(self.get_parameter("angular_speed_gain").value)
        twist.angular.z = clamp(omega_gain * heading_error, -max_omega, max_omega)
        if abs(heading_error) > 1.45:
            twist.linear.x = 0.0
        else:
            twist.linear.x = speed * max(0.0, cos(heading_error))
        self.pub.publish(twist)

    def _desired_vector(self) -> tuple[float, float, float]:
        cx = float(self.get_parameter("center_x").value)
        cy = float(self.get_parameter("center_y").value)
        dx = self.x - cx
        dy = self.y - cy
        radius = hypot(dx, dy)
        lane_radius = max(0.1, float(self.get_parameter("lane_radius_m").value))
        restore_weight = float(self.get_parameter("restore_weight").value)
        tangent_weight = float(self.get_parameter("drift_tangent_weight").value)
        attract_weight = float(self.get_parameter("attract_weight").value)
        wind_weight = float(self.get_parameter("wind_weight").value)
        speed = float(self.get_parameter("linear_speed_mps").value)

        if radius > 1e-6:
            radial_error = lane_radius - radius
            restore_x = (dx / radius) * radial_error * restore_weight
            restore_y = (dy / radius) * radial_error * restore_weight
            tangent_x = -dy / radius * tangent_weight
            tangent_y = dx / radius * tangent_weight
        else:
            restore_x = lane_radius * restore_weight
            restore_y = 0.0
            tangent_x = 0.0
            tangent_y = tangent_weight

        wind_x, wind_y = self._wind_vector()
        vx = restore_x + tangent_x + wind_x * wind_weight
        vy = restore_y + tangent_y + wind_y * wind_weight

        if self.cloud_state == "PANIC_RETURN":
            speed = float(self.get_parameter("panic_linear_speed_mps").value)
            return cx - self.x, cy - self.y, speed

        if self.cloud_state == "COOLDOWN":
            return restore_x + tangent_x * 0.35, restore_y + tangent_y * 0.35, speed * 0.45

        if self.target_team in {"RED", "WHITE"}:
            tx, ty = self._team_position(self.target_team)
            to_team_x = tx - self.x
            to_team_y = ty - self.y
            team_distance = max(1e-6, hypot(to_team_x, to_team_y))
            team_x = to_team_x / team_distance * attract_weight
            team_y = to_team_y / team_distance * attract_weight
            if self.cloud_state.startswith("COMFORT"):
                orbit_x, orbit_y = self._orbit_team_vector(tx, ty)
                return orbit_x, orbit_y, speed * 0.55
            if self.cloud_state.startswith("SHY"):
                return restore_x + tangent_x * 0.25, restore_y + tangent_y * 0.25, speed * 0.45
            return vx + team_x, vy + team_y, speed
        return vx, vy, speed

    def _orbit_team_vector(self, tx: float, ty: float) -> tuple[float, float]:
        dx = self.x - tx
        dy = self.y - ty
        radius = hypot(dx, dy)
        orbit_radius = max(0.2, float(self.get_parameter("comfort_orbit_radius_m").value))
        tangent_weight = float(self.get_parameter("comfort_orbit_tangent_weight").value)
        restore_weight = float(self.get_parameter("comfort_orbit_restore_weight").value)

        if radius > 1e-6:
            radial_error = orbit_radius - radius
            restore_x = (dx / radius) * radial_error * restore_weight
            restore_y = (dy / radius) * radial_error * restore_weight
            tangent_x = -dy / radius * tangent_weight
            tangent_y = dx / radius * tangent_weight
            return restore_x + tangent_x, restore_y + tangent_y
        return orbit_radius * restore_weight, tangent_weight

    def _wind_vector(self) -> tuple[float, float]:
        period = max(0.1, float(self.get_parameter("wind_period_sec").value))
        seconds = self.get_clock().now().nanoseconds / 1_000_000_000.0
        angle = (seconds / period) * 1.57079632679
        return cos(angle), sin(angle)

    def _team_position(self, team: str) -> tuple[float, float]:
        if team == "RED":
            return (
                float(self.get_parameter("red_team_x").value),
                float(self.get_parameter("red_team_y").value),
            )
        return (
            float(self.get_parameter("white_team_x").value),
            float(self.get_parameter("white_team_y").value),
        )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = CloudMotionController()
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
