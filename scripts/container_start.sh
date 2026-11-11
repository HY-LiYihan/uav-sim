#!/usr/bin/env bash
set -euo pipefail
cd /workspace/third_party/PX4-Autopilot/build/px4_sitl_default/rootfs
export GZ_SIM_RESOURCE_PATH="${GZ_SIM_RESOURCE_PATH:-}"
export GZ_SIM_SYSTEM_PLUGIN_PATH="${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
source ./gz_env.sh
export GZ_PARTITION="${GZ_PARTITION:?}"
export GZ_IP=127.0.0.1
export GZ_SIM_RESOURCE_PATH="/workspace/models:/workspace/worlds:${GZ_SIM_RESOURCE_PATH:-}"
export PX4_GZ_STANDALONE=1 PX4_SIM_MODEL=gz_x500 PX4_SYS_AUTOSTART=4001
export GZ_SIM_SERVER_CONFIG_PATH="${GZ_SIM_SERVER_CONFIG_PATH:-}"
# The startup script reads explicit PX4_GZ_MODELS from gz_env.sh.
gz sim -s -r "$SIM_WORLD_FILE" > "$SIM_LOG_DIR/gazebo.log" 2>&1 &
gz_pid=$!
gui_pid=''
if [[ "$SIM_GUI" == 1 ]]; then
    gz sim -g > "$SIM_LOG_DIR/gui.log" 2>&1 &
    gui_pid=$!
fi
cleanup() {
    trap - EXIT TERM INT
    [[ -z "$gui_pid" ]] || kill "$gui_pid" 2>/dev/null || true
    [[ -z "${px4_pid:-}" ]] || kill "$px4_pid" 2>/dev/null || true
    kill "$gz_pid" 2>/dev/null || true
}
trap cleanup EXIT TERM INT
# -d disables the interactive shell so Docker stdin is unnecessary.
(../bin/px4 -d 2>&1 | tee "$SIM_LOG_DIR/px4.log") &
px4_pid=$!
children=("$gz_pid" "$px4_pid")
[[ -z "$gui_pid" ]] || children+=("$gui_pid")
# A surviving PX4 process alone is insufficient if the world or GUI has crashed.
set +e
wait -n "${children[@]}"
result=$?
set -e
echo "A simulation component exited (status=$result); stopping the session."
[[ "$result" != 0 ]] || result=1
exit "$result"
