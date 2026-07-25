from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class EffectAdapter(Node):
    def __init__(self) -> None:
        super().__init__("effect_adapter")
        self.declare_parameter("log_events", True)
        self.current_mode = "NORMAL"
        self.create_subscription(String, "/awamoku/effect/event", self._on_event, 10)
        self.create_subscription(String, "/awamoku/effect/mode", self._on_mode, 10)
        self.get_logger().info("effect_adapter started in log-only mode.")

    def _on_event(self, msg: String) -> None:
        if bool(self.get_parameter("log_events").value):
            self.get_logger().info(f"effect event: {msg.data}")

    def _on_mode(self, msg: String) -> None:
        if msg.data != self.current_mode:
            self.current_mode = msg.data
            if bool(self.get_parameter("log_events").value):
                self.get_logger().info(f"effect mode: {msg.data}")


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = EffectAdapter()
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
