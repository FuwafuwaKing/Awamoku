from __future__ import annotations

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import Float32, Int32, String

from awamoku_game.game_logic import CloudGame, GameConfig, Point


class CloudGameManager(Node):
    def __init__(self) -> None:
        super().__init__("cloud_game_manager")
        self._declare_parameters()
        self.game = CloudGame(self._config_from_parameters())
        self.last_tick_time = self.get_clock().now()

        self.create_subscription(Float32, "/awamoku/red/voice_level", self._on_red_voice, 10)
        self.create_subscription(Float32, "/awamoku/white/voice_level", self._on_white_voice, 10)
        self.create_subscription(String, "/awamoku/game/command", self._on_command, 10)
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)

        self.game_state_pub = self.create_publisher(String, "/awamoku/game/state", 10)
        self.cloud_state_pub = self.create_publisher(String, "/awamoku/cloud/state", 10)
        self.target_team_pub = self.create_publisher(String, "/awamoku/cloud/target_team", 10)
        self.red_score_pub = self.create_publisher(Int32, "/awamoku/red/score", 10)
        self.white_score_pub = self.create_publisher(Int32, "/awamoku/white/score", 10)
        self.red_comfort_pub = self.create_publisher(Float32, "/awamoku/red/comfort", 10)
        self.white_comfort_pub = self.create_publisher(Float32, "/awamoku/white/comfort", 10)
        self.time_pub = self.create_publisher(Float32, "/awamoku/game/time_remaining", 10)
        self.effect_event_pub = self.create_publisher(String, "/awamoku/effect/event", 10)
        self.effect_mode_pub = self.create_publisher(String, "/awamoku/effect/mode", 10)

        publish_hz = self.get_parameter("publish_hz").value
        self.create_timer(1.0 / max(float(publish_hz), 0.1), self._tick)
        self._publish_snapshot()
        self.get_logger().info("cloud_game_manager started.")

    def _declare_parameters(self) -> None:
        defaults = GameConfig()
        self.declare_parameter("game_duration_sec", defaults.game_duration_sec)
        self.declare_parameter("publish_hz", 5.0)
        self.declare_parameter("comfort_score_per_sec", defaults.comfort_score_per_sec)
        self.declare_parameter("comfort_bonus_duration_sec", defaults.comfort_bonus_duration_sec)
        self.declare_parameter("comfort_bonus_score", defaults.comfort_bonus_score)
        self.declare_parameter("cooldown_sec", defaults.cooldown_sec)
        self.declare_parameter("panic_hold_sec", defaults.panic_hold_sec)
        self.declare_parameter("shy_distance_m", defaults.shy_distance_m)
        self.declare_parameter("comfort_min_distance_m", defaults.comfort_min_distance_m)
        self.declare_parameter("comfort_max_distance_m", defaults.comfort_max_distance_m)
        self.declare_parameter("return_arrival_distance_m", defaults.return_arrival_distance_m)
        self.declare_parameter("far_call_min", defaults.far_call_min)
        self.declare_parameter("far_call_max", defaults.far_call_max)
        self.declare_parameter("near_comfort_min", defaults.near_comfort_min)
        self.declare_parameter("near_comfort_max", defaults.near_comfort_max)
        self.declare_parameter("near_panic_min", defaults.near_panic_min)
        self.declare_parameter("voice_margin", defaults.voice_margin)
        self.declare_parameter("red_team_x", defaults.red_team.x)
        self.declare_parameter("red_team_y", defaults.red_team.y)
        self.declare_parameter("white_team_x", defaults.white_team.x)
        self.declare_parameter("white_team_y", defaults.white_team.y)
        self.declare_parameter("center_x", defaults.center.x)
        self.declare_parameter("center_y", defaults.center.y)

    def _config_from_parameters(self) -> GameConfig:
        return GameConfig(
            game_duration_sec=float(self.get_parameter("game_duration_sec").value),
            comfort_score_per_sec=float(self.get_parameter("comfort_score_per_sec").value),
            comfort_bonus_duration_sec=float(
                self.get_parameter("comfort_bonus_duration_sec").value
            ),
            comfort_bonus_score=int(self.get_parameter("comfort_bonus_score").value),
            cooldown_sec=float(self.get_parameter("cooldown_sec").value),
            panic_hold_sec=float(self.get_parameter("panic_hold_sec").value),
            shy_distance_m=float(self.get_parameter("shy_distance_m").value),
            comfort_min_distance_m=float(self.get_parameter("comfort_min_distance_m").value),
            comfort_max_distance_m=float(self.get_parameter("comfort_max_distance_m").value),
            return_arrival_distance_m=float(
                self.get_parameter("return_arrival_distance_m").value
            ),
            far_call_min=float(self.get_parameter("far_call_min").value),
            far_call_max=float(self.get_parameter("far_call_max").value),
            near_comfort_min=float(self.get_parameter("near_comfort_min").value),
            near_comfort_max=float(self.get_parameter("near_comfort_max").value),
            near_panic_min=float(self.get_parameter("near_panic_min").value),
            voice_margin=float(self.get_parameter("voice_margin").value),
            red_team=Point(
                float(self.get_parameter("red_team_x").value),
                float(self.get_parameter("red_team_y").value),
            ),
            white_team=Point(
                float(self.get_parameter("white_team_x").value),
                float(self.get_parameter("white_team_y").value),
            ),
            center=Point(
                float(self.get_parameter("center_x").value),
                float(self.get_parameter("center_y").value),
            ),
        )

    def _on_red_voice(self, msg: Float32) -> None:
        self.game.set_voice(red=msg.data)

    def _on_white_voice(self, msg: Float32) -> None:
        self.game.set_voice(white=msg.data)

    def _on_odom(self, msg: Odometry) -> None:
        position = msg.pose.pose.position
        self.game.set_robot_position(position.x, position.y)

    def _on_command(self, msg: String) -> None:
        snapshot = self.game.command(msg.data)
        self._publish_snapshot(snapshot)
        if snapshot.event != "NONE":
            self.get_logger().info(f"event={snapshot.event}")

    def _tick(self) -> None:
        now = self.get_clock().now()
        dt = (now - self.last_tick_time).nanoseconds / 1_000_000_000.0
        self.last_tick_time = now
        snapshot = self.game.step(dt)
        self._publish_snapshot(snapshot)

    def _publish_snapshot(self, snapshot=None) -> None:
        snapshot = snapshot or self.game.snapshot()
        self.game_state_pub.publish(String(data=snapshot.game_state))
        self.cloud_state_pub.publish(String(data=snapshot.cloud_state))
        self.target_team_pub.publish(String(data=snapshot.target_team))
        self.red_score_pub.publish(Int32(data=snapshot.red_score))
        self.white_score_pub.publish(Int32(data=snapshot.white_score))
        self.red_comfort_pub.publish(Float32(data=snapshot.red_comfort))
        self.white_comfort_pub.publish(Float32(data=snapshot.white_comfort))
        self.time_pub.publish(Float32(data=snapshot.time_remaining))
        self.effect_mode_pub.publish(String(data=snapshot.effect_mode))
        if snapshot.event != "NONE":
            self.effect_event_pub.publish(String(data=snapshot.event))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = CloudGameManager()
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
