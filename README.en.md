# Slamtec Mapper M2M2 LiDAR: ROS 2 Jazzy testing, RViz2 and on-board SLAM map (2026-10-29)

[中文](README.md) | **English**

Environment: Ubuntu 24.04, ROS 2 Jazzy, x86 laptop. The M2M2 is connected straight to the laptop with an Ethernet cable. `ROS_DOMAIN_ID=99`.

Results:
- The M2M2 scans at about **10.8 Hz**, 853 points per revolution, full 360°, with sensible distances
- `/scan` comes from the open-source driver [hatchbed/opensw_ros](https://github.com/hatchbed/opensw_ros). It dates from 2022 and needs 3 fixes to build and run on Ubuntu 24.04 + Jazzy ([details](docs/en/driver-patches.md))
- `m2m2_slam_bridge.py` reads the map and pose from the M2M2's **on-board SLAM** and publishes them as `/map`, `/m2m2/pose` and TF `map → laser`, so the mapping result shows up in RViz2
- **Mind the power supply**: the M2M2 runs on 5 V and draws up to about 1.3 A. Powered from the OpenCR 5 V output it kept browning out and rebooting; a 5 V 2 A USB charger fixed it

![Map built by the M2M2 on-board SLAM (white = free, black = obstacle, grey = unknown)](images/m2m2_map.png)

## Documents
| Document | Contents |
|---|---|
| [README.en.md](README.en.md) | Hardware, wiring, install, launch and test results (this file) |
| [docs/en/driver-patches.md](docs/en/driver-patches.md) | The three fixes for opensw / opensw_ros on Ubuntu 24.04 + Jazzy |
| [docs/en/protocol.md](docs/en/protocol.md) | Notes on the M2M2 (Slamware) protocol, map format and web API |
| [docs/en/troubleshooting.md](docs/en/troubleshooting.md) | Troubleshooting: brown-out reboots, no connection, build failures, segmentation fault |
| [conversation.en.md](conversation.en.md) | Summary of the test session |
| [jetson.en.md](jetson.en.md) | Wiring, build and test log on a Jetson (aarch64) |

## Files
- `setup_workspace.sh`: creates `~/m2m2_ws`, clones the upstream drivers at pinned commits, applies the patches and builds
- `patches/opensw.patch`, `patches/opensw_ros.patch`: fixes to the upstream drivers
- `scripts/m2m2_slam_bridge.py`: publishes the M2M2 on-board SLAM map and pose to ROS 2
- `scripts/slamware_client.py`: minimal Python client for the Slamware protocol (pose, known area, map)
- `scripts/scan_check.py`: listens to `/scan` for 6 s and reports rate, point count, distances and the nearest obstacle per sector
- `scripts/render_map.py`: saves the current map, scan and pose as a PNG
- `rviz/m2m2.rviz`: RViz2 config (map, scan, pose, TF)
- `images/m2m2_map.png`: the map from the test

## Hardware and wiring
| Item | Details |
|---|---|
| Model | Slamtec Mapper 2 model 2 (M2M2), firmware `4.6.1-rtm` (2023-11-28) |
| Power | **5 V**, 650–1300 mA (not 12 V) |
| Interfaces | 100 Mbps Ethernet; also runs its own Wi-Fi access point `SLAMWARE-xxxxxx` |
| Default IP | `192.168.11.1` (runs a DHCP server on the Ethernet port) |
| Ports | 1445 (Slamware SDK), 80 (web management page), 22 (SSH) |

```
USB charger 5V 2A ──► M2M2 adapter board ◄── Ethernet ──► laptop Ethernet port (192.168.11.100)
```

> ⚠️ Do not power the M2M2 from the OpenCR DC5V output. In testing it rebooted every time, a few seconds after the SLAM service started and the laser head spun up to full speed. See [troubleshooting](docs/en/troubleshooting.md#m2m2-keeps-dropping-off-the-network).

## Laptop network setup
Create a static-IP wired connection with NetworkManager:
```bash
nmcli con add type ethernet ifname enp3s0 con-name mapper \
  ipv4.method manual ipv4.addresses 192.168.11.100/24 ipv6.method link-local
nmcli con up mapper
ping 192.168.11.1
```
Replace `enp3s0` with your wired interface name (`ip -br link`).

## Install and build
```bash
sudo apt install libasio-dev
git clone https://github.com/asdfut/slamtec-m2m2-lidar.git
cd slamtec-m2m2-lidar
./setup_workspace.sh          # builds in ~/m2m2_ws, about 3–5 minutes
```
The other dependencies (`libeigen3-dev`, `libspdlog-dev`, `libopencv-dev`, `nlohmann-json3-dev`, `libassimp-dev`) usually come with a Jazzy desktop install.

## Launch
Run `export ROS_DOMAIN_ID=99` in all three terminals first.

```bash
# 1. Laser driver → /scan (frame: laser)
source ~/m2m2_ws/install/setup.bash
ros2 run opensw_ros laser_driver --ros-args -p host:=192.168.11.1 -p frame_id:=laser -p rate:=10.0

# 2. On-board SLAM bridge → /map, /m2m2/pose, TF map → laser
source /opt/ros/jazzy/setup.bash
python3 scripts/m2m2_slam_bridge.py

# 3. RViz2
rviz2 -d rviz/m2m2.rviz
```
- `laser_driver` defaults `frame_id` to `imu`; set it to `laser`
- `rate` defaults to 50, but the M2M2 only turns about 10 times a second; use 10 to avoid publishing repeated scans
- Carry the M2M2 around slowly and the map in RViz2 grows as you go

## Test results
Measured with `scripts/scan_check.py` (M2M2 sitting on a desk):

| Item | Result |
|---|---|
| Real scan rate | about 10.8 Hz (at the driver's 50 Hz, about 4 in 5 messages repeat the previous revolution) |
| Points per revolution | 853, angular resolution 0.422° |
| Angle range | −179.7° to +179.9° |
| Valid points | 554 (65%) |
| Distance | 0.24 to 5.58 m, median 1.18 m |
| Network stability | no drops for 2+ minutes once powered from a USB charger |
| On-board SLAM map | about 4 × 7.6 m, 0.05 m per cell |

## License
- Scripts and docs in this repo: free to use
- `patches/` modify [hatchbed](https://github.com/hatchbed)'s opensw and opensw_ros, which are BSD 3-Clause licensed upstream
