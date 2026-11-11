#!/usr/bin/env bash
# Read-only environment checks. Never starts containers or changes the host.
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
IMAGE="${UAV_SIM_IMAGE:-uav-sim:jammy-harmonic}"
FAILURES=0
WARNINGS=0

ok() { printf '[OK] %s\n' "$*"; }
info() { printf '[INFO] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; WARNINGS=$((WARNINGS + 1)); }
fail() { printf '[FAIL] %s\n' "$*"; FAILURES=$((FAILURES + 1)); }

if [[ $# -gt 0 ]]; then
    if [[ $# -eq 1 && ( "$1" == '--help' || "$1" == '-h' ) ]]; then
        printf 'Usage: %s\nRead-only checks; FAIL exits 1, WARN alone exits 0. UAV_SIM_IMAGE overrides image name.\n' "$0"
        exit 0
    fi
    printf 'Unknown arguments. Usage: %s\n' "$0" >&2
    exit 2
fi

info "Project: ${PROJECT_ROOT}"
info "Host: $(uname -s) $(uname -m); ROS_DISTRO=${ROS_DISTRO:-not sourced}"
if [[ -r /etc/os-release ]]; then
    # os-release is a system-owned shell assignment file.
    HOST_PRETTY="$(. /etc/os-release; printf '%s' "${PRETTY_NAME:-unknown}")"
    info "Host OS: ${HOST_PRETTY}"
fi
info 'Gazebo runs in the Docker image; host ROS/Gazebo is optional.'

if command -v git >/dev/null 2>&1; then ok "$(git --version)"; else fail 'git is missing'; fi
if command -v uv >/dev/null 2>&1; then ok "$(uv --version)"; else fail 'uv is missing (needed for lock/sync and control examples)'; fi

if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        ok 'Docker daemon is accessible'
        if docker image inspect "$IMAGE" >/dev/null 2>&1; then
            ok "Docker image exists: ${IMAGE}"
            docker image inspect --format '       Image ID: {{.Id}}' "$IMAGE"
        else
            fail "Docker image is missing: ${IMAGE}; run ./scripts/bootstrap.sh"
        fi
        if ! docker compose version >/dev/null 2>&1; then
            warn 'Docker Compose plugin is absent; required only if using Compose directly'
        fi
    else
        fail 'Docker daemon is unavailable or inaccessible; inspect daemon status and user permissions'
    fi
else
    fail 'docker is missing'
fi

PX4_ROOT="${PROJECT_ROOT}/third_party/PX4-Autopilot"
if [[ -f "${PX4_ROOT}/CMakeLists.txt" && -f "${PX4_ROOT}/Makefile" ]]; then
    ok 'PX4 source exists'
    if command -v git >/dev/null 2>&1 && git -C "$PX4_ROOT" rev-parse --verify HEAD >/dev/null 2>&1; then
        info "PX4 commit: $(git -C "$PX4_ROOT" rev-parse HEAD)"
        info "PX4 description: $(git -C "$PX4_ROOT" describe --tags --always 2>/dev/null || true)"
    fi
else
    fail 'PX4 source is absent/incomplete; finish bootstrap/submodule initialization'
fi
if [[ -f "${PX4_ROOT}/Tools/simulation/gz/worlds/default.sdf" && -d "${PX4_ROOT}/Tools/simulation/gz/models/x500" ]]; then
    ok 'Official Gazebo default world and X500 assets exist'
else
    fail 'PX4 Gazebo model submodule is absent/incomplete'
fi
if [[ -x "${PX4_ROOT}/build/px4_sitl_default/bin/px4" ]]; then
    ok 'PX4 SITL executable exists'
else
    warn 'PX4 SITL is not built yet; run ./scripts/build.sh before starting'
fi
if [[ -f "${PROJECT_ROOT}/uv.lock" ]]; then ok 'Python lockfile exists'; else fail 'uv.lock is missing'; fi

VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
if [[ -x "$VENV_PYTHON" ]]; then
    if "$VENV_PYTHON" -B - <<'PY'
import importlib
import os
from pathlib import Path
import sys
from importlib.metadata import version
assert sys.version_info >= (3, 10), 'Python 3.10 or newer is required'
import yaml
import mavsdk_grpc
from mavsdk_grpc.mission import MissionItem, MissionPlan
from mavsdk_grpc.offboard import VelocityNedYaw
server = Path(mavsdk_grpc.__file__).parent / 'bin' / 'mavsdk_server'
assert server.is_file() and os.access(server, os.X_OK), f'Missing/non-executable MAVSDK server: {server}'
print(f'       Python {sys.version.split()[0]}, mavsdk-grpc {version("mavsdk-grpc")}, PyYAML {version("pyyaml")}')
print(f'       MAVSDK server: {server}')
PY
    then
        ok 'Python virtual environment and published SDK APIs are available'
    else
        fail 'Python virtual environment is incomplete; run uv sync --locked'
    fi
else
    fail 'Project .venv is missing; run uv sync --locked'
fi

PORT_PYTHON=''
if [[ -x "$VENV_PYTHON" ]]; then PORT_PYTHON="$VENV_PYTHON";
elif command -v python3 >/dev/null 2>&1; then PORT_PYTHON="$(command -v python3)"; fi
if [[ -n "$PORT_PYTHON" ]]; then
    if "$PORT_PYTHON" -B - <<'PY'
import socket
busy = False
for protocol, number, purpose in [('udp', 14540, 'MAVSDK'), ('udp', 14550, 'QGroundControl'), ('tcp', 50051, 'MAVSDK gRPC')]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if protocol == 'udp' else socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', number))
        print(f'       {protocol.upper()} {number} ({purpose}): available')
    except OSError as exc:
        busy = True
        print(f'       {protocol.upper()} {number} ({purpose}): cannot bind ({exc})')
    finally:
        sock.close()
raise SystemExit(1 if busy else 0)
PY
    then
        ok 'Default SDK/GCS ports are available at check time'
    else
        warn 'One or more ports cannot be bound; may be an existing client, GCS, or permissions. Inspect before launching another client.'
    fi
else
    warn 'No host Python interpreter available to check port bindings'
fi

if [[ -d /dev/dri ]]; then
    info 'Host /dev/dri exists; container device access and renderer still need verification'
else
    warn '/dev/dri is not visible in this execution context; recheck outside any sandbox before concluding host graphics are absent'
fi
if command -v nvidia-smi >/dev/null 2>&1; then
    if nvidia-smi -L >/dev/null 2>&1; then
        info 'NVIDIA GPU is visible; this does not verify Docker GPU runtime access'
    else
        warn 'nvidia-smi cannot access a GPU in this execution context; sandbox device filtering may affect this result'
    fi
fi
if [[ -n "${DISPLAY:-}" ]]; then
    info "DISPLAY=${DISPLAY}; X11 authentication/container access is not yet verified"
    if [[ ! -d /tmp/.X11-unix ]]; then warn 'X11 socket directory /tmp/.X11-unix is absent'; fi
elif [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
    warn 'Only Wayland display detected; current --gui workflow needs working X11/XWayland access'
else
    warn 'No display environment detected; use the default headless mode'
fi
info 'Simulation execution and GUI frame rate are not tested by doctor.'
printf '\nChecks finished: %d failure(s), %d warning(s).\n' "$FAILURES" "$WARNINGS"
if [[ "$FAILURES" -gt 0 ]]; then exit 1; fi
