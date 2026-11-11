#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v docker >/dev/null || { echo 'Docker 未安装'; exit 1; }
command -v uv >/dev/null || { echo '需要 uv：https://docs.astral.sh/uv/'; exit 1; }
mkdir -p logs .cache/container-home
uv sync --locked
if [[ ! -f third_party/PX4-Autopilot/CMakeLists.txt ]]; then
    git submodule update --init third_party/PX4-Autopilot
fi
# Git 默认使用主仓库已记录的提交，不追踪远程分支。
git -C third_party/PX4-Autopilot submodule update --init --recursive
# 兼容未安装 buildx 的 Docker。
docker build -t uav-sim:jammy-harmonic -f docker/Dockerfile .
echo '环境准备完成，执行 ./scripts/build.sh'
