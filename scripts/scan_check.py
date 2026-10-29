import math
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

DURATION = 6.0


class ScanCheck(Node):
    def __init__(self):
        super().__init__("scan_check")
        self.msgs = []
        self.create_subscription(LaserScan, "scan", self.msgs.append, qos_profile_sensor_data)


def main():
    rclpy.init()
    node = ScanCheck()
    end = time.time() + DURATION
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    msgs = node.msgs
    print(f"received {len(msgs)} scans in {DURATION:.0f}s -> {len(msgs) / DURATION:.1f} Hz")
    if not msgs:
        return
    m = msgs[-1]
    n = len(m.ranges)
    valid = [r for r in m.ranges if math.isfinite(r) and m.range_min <= r <= m.range_max and r > 0]
    print(f"frame_id={m.header.frame_id} points={n} valid={len(valid)} ({100 * len(valid) / n:.0f}%)")
    print(f"angle {math.degrees(m.angle_min):.1f} .. {math.degrees(m.angle_max):.1f} deg, "
          f"step {math.degrees(m.angle_increment):.3f} deg, range_min={m.range_min} range_max={m.range_max}")
    if valid:
        print(f"distance min {min(valid):.3f} m, max {max(valid):.3f} m, "
              f"median {sorted(valid)[len(valid) // 2]:.3f} m")
    print("sector  (angle: nearest valid distance)")
    for deg in range(-180, 180, 30):
        lo, hi = math.radians(deg), math.radians(deg + 30)
        vals = [r for i, r in enumerate(m.ranges)
                if lo <= m.angle_min + i * m.angle_increment < hi
                and math.isfinite(r) and m.range_min <= r <= m.range_max and r > 0]
        print(f"  {deg:+4d}..{deg + 30:+4d} deg: " + (f"{min(vals):.2f} m ({len(vals)} pts)" if vals else "no returns"))
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
