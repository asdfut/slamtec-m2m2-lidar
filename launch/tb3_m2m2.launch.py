"""TurtleBot3 (OpenCR) + Slamtec Mapper M2M2 as the robot's LiDAR.

Starts:
- robot_state_publisher with the TurtleBot3 URDF (base_footprint -> base_link -> base_scan ...)
- turtlebot3_node on the OpenCR (motors, IMU, battery, odom -> base_footprint)
- static TF base_scan -> laser (where the M2M2 sits relative to the stock LDS mount)
- opensw_ros laser_driver -> /scan in frame laser (respawns if the M2M2 drops off)
- m2m2_slam_bridge.py in odom mode -> /map, /m2m2/pose, TF map -> odom
- optionally RViz2

Usage (needs ~/m2m2_ws sourced for opensw_ros, and dialout access to the OpenCR):
  source ~/m2m2_ws/install/setup.bash
  ros2 launch launch/tb3_m2m2.launch.py
  ros2 launch launch/tb3_m2m2.launch.py laser_yaw:=3.1416 rviz:=true
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def generate_launch_description():
    tb3_bringup = get_package_share_directory("turtlebot3_bringup")
    tb3_description = get_package_share_directory("turtlebot3_description")

    model = LaunchConfiguration("model")
    usb_port = LaunchConfiguration("usb_port")
    host = LaunchConfiguration("host")

    robot_description = ParameterValue(
        Command(["xacro ", PathJoinSubstitution([tb3_description, "urdf", ["turtlebot3_", model, ".urdf"]]),
                 " namespace:="]),
        value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument("model", default_value="burger", description="TurtleBot3 model"),
        DeclareLaunchArgument("usb_port", default_value="/dev/ttyACM0", description="OpenCR serial port"),
        DeclareLaunchArgument("host", default_value="192.168.11.1", description="M2M2 IP address"),
        DeclareLaunchArgument("laser_x", default_value="0.0", description="M2M2 offset from base_scan [m]"),
        DeclareLaunchArgument("laser_y", default_value="0.0"),
        DeclareLaunchArgument("laser_z", default_value="0.0"),
        DeclareLaunchArgument("laser_yaw", default_value="0.0",
                              description="M2M2 yaw relative to the robot's forward direction [rad]"),
        DeclareLaunchArgument("rviz", default_value="false", description="Start RViz2"),

        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": robot_description}],
            output="screen"),

        Node(
            package="turtlebot3_node",
            executable="turtlebot3_ros",
            parameters=[PathJoinSubstitution([tb3_bringup, "param", [model, ".yaml"]]), {"namespace": ""}],
            arguments=["-i", usb_port],
            output="screen"),

        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            arguments=["--x", LaunchConfiguration("laser_x"), "--y", LaunchConfiguration("laser_y"),
                       "--z", LaunchConfiguration("laser_z"), "--yaw", LaunchConfiguration("laser_yaw"),
                       "--frame-id", "base_scan", "--child-frame-id", "laser"],
            output="screen"),

        # laser_driver exits on "Broken pipe" when the M2M2 reboots; respawn brings it back.
        Node(
            package="opensw_ros",
            executable="laser_driver",
            parameters=[{"host": host, "frame_id": "laser", "rate": 10.0}],
            respawn=True,
            respawn_delay=5.0,
            output="screen"),

        ExecuteProcess(
            cmd=["python3", os.path.join(REPO_DIR, "scripts", "m2m2_slam_bridge.py"),
                 "--ros-args", "-p", ["host:=", host], "-p", "odom_frame:=odom"],
            output="screen"),

        Node(
            package="rviz2",
            executable="rviz2",
            arguments=["-d", os.path.join(REPO_DIR, "rviz", "tb3_m2m2.rviz")],
            condition=IfCondition(LaunchConfiguration("rviz")),
            output="screen"),
    ])
