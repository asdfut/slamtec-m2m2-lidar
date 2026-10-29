# opensw / opensw_ros 在 Ubuntu 24.04 + ROS 2 Jazzy 上的修正

**中文** | [English](../en/driver-patches.md) | [回到 README](../../README.md)

Slamtec 官方的 ROS SDK 是閉源的，而且只支援 ROS 1。這裡用的是 [hatchbed](https://github.com/hatchbed) 的開放原始碼驅動：

| 套件 | 用途 | 測試用的版本 |
|---|---|---|
| [opensw](https://github.com/hatchbed/opensw) | Slamware 通訊程式庫（C++） | `0125bc6`（2022-10-11） |
| [opensw_ros](https://github.com/hatchbed/opensw_ros) | ROS 2 驅動：`laser_driver`、`imu_driver` | `4c0fcad`（`ros2` 分支，2022-10-11） |
| [hatchbed_common](https://github.com/hatchbed/hatchbed_common) | 參數與工具 | `e31b2b6`（2026-10-19） |
| [asyncapi_gencpp](https://github.com/hatchbed/asyncapi_gencpp) | 從協定定義產生 C++ 訊息類別 | `fe77883`（2022-07-29） |

`setup_workspace.sh` 會下載這幾個版本並套用 `patches/` 裡的修正。

## 1. opensw：asio 1.28 沒有 `deadline_timer`
**錯誤**
```
client.h:205:11: error: 'deadline_timer' in namespace 'asio' does not name a type
client.cpp:73:111: error: 'error' is not a member of 'asio::placeholders'
```
**原因**：Ubuntu 24.04 的 `libasio-dev` 是 1.28，獨立版 asio 只有在有 Boost.DateTime 時才提供 `deadline_timer`。

**修正**（`patches/opensw.patch`）：
- `asio::deadline_timer` → `asio::steady_timer`
- `expires_from_now(boost::posix_time::milliseconds(n))` → `expires_after(std::chrono::milliseconds(n))`
- `expires_at() <= deadline_timer::traits_type::now()` → `expiry() <= steady_timer::clock_type::now()`
- `expires_at(boost::posix_time::pos_infin)` → `expires_at(steady_timer::time_point::max())`
- `boost::bind(&Client::handleConnect, this, asio::placeholders::error)` → lambda
- 移除 `boost/bind.hpp`、`boost/date_time` 的 include

逾時的行為和原本一樣（連線、收資料預設 500 ms）。

## 2. opensw_ros：新版 hatchbed_common 的參數 API
**錯誤**
```
laser_driver.cpp:56:36: error: conversion from 'hatchbed_common::StringParameter' to non-scalar type 'std::string' requested
laser_driver.cpp:63:12: error: 'class hatchbed_common::ParamHandler' has no member named 'register_param'
```
**原因**：`opensw_ros` 是照 2022 年的 `hatchbed_common` 寫的，新版的 `param()` 改成回傳參數物件，要呼叫 `.declare()` 才會真的宣告；`register_param` 也被移除了。2022 年的 `hatchbed_common` 版本同樣沒有 `register_param`，所以改驅動比較直接。

**修正**（`patches/opensw_ros.patch`）：
```cpp
// 靜態參數
std::string host = params.param("host", std::string("192.168.11.11"), "Host to connect to").declare().value();

// 動態參數（原本的 register_param）
params.param(&min_range, "min_range", 0.0, "Min sensor range in meters").min(0.0).max(10.0).dynamic().declare();
```

## 3. opensw_ros：一連線就 Segmentation fault
**現象**：印出 `Connecting to [192.168.11.1:1445] ...` 後馬上當掉。用 gdb 看到：
```
#0  __strlen_avx2 ()
#1  rcl_logging_rosout_output_handler () from librcl.so
#5  rcutils_log ()
#6  opensw_ros::RosLogSink<std::mutex>::sink_it_(...)
#9  opensw::Client::connect(...)
```
**原因**：`RosLogSink` 把 spdlog 訊息的 `source.funcname`、`source.filename` 直接當成 `rcutils_log_location_t` 傳給 ROS。spdlog 沒有記錄來源位置時這兩個是空指標，Jazzy 的 `/rosout` 會對它們呼叫 `strlen()`。

**修正**：空指標時改傳空字串。原本的 `static` 也拿掉了，否則之後每則訊息都會沿用第一則訊息的來源位置。

## 4. 編譯時記憶體不足
```
c++: fatal error: Killed signal terminated program cc1plus
```
16 核心同時編譯會吃光 7 GB 記憶體。要限制並行數：
```bash
MAKEFLAGS=-j2 colcon build --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release
```

## 其他注意事項
- `laser_driver` 的 `frame_id` 預設值寫成 `imu`，啟動時要加 `-p frame_id:=laser`
- `host` 預設是 `192.168.11.11`，M2M2 預設是 `192.168.11.1`
- `rate` 是驅動向 M2M2 要資料的頻率，不是雷射轉速。預設 50 Hz 時大部分是重複的一圈，建議設 10
