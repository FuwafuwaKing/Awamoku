from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class VoiceSourceMux(Node):
    def __init__(self) -> None:
        super().__init__("voice_source_mux")
        self.declare_parameter("voice_source", "sim")
        self.declare_parameter("publish_hz", 10.0)
        self.declare_parameter("input_timeout_sec", 1.0)

        self.values = {
            "sim": {"red": 0.0, "white": 0.0},
            "real": {"red": 0.0, "white": 0.0},
        }
        self.last_seen = {
            "sim": {"red": None, "white": None},
            "real": {"red": None, "white": None},
        }

        self.create_subscription(
            Float32, "/awamoku/red/voice_level_sim", lambda msg: self._set("sim", "red", msg), 10
        )
        self.create_subscription(
            Float32,
            "/awamoku/white/voice_level_sim",
            lambda msg: self._set("sim", "white", msg),
            10,
        )
        self.create_subscription(
            Float32,
            "/awamoku/red/voice_level_real",
            lambda msg: self._set("real", "red", msg),
            10,
        )
        self.create_subscription(
            Float32,
            "/awamoku/white/voice_level_real",
            lambda msg: self._set("real", "white", msg),
            10,
        )
        self.red_pub = self.create_publisher(Float32, "/awamoku/red/voice_level", 10)
        self.white_pub = self.create_publisher(Float32, "/awamoku/white/voice_level", 10)

        publish_hz = float(self.get_parameter("publish_hz").value)
        self.create_timer(1.0 / max(publish_hz, 0.1), self._publish)
        self.get_logger().info("voice_source_mux started.")

    def _set(self, source: str, team: str, msg: Float32) -> None:
        self.values[source][team] = max(0.0, min(1.0, float(msg.data)))
        self.last_seen[source][team] = self.get_clock().now()

    def _publish(self) -> None:
        source = str(self.get_parameter("voice_source").value).lower()
        if source not in self.values:
            source = "sim"
        timeout = float(self.get_parameter("input_timeout_sec").value)
        red = self._fresh_value(source, "red", timeout)
        white = self._fresh_value(source, "white", timeout)
        self.red_pub.publish(Float32(data=red))
        self.white_pub.publish(Float32(data=white))

    def _fresh_value(self, source: str, team: str, timeout: float) -> float:
        last_seen = self.last_seen[source][team]
        if last_seen is None:
            return 0.0
        age = (self.get_clock().now() - last_seen).nanoseconds / 1_000_000_000.0
        if age > timeout:
            return 0.0
        return self.values[source][team]


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = VoiceSourceMux()
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
