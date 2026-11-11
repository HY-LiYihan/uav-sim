#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p .cache/container-home logs
# 构建环境和 MAVSDK 运行环境分开，避免 PX4 的 Python 依赖相互影响。
docker run --rm --user "$(id -u):$(id -g)" \
    -e HOME=/workspace/.cache/container-home -e JOBS="${JOBS:-4}" \
    -v "$ROOT:/workspace" -w /workspace uav-sim:jammy-harmonic bash -euc '
    python3 -m venv .venv-build
    if [[ -s dependencies/px4-python-resolved.txt ]]; then
        .venv-build/bin/pip install -r dependencies/px4-python-resolved.txt
    else
        .venv-build/bin/pip install -r third_party/PX4-Autopilot/Tools/setup/requirements.txt
        .venv-build/bin/pip freeze --all > dependencies/px4-python-resolved.txt
    fi
    export PATH="/workspace/.venv-build/bin:$PATH"
    cd third_party/PX4-Autopilot
    make -j"$JOBS" px4_sitl
    '
