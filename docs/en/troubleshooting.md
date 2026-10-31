# Troubleshooting

[中文](../zh/troubleshooting.md) | **English** | [Back to README](../../README.en.md)

## The laptop can't see the M2M2
**Symptom**: the wired port has no link (`cat /sys/class/net/enp3s0/carrier` prints `0`) and there's no `SLAMWARE-xxxxxx` Wi-Fi network.

**Check**:
1. Is the M2M2 powered? The laser head should spin and the LED should be on
2. The Ethernet cable must go into the RJ45 port on the M2M2 **adapter board**, not just into the laptop. In testing, the far end of the cable was lying unplugged on the desk
3. The M2M2 is not a USB device, so it never shows up in `lsusb`

## Link is up but ping or port 1445 fails
- The laptop's wired interface must be on `192.168.11.x`. The M2M2's DHCP server usually hands out `192.168.11.200`; if not, use the `mapper` connection in the README
- If another profile grabs the wired port automatically (for example a connection-sharing profile), stop it from autoconnecting:
  ```bash
  nmcli con modify <other-profile> connection.autoconnect no
  nmcli con up mapper
  ```
- After power-on it takes about **35 s** before the SLAM service (1445) opens. Until then only ping and the web page (80) respond

## M2M2 keeps dropping off the network
**Symptom**: the link keeps going up and down. The kernel log looks like this:
```
23:24:54  Link is Up      ← M2M2 boots
23:25:30  1445 opens      ← SLAM service starts, laser spins up to full speed
23:25:35  Link is Down    ← reboots 5 s later
```
It dropped every time, a few seconds after the SLAM service started; the previous cycle lasted 47 s (boot plus startup).

**Cause**: a bad contact at the power plug. The M2M2 runs on 5 V at 650–1300 mA and peaks when the laser head is at full speed, which is when a loose plug is most likely to drop out.

At first this looked like the OpenCR DC5V output running out of current, and switching to a USB charger seemed to fix it, but the plug was being held in the whole time. On 2026-10-31, back on OpenCR 5 V on the NUC with only the plug pressed home, it ran for about 18 minutes ([nuc.en.md](../../nuc.en.md)).

**Fix**:
1. Push the power plug all the way in and secure it with hot glue, a cable tie or tape, especially if you carry the M2M2 around
2. The OpenCR 5 V output is fine; a 5 V 2 A+ USB charger works too
3. How to tell: with the plug pressed home, the link should survive the SLAM service start (about 35 s after power-on)

> ⚠️ The M2M2 is a 5 V device. Never connect it to the OpenCR 12 V output.

## Build failures
| Error | Cause | Fix |
|---|---|---|
| `Killed signal terminated program cc1plus` | Out of memory | `MAKEFLAGS=-j2 colcon build --executor sequential` |
| `'deadline_timer' in namespace 'asio' does not name a type` | asio 1.28 | Apply `patches/opensw.patch` |
| `has no member named 'register_param'` | Newer hatchbed_common API | Apply `patches/opensw_ros.patch` |
| `asio.hpp` not found | asio not installed | `sudo apt install libasio-dev` |
| `Could not find a package configuration file provided by "nlohmann_json"` | nlohmann json not installed | `sudo apt install nlohmann-json3-dev` |

See [driver-patches.md](driver-patches.md) for details.

## `laser_driver` segfaults right after connecting
This is the `/rosout` null-pointer bug; apply `patches/opensw_ros.patch`. To debug it yourself:
```bash
ros2 run --prefix 'gdb -batch -ex run -ex bt --args' opensw_ros laser_driver \
  --ros-args -p host:=192.168.11.1 -p frame_id:=laser -p verbose:=true
```

## laser_driver dies after the M2M2 reboots
**Symptom**: when the M2M2 loses power and reboots, `laser_driver` keeps printing `Socket timed out`, then
```
terminate called after throwing an instance of 'std::system_error'
  what():  write: Broken pipe
[ros2run]: Aborted
```
and exits without recovering. `m2m2_slam_bridge.py` reconnects on its own.

**Fix**: wait for port 1445 to reopen (about 35 s after boot), then restart `laser_driver`:
```bash
until timeout 1 bash -c '</dev/tcp/192.168.11.1/1445' 2>/dev/null; do sleep 2; done
ros2 run opensw_ros laser_driver --ros-args -p host:=192.168.11.1 -p frame_id:=laser -p rate:=10.0
```
The on-board SLAM map is cleared when the M2M2 reboots.

## RViz2 shader error at startup
```
[ERROR] [rviz2]: rviz/glsl120/indexed_8bit_image.vert ...
active samplers with a different type refer to the same texture image unit
```
This appeared during testing but the map still rendered fine, so it can be ignored. If the map really doesn't show, use `scripts/render_map.py` to save it as an image instead.

## Interfering with the robot's ROS 2
All testing here used `ROS_DOMAIN_ID=99`. If the robot uses another domain (for example 30), neither side sees the other's topics.
