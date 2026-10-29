"""Publish the Slamtec Mapper M2M2's on-board SLAM result to ROS 2.

- /map (nav_msgs/OccupancyGrid, latched): the device's explorer map
- TF map -> laser: the device's pose estimate
- /m2m2/pose (geometry_msgs/PoseStamped)

Run alongside opensw_ros laser_driver (frame_id:=laser) so /scan lines up with the map.
"""
import math
import os
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from tf2_ros import TransformBroadcaster

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slamware_client import SlamwareClient  # noqa: E402


def yaw_to_quat(yaw):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class M2M2SlamBridge(Node):
    def __init__(self):
        super().__init__("m2m2_slam_bridge")
        self.host = self.declare_parameter("host", "192.168.11.1").value
        self.port = self.declare_parameter("port", 1445).value
        self.map_frame = self.declare_parameter("map_frame", "map").value
        self.laser_frame = self.declare_parameter("laser_frame", "laser").value
        pose_rate = self.declare_parameter("pose_rate", 10.0).value
        map_period = self.declare_parameter("map_period", 2.0).value

        latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.map_pub = self.create_publisher(OccupancyGrid, "map", latched)
        self.pose_pub = self.create_publisher(PoseStamped, "m2m2/pose", 10)
        self.tf = TransformBroadcaster(self)
        self.client = None

        self.create_timer(1.0 / pose_rate, self.publish_pose)
        self.create_timer(map_period, self.publish_map)

    def ensure_client(self):
        if self.client is None:
            try:
                self.client = SlamwareClient(self.host, self.port)
                self.get_logger().info(f"Connected to {self.host}:{self.port}")
            except OSError as e:
                self.get_logger().warn(f"Connect failed: {e}", throttle_duration_sec=5.0)
        return self.client

    def call(self, fn, *args):
        if self.ensure_client() is None:
            return None
        try:
            return fn(self.client, *args)
        except (OSError, ValueError, KeyError) as e:
            self.get_logger().warn(f"Request failed, reconnecting: {e}")
            self.client.close()
            self.client = None
            return None

    def publish_pose(self):
        p = self.call(SlamwareClient.pose)
        if p is None:
            return
        stamp = self.get_clock().now().to_msg()
        qx, qy, qz, qw = yaw_to_quat(p["yaw"])

        t = TransformStamped()
        t.header.stamp = stamp
        t.header.frame_id = self.map_frame
        t.child_frame_id = self.laser_frame
        t.transform.translation.x = p["x"]
        t.transform.translation.y = p["y"]
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self.tf.sendTransform(t)

        msg = PoseStamped()
        msg.header = t.header
        msg.pose.position.x = p["x"]
        msg.pose.position.y = p["y"]
        msg.pose.orientation.z = qz
        msg.pose.orientation.w = qw
        self.pose_pub.publish(msg)

    def publish_map(self):
        area = self.call(SlamwareClient.known_area)
        if area is None:
            return
        width = area["max_x"] - area["min_x"]
        height = area["max_y"] - area["min_y"]
        if width <= 0 or height <= 0:
            return
        m = self.call(SlamwareClient.map_bitmap, area["min_x"], area["min_y"], width, height)
        if m is None:
            return

        grid = OccupancyGrid()
        grid.header.stamp = self.get_clock().now().to_msg()
        grid.header.frame_id = self.map_frame
        grid.info.resolution = m["resolution"]
        grid.info.width = m["dimension_x"]
        grid.info.height = m["dimension_y"]
        grid.info.origin.position.x = m["real_x"]
        grid.info.origin.position.y = m["real_y"]
        grid.info.origin.orientation.w = 1.0
        # Slamware 8-bit cells are signed: 0 unknown, > 0 free, < 0 occupied.
        grid.data = [-1 if c == 0 else (0 if c < 128 else 100) for c in m["cells"]]
        self.map_pub.publish(grid)


def main():
    rclpy.init()
    node = M2M2SlamBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.client:
            node.client.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
