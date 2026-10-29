# M2M2（Slamware）通訊協定與網頁 API 筆記

**中文** | [English](../en/protocol.md) | [回到 README](../../README.md)

以下是從 `opensw` 的原始碼和實際測試整理出來的，不是 Slamtec 官方文件。`scripts/slamware_client.py` 就是照這些格式寫的。

## TCP 1445：Slamware 指令
- 傳輸：TCP，每則訊息是一段 JSON，結尾加分隔字串 `"\n\r\n\r\n"`
- 請求：
  ```json
  {"command": "getpose", "request_id": 12345}
  {"command": "getmapdata", "request_id": 12346, "args": {...}}
  ```
- 回應：同樣以 `"\n\r\n\r\n"` 結尾，內容放在 `result`
- 可以同時開多條連線（測試時 `laser_driver` 和 `m2m2_slam_bridge.py` 各開一條）

| 指令 | 用途 | `result` 重點欄位 |
|---|---|---|
| `getpose` | 內建 SLAM 的位置 | `x`、`y`、`z`、`yaw`、`pitch`、`roll`（公尺、弧度） |
| `getlaserscan` | 一圈雷射 | `laser_points`（base64 + RLE 二進位），以及掃描當下的 `x`、`y`、`yaw` |
| `getknownarea` | 地圖目前的範圍 | `min_x`、`min_y`、`max_x`、`max_y` |
| `getmapdata` | 地圖格子 | `dimension_x`、`dimension_y`、`real_x`、`real_y`、`resolution`、`map_data` |
| `getlocation` | 只有位置 | `x`、`y` |
| `getimuinrobotcoordinate` | IMU | 加速度、角速度 |
| `getrobothealth`、`getsystemresource`、`getsdpversion` | 狀態、版本 | |

`getknownarea` 和 `getmapdata` 的 `args`：
```json
{"type": 0, "kind": 0, "partially": false,
 "area": {"x": -2.45, "y": -6.35, "width": 4.0, "height": 7.6}}
```
- `type`：0 = 8 位元點陣圖
- `kind`：0 = 探索地圖（EXPLORERMAP）。其他值：5 costmap、30 SLAM map、40 local SLAM map

## 二進位資料：base64 + RLE
`map_data` 和 `laser_points` 都是 base64 編碼的 RLE 壓縮資料：
- 前 9 bytes 是標頭：3 bytes 簽章、`[3]` 哨兵值 1、`[4]` 哨兵值 2、`[5..8]` 解壓後大小（uint32，little-endian）
- 之後逐 byte 讀：
  - 遇到哨兵值 1 時，後面接 `count, value`，代表 `value` 重複 `count` 次
  - 如果 `count == 0` 且 `value == 哨兵值 2`，代表兩個哨兵值互換
  - 其他 byte 照抄

## 地圖格子的值
8 位元**有號**整數：

| 值 | 意思 | `/map`（OccupancyGrid） |
|---|---|---|
| 0 | 未知 | −1 |
| 1 ～ 127 | 空地（越大越確定） | 0 |
| −1 ～ −127（byte 129 ～ 255） | 障礙物 | 100 |

資料是一列一列存的（先 x 再 y），原點在 `real_x`、`real_y`，跟 ROS 的 OccupancyGrid 一樣，可以直接轉。測試時的地圖約 4 × 7.6 m，82 × 154 格，0.05 m／格。

## TCP 80：網頁管理 API
網頁「Slamtec Device Management」背後的 API 在 `/service` 下，不需要登入就能讀：
```bash
curl http://192.168.11.1/service/system/product
# {"model":"M2M2","name":"Slamtec Mapper 2 model 2","network":{"ip":"192.168.11.1","mode":"AP(2.4G)",...},"type":"mapper"}

curl http://192.168.11.1/service/system/firmware_upgrade/version
# {"VERSION":"4.6.1-rtm-mapper-E1M2-20231128", ...}

curl http://192.168.11.1/service/system/network/interfaces
# eth0：DHCP Server，192.168.11.1/24；wlan0：AP，同一個 IP
```
其他路徑（從網頁的 JavaScript 找到，未全部測試）：`/system/lidar/info`、`/system/networking`、`/system/restart`、`/system/firmware_update` 等。修改設定或重開機的 API 需要登入，沒有試。
