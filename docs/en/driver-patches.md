# Fixes for opensw / opensw_ros on Ubuntu 24.04 + ROS 2 Jazzy

[中文](../zh/driver-patches.md) | **English** | [Back to README](../../README.en.md)

Slamtec's official ROS SDK is closed source and supports ROS 1 only. This setup uses the open-source drivers from [hatchbed](https://github.com/hatchbed):

| Package | Purpose | Tested version |
|---|---|---|
| [opensw](https://github.com/hatchbed/opensw) | Slamware protocol client library (C++) | `0125bc6` (2022-10-11) |
| [opensw_ros](https://github.com/hatchbed/opensw_ros) | ROS 2 driver: `laser_driver`, `imu_driver` | `4c0fcad` (`ros2` branch, 2022-10-11) |
| [hatchbed_common](https://github.com/hatchbed/hatchbed_common) | Parameters and utilities | `e31b2b6` (2026-10-19) |
| [asyncapi_gencpp](https://github.com/hatchbed/asyncapi_gencpp) | Generates C++ message classes from the protocol spec | `fe77883` (2022-07-29) |

`setup_workspace.sh` checks out these versions and applies the fixes in `patches/`.

## 1. opensw: asio 1.28 has no `deadline_timer`
**Error**
```
client.h:205:11: error: 'deadline_timer' in namespace 'asio' does not name a type
client.cpp:73:111: error: 'error' is not a member of 'asio::placeholders'
```
**Cause**: Ubuntu 24.04 ships `libasio-dev` 1.28. Standalone asio only provides `deadline_timer` when Boost.DateTime is available.

**Fix** (`patches/opensw.patch`):
- `asio::deadline_timer` → `asio::steady_timer`
- `expires_from_now(boost::posix_time::milliseconds(n))` → `expires_after(std::chrono::milliseconds(n))`
- `expires_at() <= deadline_timer::traits_type::now()` → `expiry() <= steady_timer::clock_type::now()`
- `expires_at(boost::posix_time::pos_infin)` → `expires_at(steady_timer::time_point::max())`
- `boost::bind(&Client::handleConnect, this, asio::placeholders::error)` → a lambda
- Dropped the `boost/bind.hpp` and `boost/date_time` includes

Timeout behaviour is unchanged (500 ms by default for connect and receive).

## 2. opensw_ros: the newer hatchbed_common parameter API
**Error**
```
laser_driver.cpp:56:36: error: conversion from 'hatchbed_common::StringParameter' to non-scalar type 'std::string' requested
laser_driver.cpp:63:12: error: 'class hatchbed_common::ParamHandler' has no member named 'register_param'
```
**Cause**: `opensw_ros` was written against the 2022 `hatchbed_common`. Newer `param()` returns a parameter object that has to be `.declare()`d, and `register_param` is gone. The 2022 `hatchbed_common` doesn't have `register_param` either, so patching the driver was the simpler route.

**Fix** (`patches/opensw_ros.patch`):
```cpp
// static parameters
std::string host = params.param("host", std::string("192.168.11.11"), "Host to connect to").declare().value();

// dynamic parameters (formerly register_param)
params.param(&min_range, "min_range", 0.0, "Min sensor range in meters").min(0.0).max(10.0).dynamic().declare();
```

## 3. opensw_ros: segmentation fault right after connecting
**Symptom**: crashes immediately after `Connecting to [192.168.11.1:1445] ...`. gdb shows:
```
#0  __strlen_avx2 ()
#1  rcl_logging_rosout_output_handler () from librcl.so
#5  rcutils_log ()
#6  opensw_ros::RosLogSink<std::mutex>::sink_it_(...)
#9  opensw::Client::connect(...)
```
**Cause**: `RosLogSink` passes spdlog's `source.funcname` and `source.filename` straight into an `rcutils_log_location_t`. They are null when spdlog records no source location, and Jazzy's `/rosout` handler calls `strlen()` on them.

**Fix**: pass empty strings when they are null. The `static` qualifier is also gone; it made every later message reuse the first message's source location.

## 4. Out of memory while compiling
```
c++: fatal error: Killed signal terminated program cc1plus
```
Building on all 16 cores at once exhausts 7 GB of RAM. Limit parallelism:
```bash
MAKEFLAGS=-j2 colcon build --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release
```

## Other gotchas
- `laser_driver` defaults `frame_id` to `imu`; launch it with `-p frame_id:=laser`
- `host` defaults to `192.168.11.11`; the M2M2 default is `192.168.11.1`
- `rate` is how often the driver polls the M2M2, not the laser's spin rate. At the default 50 Hz most messages repeat the previous revolution; 10 is a better value
