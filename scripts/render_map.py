"""Save a PNG of the M2M2 SLAM map with the latest laser scan and pose overlaid.

Needs m2m2_slam_bridge.py and the opensw_ros laser_driver running (same ROS_DOMAIN_ID).
Usage: python3 render_map.py [output.png]
"""
import math
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rclpy  # noqa: E402
from geometry_msgs.msg import PoseStamped  # noqa: E402
from nav_msgs.msg import OccupancyGrid  # noqa: E402
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data  # noqa: E402
from sensor_msgs.msg import LaserScan  # noqa: E402


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "m2m2_map.png"
    rclpy.init()
    node = rclpy.create_node("m2m2_render_map")
    got = {}
    latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(OccupancyGrid, "map", lambda m: got.__setitem__("map", m), latched)
    node.create_subscription(LaserScan, "scan", lambda m: got.__setitem__("scan", m), qos_profile_sensor_data)
    node.create_subscription(PoseStamped, "m2m2/pose", lambda m: got.__setitem__("pose", m), 10)
    end = time.time() + 10
    while time.time() < end and len(got) < 3:
        rclpy.spin_once(node, timeout_sec=0.1)
    if "map" not in got:
        sys.exit("No /map received. Is m2m2_slam_bridge.py running?")

    m = got["map"]
    info = m.info
    grid = np.array(m.data, dtype=np.int16).reshape(info.height, info.width)
    img = np.full(grid.shape, 0.75)          # unknown: light grey
    img[grid == 0] = 1.0                      # free: white
    img[grid == 100] = 0.1                    # occupied: near black
    x0, y0, res = info.origin.position.x, info.origin.position.y, info.resolution
    extent = [x0, x0 + info.width * res, y0, y0 + info.height * res]

    fig, ax = plt.subplots(figsize=(6, 6 * info.height / max(info.width, 1) + 0.6), dpi=120)
    ax.imshow(img, cmap="gray", vmin=0, vmax=1, origin="lower", extent=extent, interpolation="nearest")

    if "pose" in got:
        p = got["pose"].pose
        yaw = 2 * math.atan2(p.orientation.z, p.orientation.w)
        px, py = p.position.x, p.position.y
        if "scan" in got:
            s = got["scan"]
            angles = s.angle_min + np.arange(len(s.ranges)) * s.angle_increment
            r = np.array(s.ranges)
            ok = np.isfinite(r) & (r > 0) & (r <= s.range_max)
            ax.scatter(px + r[ok] * np.cos(angles[ok] + yaw), py + r[ok] * np.sin(angles[ok] + yaw),
                       s=2, c="#d62728", label="laser scan")
        ax.arrow(px, py, 0.35 * math.cos(yaw), 0.35 * math.sin(yaw), width=0.05,
                 color="#1f77b4", length_includes_head=True, label="M2M2 pose")
        ax.legend(loc="upper right", fontsize=8)

    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"M2M2 SLAM map  {info.width}x{info.height} cells @ {res:.2f} m")
    fig.tight_layout()
    fig.savefig(out)
    print(f"saved {out}")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
