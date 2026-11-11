#!/usr/bin/env bash
set -euo pipefail
# Host-side NVIDIA runtime setup. Does not install or replace the GPU driver.
command -v nvidia-smi >/dev/null
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
if ! command -v nvidia-ctk >/dev/null; then
    tmpdir="$(mktemp -d)"
    curl --retry 3 -fsSL https://nvidia.github.io/libnvidia-container/gpgkey -o "$tmpdir/key"
    gpg --batch --yes --dearmor -o "$tmpdir/keyring.gpg" "$tmpdir/key"
    curl --retry 3 -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list -o "$tmpdir/repo.list"
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' "$tmpdir/repo.list" > "$tmpdir/signed.list"
    sudo install -m 644 "$tmpdir/keyring.gpg" /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    sudo install -m 644 "$tmpdir/signed.list" /etc/apt/sources.list.d/nvidia-container-toolkit.list
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
fi
sudo nvidia-ctk runtime configure --runtime=docker
# Refuse to interrupt other running containers.
if [[ -n "$(docker ps -q)" ]]; then
    echo 'Docker 有正在运行的容器；配置已写入，请在方便时自行重启 Docker，然后验证 --gpus all。'
    exit 1
fi
sudo systemctl restart docker
docker run --rm --gpus all uav-sim:jammy-harmonic nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
