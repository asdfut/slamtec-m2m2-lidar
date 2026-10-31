# Intel NUC 測試紀錄（2026-10-31）

**中文** | [English](nuc.en.md) | [回到 README](README.md)

環境：Intel NUC8i7BEH（x86_64，記憶體 7.6 GB）、Ubuntu 24.04、ROS 2 Jazzy。M2M2 用網路線接 NUC 的有線網路孔 `eno1`，OpenCR 用 USB 接 NUC，**M2M2 由 OpenCR 的 5V 輸出供電**（OpenCR 接 DC 變壓器）。

## 1. 偵測
- **OpenCR**：出現在 `/dev/ttyACM0`（`0483:5740`，ROBOTIS OpenCR Virtual ComPort）。要加進 `dialout` 群組並重新登入才能開
- **M2M2**：一開始 `eno1` 一直是 `NO-CARRIER`，Wi-Fi 也掃不到 `SLAMWARE-xxxxxx`。量 OpenCR 5V 輸出是 4.86 V（空載）

## 2. 供電：問題是插頭接觸，不是電流
- 插頭沒壓緊時：`12:00:10 Link is Up` → `12:00:22 Link is Down`，之後完全沒恢復
- 把電源插頭**壓緊**插進 M2M2 後：`12:10:51 Link is Up`，一路穩定到 `12:29:03`（**約 18 分鐘**），中間 SLAM 服務啟動、雷射頭全速轉動都沒斷
- `12:29:03` 拿著 M2M2 走動建圖時斷了一次，8 秒後重開，應該是插頭又被碰鬆
- 結論：OpenCR 的 5V 輸出供得起 M2M2。2026-10-29 和 Jetson 測試時「接 OpenCR 會斷電」的現象，其實是插頭接觸不良（當時換成 USB 充電頭時也是一直壓著插頭）。要拿著走動的話，插頭要用熱熔膠、束帶等固定

## 3. 網路
- 不用手動設固定 IP：M2M2 的 DHCP 分給 NUC `192.168.11.200`
- `192.168.11.1` ping 0.8 ms、0% 掉包，80、1445 埠開著

## 4. 編譯
- 缺 `nlohmann-json3-dev`（`opensw` 的 `find_package(nlohmann_json REQUIRED)` 需要），Jazzy 桌面版沒有預裝，要 `sudo apt install nlohmann-json3-dev`。`libasio-dev` 已經有了
- `setup_workspace.sh` 4 個套件共 3 分 44 秒，只有 CMake 版本棄用警告

## 5. 掃描測試
`scripts/scan_check.py` 結果（M2M2 放在桌上）：

| 項目 | 結果 |
|---|---|
| 掃描頻率 | 10.2 Hz |
| 每圈點數 | 860 點，有效 718 點（83%） |
| 角度範圍 | −179.7° ～ +180.0°，0.419°／點 |
| 距離 | 0.74 ～ 6.17 m，中位數 1.47 m |

## 6. SLAM 橋接與 RViz2
- `m2m2_slam_bridge.py` 正常發布 `/map`（約 0.5 Hz）、`/m2m2/pose`、TF `map → laser`
- RViz2 顯示地圖 146 × 98 格（約 7.3 × 4.9 m）。啟動時出現一次 TF `extrapolation into the future` 和已知的 GLSL 錯誤，都不影響顯示

## 7. 斷線後 `laser_driver` 當掉
- M2M2 斷電重開時，`laser_driver` 會一直 `Socket timed out` 重試，最後丟出 `std::system_error: write: Broken pipe` 直接結束（exit code 250），不會自己恢復
- `m2m2_slam_bridge.py` 會自己重連，不受影響
- 暫時解法：等 1445 重新打開（開機後約 35 秒）再重開 `laser_driver`。M2M2 重開機後內建 SLAM 地圖會清空
