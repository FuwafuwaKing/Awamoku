from __future__ import annotations

from dataclasses import dataclass

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float32, Int32, String


VALID_COMMANDS = {"START", "RESET", "STOP", "ESTOP"}


@dataclass
class VoiceLevels:
    red: float = 0.0
    white: float = 0.0


class Phase0ContractNode(Node):
    """Minimal Awamoku topic contract node for Unity/ROS smoke tests."""

    def __init__(self) -> None:
        super().__init__("awamoku_phase0_contract")

        self.declare_parameter("game_duration_sec", 75.0)
        self.declare_parameter("publish_hz", 5.0)
        self.declare_parameter("initial_game_state", "IDLE")
        self.declare_parameter("initial_cloud_state", "DRIFT")

        self.game_duration_sec = float(
            self.get_parameter("game_duration_sec").get_parameter_value().double_value
        )
        publish_hz = float(self.get_parameter("publish_hz").get_parameter_value().double_value)
        self.game_state = self._string_parameter("initial_game_state", "IDLE")
        self.cloud_state = self._string_parameter("initial_cloud_state", "DRIFT")
        self.target_team = "NONE"
        self.effect_mode = "NORMAL"
        self.time_remaining = self.game_duration_sec
        self.scores = {"red": 0, "white": 0}
        self.comfort = {"red": 0.0, "white": 0.0}
        self.voice = VoiceLevels()
        self.last_tick_time = self.get_clock().now()

        self.create_subscription(
            Float32,
            "/awamoku/red/voice_level_sim",
            lambda msg: self._set_voice("red", msg.data),
            10,
        )
        self.create_subscription(
            Float32,
            "/awamoku/white/voice_level_sim",
            lambda msg: self._set_voice("white", msg.data),
            10,
        )
        self.create_subscription(String, "/awamoku/game/command", self._on_command, 10)

        self.red_voice_pub = self.create_publisher(Float32, "/awamoku/red/voice_level", 10)
        self.white_voice_pub = self.create_publisher(Float32, "/awamoku/white/voice_level", 10)
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
        self.desired_twist_pub = self.create_publisher(
            Twist, "/awamoku/motion/desired_twist", 10
        )

        self.create_timer(1.0 / max(publish_hz, 0.1), self._tick)
        self.get_logger().info("Awamoku Phase 0 contract node started.")

    def _string_parameter(self, name: str, fallback: str) -> str:
        value = self.get_parameter(name).get_parameter_value().string_value
        return value or fallback

    def _set_voice(self, team: str, value: float) -> None:
        clamped = max(0.0, min(1.0, float(value)))
        setattr(self.voice, team, clamped)

    def _on_command(self, msg: String) -> None:
        command = msg.data.strip().upper()
        if command not in VALID_COMMANDS:
            self.get_logger().warning(f"Ignoring unknown game command: {msg.data}")
            return

        if command == "START":
            self.game_state = "PLAYING"
            self.cloud_state = "DRIFT"
            self.target_team = "NONE"
            self.effect_mode = "NORMAL"
            self.time_remaining = self.game_duration_sec
            self._publish_event("GAME_START")
        elif command == "RESET":
            self.game_state = "IDLE"
            self.cloud_state = "DRIFT"
            self.target_team = "NONE"
            self.effect_mode = "NORMAL"
            self.time_remaining = self.game_duration_sec
            self.scores = {"red": 0, "white": 0}
            self.comfort = {"red": 0.0, "white": 0.0}
            self._publish_event("NONE")
        elif command == "STOP":
            self.game_state = "FINISHED"
            self.cloud_state = "DRIFT"
            self.target_team = "NONE"
            self.effect_mode = "FINISHED"
            self._publish_event("GAME_FINISH")
        elif command == "ESTOP":
            self.game_state = "EMERGENCY_STOP"
            self.cloud_state = "COOLDOWN"
            self.target_team = "NONE"
            self.effect_mode = "COOLDOWN"
            self._publish_event("NONE")

        self.get_logger().info(f"Accepted game command: {command}")

    def _tick(self) -> None:
        now = self.get_clock().now()
        dt = (now - self.last_tick_time).nanoseconds / 1_000_000_000.0
        self.last_tick_time = now

        if self.game_state == "PLAYING":
            self.time_remaining = max(0.0, self.time_remaining - dt)
            if self.time_remaining <= 0.0:
                self.game_state = "FINISHED"
                self.effect_mode = "FINISHED"
                self._publish_event("DRAW")

        self.red_voice_pub.publish(Float32(data=self.voice.red))
        self.white_voice_pub.publish(Float32(data=self.voice.white))
        self.game_state_pub.publish(String(data=self.game_state))
        self.cloud_state_pub.publish(String(data=self.cloud_state))
        self.target_team_pub.publish(String(data=self.target_team))
        self.red_score_pub.publish(Int32(data=self.scores["red"]))
        self.white_score_pub.publish(Int32(data=self.scores["white"]))
        self.red_comfort_pub.publish(Float32(data=self.comfort["red"]))
        self.white_comfort_pub.publish(Float32(data=self.comfort["white"]))
        self.time_pub.publish(Float32(data=self.time_remaining))
        self.effect_mode_pub.publish(String(data=self.effect_mode))
        self.desired_twist_pub.publish(Twist())

    def _publish_event(self, event: str) -> None:
        self.effect_event_pub.publish(String(data=event))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = Phase0ContractNode()
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
