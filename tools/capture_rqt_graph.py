#!/usr/bin/env python3
"""Capture the complete live ROS 2 graph with rqt_graph's DOT generator."""

from pathlib import Path
import subprocess
import time

import rclpy
from qt_dotgraph.pydotfactory import PydotFactory
from rqt_graph.dotcode import NODE_TOPIC_ALL_GRAPH, RosGraphDotcodeGenerator
from rqt_graph.rosgraph2_impl import Graph


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "docs" / "images"
DOT_PATH = OUTPUT_DIR / "rqt_graph_complete.dot"
SVG_PATH = OUTPUT_DIR / "rqt_graph_complete.svg"
PNG_PATH = OUTPUT_DIR / "rqt_graph_complete_16x9.png"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = rclpy.create_node("rqt_graph_capture")

    try:
        # Let DDS discovery observe every publisher and subscriber before polling.
        time.sleep(3)
        graph = Graph(node)
        graph.set_node_stale(5.0)
        graph.update()

        dotcode = RosGraphDotcodeGenerator(node).generate_dotcode(
            rosgraphinst=graph,
            ns_filter="/",
            topic_filter="/",
            graph_mode=NODE_TOPIC_ALL_GRAPH,
            dotcode_factory=PydotFactory(),
            hide_single_connection_topics=False,
            hide_dead_end_topics=False,
            cluster_namespaces_level=0,
            accumulate_actions=False,
            orientation="LR",
            ranksep=0.7,
            quiet=False,
            unreachable=False,
            hide_tf_nodes=False,
            group_tf_nodes=False,
            group_image_nodes=False,
            hide_dynamic_reconfigure=False,
        )
        DOT_PATH.write_text(dotcode, encoding="utf-8")

        subprocess.run(["dot", "-Tsvg", str(DOT_PATH), "-o", str(SVG_PATH)], check=True)
        subprocess.run(
            [
                "convert",
                "-density",
                "180",
                str(SVG_PATH),
                "-resize",
                "1880x1000",
                "-background",
                "white",
                "-gravity",
                "center",
                "-extent",
                "1920x1080",
                "-colorspace",
                "sRGB",
                "-depth",
                "8",
                str(PNG_PATH),
            ],
            check=True,
        )
        print(PNG_PATH)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
