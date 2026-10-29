# Notes on the M2M2 (Slamware) protocol and web API

[中文](../zh/protocol.md) | **English** | [Back to README](../../README.en.md)

Pieced together from the `opensw` source and from testing. This is not official Slamtec documentation. `scripts/slamware_client.py` follows these formats.

## TCP 1445: Slamware commands
- Transport: TCP. Each message is a JSON object followed by the delimiter `"\n\r\n\r\n"`
- Requests:
  ```json
  {"command": "getpose", "request_id": 12345}
  {"command": "getmapdata", "request_id": 12346, "args": {...}}
  ```
- Responses end with the same `"\n\r\n\r\n"`; the payload is in `result`
- Several connections can be open at once (in testing, `laser_driver` and `m2m2_slam_bridge.py` each held one)

| Command | Purpose | Key `result` fields |
|---|---|---|
| `getpose` | Pose from the on-board SLAM | `x`, `y`, `z`, `yaw`, `pitch`, `roll` (metres, radians) |
| `getlaserscan` | One laser revolution | `laser_points` (base64 + RLE binary), plus the pose at scan time `x`, `y`, `yaw` |
| `getknownarea` | Current map extents | `min_x`, `min_y`, `max_x`, `max_y` |
| `getmapdata` | Map cells | `dimension_x`, `dimension_y`, `real_x`, `real_y`, `resolution`, `map_data` |
| `getlocation` | Position only | `x`, `y` |
| `getimuinrobotcoordinate` | IMU | acceleration, angular velocity |
| `getrobothealth`, `getsystemresource`, `getsdpversion` | Status, version | |

`args` for `getknownarea` and `getmapdata`:
```json
{"type": 0, "kind": 0, "partially": false,
 "area": {"x": -2.45, "y": -6.35, "width": 4.0, "height": 7.6}}
```
- `type`: 0 = 8-bit bitmap
- `kind`: 0 = explorer map (EXPLORERMAP). Others: 5 costmap, 30 SLAM map, 40 local SLAM map

## Binary payloads: base64 + RLE
`map_data` and `laser_points` are base64-encoded, RLE-compressed bytes:
- A 9-byte header: 3-byte signature, `[3]` sentinel 1, `[4]` sentinel 2, `[5..8]` inflated size (uint32, little-endian)
- Then byte by byte:
  - On sentinel 1, the next two bytes are `count, value`: repeat `value` `count` times
  - If `count == 0` and `value == sentinel 2`, swap the two sentinels
  - Any other byte is copied as is

## Map cell values
Signed 8-bit integers:

| Value | Meaning | `/map` (OccupancyGrid) |
|---|---|---|
| 0 | Unknown | −1 |
| 1 to 127 | Free (higher = more certain) | 0 |
| −1 to −127 (bytes 129 to 255) | Obstacle | 100 |

Cells are stored row by row (x fastest, then y) with the origin at `real_x`, `real_y`, the same layout as a ROS OccupancyGrid, so the conversion is direct. The test map was about 4 × 7.6 m, 82 × 154 cells at 0.05 m.

## TCP 80: web management API
The API behind the "Slamtec Device Management" page lives under `/service`; read endpoints work without logging in:
```bash
curl http://192.168.11.1/service/system/product
# {"model":"M2M2","name":"Slamtec Mapper 2 model 2","network":{"ip":"192.168.11.1","mode":"AP(2.4G)",...},"type":"mapper"}

curl http://192.168.11.1/service/system/firmware_upgrade/version
# {"VERSION":"4.6.1-rtm-mapper-E1M2-20231128", ...}

curl http://192.168.11.1/service/system/network/interfaces
# eth0: DHCP server, 192.168.11.1/24; wlan0: access point, same IP
```
Other paths found in the page's JavaScript (not all tested): `/system/lidar/info`, `/system/networking`, `/system/restart`, `/system/firmware_update` and more. Endpoints that change settings or reboot need a login and were not tried.
