# Test session log (summary)

[中文](conversation.md) | **English** | [Back to README](README.en.md)

2026-10-29: testing a Slamtec Mapper M2M2 on a laptop (Ubuntu 24.04, ROS 2 Jazzy) together with Claude Code.

## 1. Device not found
- At first the M2M2 didn't show up over USB, wired Ethernet or Wi-Fi
- A photo showed the far end of the Ethernet cable wasn't plugged into the M2M2 adapter board; once it was, the wired link came up (100 Mbps)

## 2. Network setup
- A connection-sharing profile created earlier for a Jetson (`10.42.0.1`) grabbed the wired port automatically
- Added a static profile `mapper` (`192.168.11.100/24`); the M2M2 answered ping at `192.168.11.1`
- Open ports: 22 (SSH), 80 (web management), 1445 (Slamware)
- The web API reported model M2M2, firmware `4.6.1-rtm`

## 3. Repeated drop-outs
- The link stayed up for 6 s, 19 s, then 47 s, and finally didn't come back
- The first assumption that the M2M2 needs 12 V was wrong; the official spec says **5 V, 650–1300 mA**
- A photo confirmed the M2M2 was on the OpenCR DC5V output, so the voltage was right
- Watching again: boot → SLAM service up after 36 s → link down 5 s later. Diagnosis: not enough current once the laser head spins at full speed
- Powered from a USB charger instead, it stayed up for 2+ minutes

## 4. Building the driver
- Slamtec's official ROS SDK is closed source and ROS 1 only, so hatchbed's opensw / opensw_ros were used instead
- Problems in order: out of memory (16 parallel jobs) → asio 1.28 has no `deadline_timer` → hatchbed_common changed its parameter API
- Claude Code's safety checks block building and running code downloaded from outside. For the build, `/permissions` added `Bash(colcon build:*)`; the driver itself was run by the user in their own terminal

## 5. Driver crash
- `laser_driver` segfaulted right after connecting
- A `gdb` backtrace pointed at `RosLogSink` passing null pointers to `/rosout`; fixed

## 6. Scan test
- About 10.8 Hz in practice, 853 points per revolution, 360°, 65% valid points, distances 0.24–5.58 m
- At the driver's 50 Hz, 4 in 5 messages repeat the previous revolution; `rate:=10` is recommended

## 7. RViz2 and SLAM
- The Slamware protocol exposes the on-board SLAM pose (`getpose`) and map (`getmapdata`) directly
- Wrote `slamware_client.py` (protocol client) and `m2m2_slam_bridge.py` (publishes `/map`, `/m2m2/pose`, TF)
- Map cells are signed values (0 unknown, positive free, negative obstacle); RViz2 shows the map correctly
- While carrying the M2M2 around, the link dropped once (probably a bumped cable or power lead); the M2M2 rebooted and came back on its own
