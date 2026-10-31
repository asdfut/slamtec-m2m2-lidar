# Intel NUC test log (2026-10-31)

[中文](nuc.md) | **English** | [Back to README](README.en.md)

Environment: Intel NUC8i7BEH (x86_64, 7.6 GB RAM), Ubuntu 24.04, ROS 2 Jazzy. The M2M2 is cabled to the NUC's wired port `eno1`, the OpenCR is on USB, and **the M2M2 is powered from the OpenCR 5 V output** (OpenCR on a DC adapter).

## 1. Detection
- **OpenCR**: shows up as `/dev/ttyACM0` (`0483:5740`, ROBOTIS OpenCR Virtual ComPort). The user has to join the `dialout` group and log in again to open it
- **M2M2**: at first `eno1` stayed at `NO-CARRIER` and no `SLAMWARE-xxxxxx` Wi-Fi was visible. The OpenCR 5 V output measured 4.86 V (no load)

## 2. Power: the problem is the plug, not the current
- Plug not pushed home: `12:00:10 Link is Up` → `12:00:22 Link is Down`, and it never came back
- With the power plug **pressed firmly** into the M2M2: `12:10:51 Link is Up`, stable until `12:29:03` (**about 18 minutes**), through SLAM service startup and the laser head at full speed
- At `12:29:03`, while carrying the M2M2 around to map, it dropped once and rebooted 8 s later, most likely because the plug got knocked loose again
- Conclusion: the OpenCR 5 V output can power the M2M2. The "drops out on OpenCR power" behaviour seen on 2026-10-29 and on the Jetson was really a bad plug contact (the plug was also being held in when the USB charger was used). If you carry the M2M2 around, fix the plug in place with hot glue, a cable tie or similar

## 3. Network
- No static IP needed: the M2M2's DHCP server gave the NUC `192.168.11.200`
- `192.168.11.1` answers ping in 0.8 ms with 0% loss; ports 80 and 1445 are open

## 4. Build
- `nlohmann-json3-dev` was missing (`opensw` has `find_package(nlohmann_json REQUIRED)`). It is not part of the Jazzy desktop install: `sudo apt install nlohmann-json3-dev`. `libasio-dev` was already present
- `setup_workspace.sh` built all 4 packages in 3 min 44 s, with only CMake deprecation warnings

## 5. Scan test
`scripts/scan_check.py` (M2M2 sitting on a desk):

| Item | Result |
|---|---|
| Scan rate | 10.2 Hz |
| Points per revolution | 860, 718 valid (83%) |
| Angle range | −179.7° to +180.0°, 0.419° per point |
| Distance | 0.74 to 6.17 m, median 1.47 m |

## 6. SLAM bridge and RViz2
- `m2m2_slam_bridge.py` publishes `/map` (about 0.5 Hz), `/m2m2/pose` and TF `map → laser`
- RViz2 shows a 146 × 98 cell map (about 7.3 × 4.9 m). At startup there was one TF `extrapolation into the future` error and the known GLSL error; neither affects the display

## 7. `laser_driver` dies after a disconnect
- When the M2M2 loses power and reboots, `laser_driver` retries with `Socket timed out` and then exits on `std::system_error: write: Broken pipe` (exit code 250). It does not recover by itself
- `m2m2_slam_bridge.py` reconnects on its own
- Workaround for now: wait for port 1445 to reopen (about 35 s after boot), then restart `laser_driver`. The on-board SLAM map is cleared when the M2M2 reboots
