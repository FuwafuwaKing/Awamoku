from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class MicrophoneAdapter(Node):
    """Placeholder real microphone adapter.

    It publishes configured fixed levels so the real-input path can be tested
    without audio devices. Actual RMS capture and calibration belong to Phase 5.
    """

    def __init__(self) -> None:
        super().__init__("microphone_adapter")
        self.declare_parameter("publish_hz", 10.0)
        self.declare_parameter("red_level", 0.0)
        self.declare_parameter("white_level", 0.0)
        self.red_pub = self.create_publisher(Float32, "/awamoku/red/voice_level_real", 10)
        self.white_pub = self.create_publisher(Float32, "/awamoku/white/voice_level_real", 10)
        publish_hz = float(self.get_parameter("publish_hz").value)
        self.create_timer(1.0 / max(publish_hz, 0.1), self._publish)
        self.get_logger().warning(
            "microphone_adapter is a fixed-level placeholder; no audio device is opened."
        )

    def _publish(self) -> None:
        red = max(0.0, min(1.0, float(self.get_parameter("red_level").value)))
        white = max(0.0, min(1.0, float(self.get_parameter("white_level").value)))
        self.red_pub.publish(Float32(data=red))
        self.white_pub.publish(Float32(data=white))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = MicrophoneAdapter()
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
