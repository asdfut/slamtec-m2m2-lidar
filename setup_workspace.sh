#!/usr/bin/env bash
# Build the M2M2 ROS 2 driver workspace (Ubuntu 24.04 + ROS 2 Jazzy).
# Clones the upstream hatchbed repos at the tested commits, applies this repo's patches and builds.
# Usage: ./setup_workspace.sh [workspace_dir]   (default: ~/m2m2_ws)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
WS="${1:-$HOME/m2m2_ws}"

clone() {  # name url commit
    local dir="$WS/src/$1"
    if [ ! -d "$dir" ]; then
        git clone -q "$2" "$dir"
    fi
    git -C "$dir" checkout -q "$3"
}

mkdir -p "$WS/src"
clone asyncapi_gencpp https://github.com/hatchbed/asyncapi_gencpp.git fe77883cdc9a648ff95bb08a47c9decced393452
clone hatchbed_common https://github.com/hatchbed/hatchbed_common.git e31b2b6251ed7cc0de0b04207c60d84b6ed028a4
clone opensw          https://github.com/hatchbed/opensw.git          0125bc6a6dbbfcc2c37bf498a8a7a88b88567c01
clone opensw_ros      https://github.com/hatchbed/opensw_ros.git      4c0fcad1daa180728291451fa97e38cc37492f10

for p in opensw opensw_ros; do
    if git -C "$WS/src/$p" apply --check "$REPO_DIR/patches/$p.patch" 2>/dev/null; then
        git -C "$WS/src/$p" apply "$REPO_DIR/patches/$p.patch"
        echo "applied patches/$p.patch"
    else
        echo "patches/$p.patch already applied (or does not apply), skipping"
    fi
done

# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
cd "$WS"
# Limit parallelism: a full-speed build runs out of memory on a 7-8 GB machine.
MAKEFLAGS=-j2 colcon build --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release
echo "Done. Run: source $WS/install/setup.bash"
