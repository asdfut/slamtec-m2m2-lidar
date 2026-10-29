# 測試過程紀錄（摘要）

**中文** | [English](conversation.en.md) | [回到 README](README.md)

2026-10-29，在筆電（Ubuntu 24.04、ROS 2 Jazzy）上和 Claude Code 一起測試 Slamtec Mapper M2M2。

## 1. 找不到裝置
- 一開始 USB、有線網路、Wi-Fi 都看不到 M2M2
- 照片顯示網路線另一頭沒插在 M2M2 的轉接板上，接好後有線網路連上（100 Mbps）

## 2. 設定網路
- 筆電上原本有一個為 Jetson 建的網路分享設定（`10.42.0.1`）自動接管了有線網路孔
- 新增固定 IP 設定 `mapper`（`192.168.11.100/24`），M2M2 在 `192.168.11.1` 回應 ping
- 掃連接埠：22（SSH）、80（網頁管理）、1445（Slamware）開著
- 從網頁 API 讀到型號 M2M2、韌體 `4.6.1-rtm`

## 3. 一直斷線重開
- 連線撐 6 秒、19 秒、47 秒就斷，最後完全沒恢復
- 一開始誤以為 M2M2 要 12V，查了官方規格後更正為 **5V、650–1300 mA**
- 照片確認 M2M2 接在 OpenCR 的 DC5V 輸出上，電壓正確
- 再觀察一次：開機 → 36 秒後 SLAM 服務啟動 → 5 秒後斷線，判斷是雷射頭全速轉動時電流不夠
- 改用 USB 充電頭供電，連續 2 分鐘以上沒斷

## 4. 編譯驅動
- Slamtec 官方 ROS SDK 是閉源而且只有 ROS 1，改用 hatchbed 的 opensw / opensw_ros
- 遇到的問題依序是：記憶體不足（16 核心並行）→ asio 1.28 沒有 `deadline_timer` → hatchbed_common 參數 API 改了
- Claude Code 的安全機制會擋下編譯、執行外部下載的程式碼：編譯時用 `/permissions` 加上 `Bash(colcon build:*)`，驅動則由使用者自己在終端機執行

## 5. 驅動當掉
- `laser_driver` 一連線就 Segmentation fault
- 用 `gdb` 取得 backtrace，定位在 `RosLogSink` 把空指標傳給 `/rosout`，修正後正常

## 6. 掃描測試
- 實際約 10.8 Hz，853 點／圈，360°，有效點 65%，距離 0.24–5.58 m
- 驅動用 50 Hz 發布時有 4/5 是重複的一圈，建議 `rate:=10`

## 7. RViz2 與 SLAM
- 發現 M2M2 的 Slamware 協定可以直接拿到內建 SLAM 的位置（`getpose`）和地圖（`getmapdata`）
- 寫了 `slamware_client.py`（協定用戶端）和 `m2m2_slam_bridge.py`（發布 `/map`、`/m2m2/pose`、TF）
- 地圖格子的值是有號整數（0 未知、正數空地、負數障礙物），RViz2 顯示正確
- 拿著 M2M2 走動時，連線一度斷掉（應該是線或電源被碰到），M2M2 自己重開後恢復
