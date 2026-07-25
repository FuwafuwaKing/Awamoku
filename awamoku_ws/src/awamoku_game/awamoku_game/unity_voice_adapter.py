from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class UnityVoiceAdapter(Node):
    """Optional clamp adapter for raw Unity sliders.

    Unity may publish directly to `/awamoku/*/voice_level_sim`. If a scene needs a
    raw debugging topic, publish to `*_voice_level_sim_raw` and run this node.
    """

    def __init__(self) -> None:
        super().__init__("unity_voice_adapter")
        self.create_subscription(
            Float32,
            "/awamoku/red/voice_level_sim_raw",
            lambda msg: self._publish(self.red_pub, msg),
            10,
        )
        self.create_subscription(
            Float32,
            "/awamoku/white/voice_level_sim_raw",
            lambda msg: self._publish(self.white_pub, msg),
            10,
        )
        self.red_pub = self.create_publisher(Float32, "/awamoku/red/voice_level_sim", 10)
        self.white_pub = self.create_publisher(Float32, "/awamoku/white/voice_level_sim", 10)
        self.get_logger().info("unity_voice_adapter started.")

    def _publish(self, publisher, msg: Float32) -> None:
        publisher.publish(Float32(data=max(0.0, min(1.0, float(msg.data)))))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = UnityVoiceAdapter()
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
