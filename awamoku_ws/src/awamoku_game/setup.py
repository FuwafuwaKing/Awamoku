import os
from glob import glob

from setuptools import setup

package_name = "awamoku_game"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="haruki",
    maintainer_email="haruki@example.com",
    description="Awamoku Unity + ROS 2 cloud robot prototype.",
    license="All rights reserved",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "cloud_game_manager = awamoku_game.cloud_game_manager:main",
            "cloud_motion_controller = awamoku_game.cloud_motion_controller:main",
            "effect_adapter = awamoku_game.effect_adapter:main",
            "microphone_adapter = awamoku_game.microphone_adapter:main",
            "phase0_contract_node = awamoku_game.phase0_contract_node:main",
            "safety_guard = awamoku_game.safety_guard:main",
            "unity_voice_adapter = awamoku_game.unity_voice_adapter:main",
            "voice_source_mux = awamoku_game.voice_source_mux:main",
        ],
    },
)
