# Jetson 測試紀錄（2026-10-30）

**中文** | [English](jetson.en.md) | [回到 README](README.md)

環境：NVIDIA Jetson（L4T，核心 6.8.12-tegra，aarch64，記憶體 7.3 GB）、Ubuntu 24.04、ROS 2 Jazzy。M2M2 用網路線接 Jetson 的有線網路孔 `enP8p1s0`，OpenCR 用 USB 接 Jetson。

## 1. 接線與偵測
- **OpenCR**：一開始 USB 上看不到，換一條能傳資料的 USB 線、插在 USB-A 埠後出現 `/dev/ttyACM0`（`0483:5740`，ROBOTIS OpenCR Virtual ComPort）
- 使用者要加進 `dialout` 群組（`sudo usermod -aG dialout $USER`，重新登入）才能開 `/dev/ttyACM0`
- **M2M2**：接在 OpenCR 的 5V 輸出時雷達完全不亮；改用 USB 充電頭供電，壓緊接頭後網路孔 link up
- Jetson 不用手動設 IP：M2M2 的 DHCP 分給 Jetson `192.168.11.200`，`192.168.11.1` ping 得到，1445、80 埠開著

## 2. 編譯
- `setup_workspace.sh` 原本在 `source /opt/ros/jazzy/setup.bash` 這行失敗（`AMENT_TRACE_SETUP_FILES: unbound variable`），因為腳本開了 `set -u`。已修正為 source 前後暫時關閉 `-u`
- 需要先 `sudo apt install libasio-dev nlohmann-json3-dev`（Jetson 上沒有預裝）
- 4 個套件共 10 分 17 秒，其中 `hatchbed_common` 會一起編測試程式，就花了 7 分 34 秒

## 3. 掃描測試
- `rate:=10` 會讓驅動當掉：`parameter 'rate' has invalid type ... {double}, setting it to {integer} is not allowed`，要寫成 `rate:=10.0`（README 已修正）
- `scripts/scan_check.py` 結果：

| 項目 | 結果 |
|---|---|
| 掃描頻率 | 10.2 Hz |
| 每圈點數 | 857 點，有效 650 點（76%） |
| 角度範圍 | −179.8° ～ +179.8°，0.42°／點 |
| 距離 | 0.32 ～ 6.17 m，中位數 1.04 m |

## 4. SLAM 橋接與 RViz2
- `m2m2_slam_bridge.py` 正常發布 `/map`、`/m2m2/pose`、TF `map → laser`
- RViz2 直接開在 Jetson 桌面（`DISPLAY=:1`）
- 地圖約 5 × 8 m（102 × 159 格，0.05 m／格）：

![Jetson 上的 M2M2 內建 SLAM 地圖](images/m2m2_map_jetson.png)

## 5. 雷達斷電重開後驅動卡住
- 充電頭接觸不良讓 M2M2 斷電重開（`enP8p1s0` link down → 13 秒後 link up）
- `m2m2_slam_bridge.py` 會自己重新連上，但 `laser_driver` 停在 `Connecting to [192.168.11.1:1445] ...` 不會恢復，要重新啟動驅動
- 供電線要固定好
