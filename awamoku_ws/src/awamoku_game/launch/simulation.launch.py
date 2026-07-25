from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from awamoku_game.launch_guards import claim_single_instance


def generate_launch_description() -> LaunchDescription:
    model = LaunchConfiguration("model")
    ros_domain_id = LaunchConfiguration("ros_domain_id")
    ros_ip = LaunchConfiguration("ros_ip")
    voice_source = LaunchConfiguration("voice_source")
    use_gazebo = LaunchConfiguration("use_gazebo")
    use_endpoint = LaunchConfiguration("use_endpoint")
    use_microphone_placeholder = LaunchConfiguration("use_microphone_placeholder")

    turtlebot3_gazebo_launch = PathJoinSubstitution(
        [FindPackageShare("turtlebot3_gazebo"), "launch", "empty_world.launch.py"]
    )
    params_file = PathJoinSubstitution(
        [FindPackageShare("awamoku_game"), "config", "awamoku_params.yaml"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "model",
                default_value=EnvironmentVariable("TURTLEBOT3_MODEL", default_value="burger"),
            ),
            DeclareLaunchArgument(
                "ros_domain_id",
                default_value=EnvironmentVariable("ROS_DOMAIN_ID", default_value="30"),
            ),
            DeclareLaunchArgument("ros_ip", default_value="0.0.0.0"),
            DeclareLaunchArgument("voice_source", default_value="sim"),
            DeclareLaunchArgument("use_gazebo", default_value="true"),
            DeclareLaunchArgument("use_endpoint", default_value="true"),
            DeclareLaunchArgument("use_microphone_placeholder", default_value="false"),
            SetEnvironmentVariable("ROS_DOMAIN_ID", ros_domain_id),
            SetEnvironmentVariable("TURTLEBOT3_MODEL", model),
            OpaqueFunction(
                function=claim_single_instance,
                args=[ros_domain_id, use_endpoint, ros_ip],
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(turtlebot3_gazebo_launch),
                condition=IfCondition(use_gazebo),
            ),
            Node(
                package="ros_tcp_endpoint",
                executable="default_server_endpoint",
                name="UnityEndpoint",
                emulate_tty=True,
                condition=IfCondition(use_endpoint),
                parameters=[{"ROS_IP": ros_ip}, {"ROS_TCP_PORT": 10000}],
            ),
            Node(
                package="awamoku_game",
                executable="voice_source_mux",
                name="voice_source_mux",
                output="screen",
                parameters=[params_file, {"voice_source": voice_source}],
            ),
            Node(
                package="awamoku_game",
                executable="cloud_game_manager",
                name="cloud_game_manager",
                output="screen",
                parameters=[params_file],
            ),
            Node(
                package="awamoku_game",
                executable="cloud_motion_controller",
                name="cloud_motion_controller",
                output="screen",
                parameters=[params_file],
            ),
            Node(
                package="awamoku_game",
                executable="safety_guard",
                name="safety_guard",
                output="screen",
                parameters=[params_file],
            ),
            Node(
                package="awamoku_game",
                executable="effect_adapter",
                name="effect_adapter",
                output="screen",
                parameters=[params_file],
            ),
            Node(
                package="awamoku_game",
                executable="microphone_adapter",
                name="microphone_adapter",
                output="screen",
                condition=IfCondition(use_microphone_placeholder),
                parameters=[params_file],
            ),
        ]
    )
