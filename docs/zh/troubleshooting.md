# 問題排解

**中文** | [English](../en/troubleshooting.md) | [回到 README](../../README.md)

## 筆電偵測不到 M2M2
**現象**：有線網路孔沒有連線（`cat /sys/class/net/enp3s0/carrier` 是 `0`），Wi-Fi 也看不到 `SLAMWARE-xxxxxx`。

**檢查**：
1. M2M2 有沒有通電：雷射頭在轉、指示燈亮
2. 網路線要接在 M2M2 **轉接板的 RJ45 孔**上，不是只接在筆電端。測試時就是網路線另一頭沒插，空放在桌上
3. M2M2 不是 USB 裝置，`lsusb` 看不到它是正常的

## 連上了但 ping 不到 / 連不到 1445
- 筆電的有線網路要在 `192.168.11.x` 網段（見 README 的 `mapper` 連線設定）
- 如果筆電上有其他會自動接管有線網路孔的設定（例如網路分享），先關掉自動連線：
  ```bash
  nmcli con modify <其他連線名稱> connection.autoconnect no
  nmcli con up mapper
  ```
- M2M2 開機後約 **35 秒** SLAM 服務（1445）才會開，在那之前只有 ping 和網頁（80）會通

## M2M2 一直斷線重開
**現象**：網路連線斷斷續續，系統紀錄像這樣：
```
23:24:54  Link is Up      ← M2M2 開機
23:25:30  1445 打開       ← SLAM 服務啟動，雷射頭全速轉動
23:25:35  Link is Down    ← 5 秒後斷電重開
```
每次都在 SLAM 服務啟動後幾秒斷線，前一次也是撐了 47 秒（開機 + 啟動）就斷。

**原因**：供電電流不夠。M2M2 是 5V、650–1300 mA，雷射頭全速轉動時耗電最大。測試時接在 OpenCR 的 DC5V 輸出（OpenCR 由 DC 變壓器供電），撐不住。

**解法**：給 M2M2 獨立的 5V 2A 以上電源（例如 USB 充電頭）。換了之後連續 2 分鐘以上都沒斷。

> ⚠️ M2M2 是 5V，不要接 OpenCR 的 12V 輸出。

## 編譯失敗
| 錯誤 | 原因 | 解法 |
|---|---|---|
| `Killed signal terminated program cc1plus` | 記憶體不足 | `MAKEFLAGS=-j2 colcon build --executor sequential` |
| `'deadline_timer' in namespace 'asio' does not name a type` | asio 1.28 | 套用 `patches/opensw.patch` |
| `has no member named 'register_param'` | hatchbed_common 新版 API | 套用 `patches/opensw_ros.patch` |
| 找不到 `asio.hpp` | 沒裝 asio | `sudo apt install libasio-dev` |

詳見 [driver-patches.md](driver-patches.md)。

## `laser_driver` 一連線就 Segmentation fault
`/rosout` 記錄的空指標問題，套用 `patches/opensw_ros.patch` 就好。自己除錯可以用：
```bash
ros2 run --prefix 'gdb -batch -ex run -ex bt --args' opensw_ros laser_driver \
  --ros-args -p host:=192.168.11.1 -p frame_id:=laser -p verbose:=true
```

## RViz2 啟動時出現著色器錯誤
```
[ERROR] [rviz2]: rviz/glsl120/indexed_8bit_image.vert ...
active samplers with a different type refer to the same texture image unit
```
測試時出現這個錯誤，但地圖還是正常顯示，可以忽略。如果地圖真的顯示不出來，可以改用 `scripts/render_map.py` 輸出成圖片。

## 機器人那邊的 ROS 2 被干擾
這裡的測試都用 `ROS_DOMAIN_ID=99`。機器人如果用別的 Domain（例如 30），兩邊不會互相看到 topic。
