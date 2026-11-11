# 依赖记录

- `environment.json` 记录本次实际构建使用的 PX4 / Gazebo 模型提交、Docker 镜像 ID、运行与构建 Python 版本。
- `system-packages.txt` 是已构建仿真镜像的 Debian 包版本快照，便于审查和排查版本差异。
- `px4-python-resolved.txt` 固定 PX4 构建虚拟环境的全部 Python 包，构建脚本优先使用它。该环境使用容器 Python 3.10，与宿主控制环境分开。
- 根目录的 `pyproject.toml` / `uv.lock` 管理宿主 MAVSDK 控制环境；正常安装使用 `uv sync --locked`。
- PX4 的 Git submodule 及全部嵌套子模块固定源码，`assets/manifest.yaml` 管理额外大型资源的版本、来源、许可证和 SHA256。当前没有额外下载项。

仿真镜像不依赖宿主 ROS，项目也没有自动安装 ROS 桥接组件。`ros_ws/src/` 预留给后续需求。

Dockerfile 固定 Ubuntu 22.04 和 Gazebo Harmonic 系列；在线 apt 软件源会更新。包版本快照用于记录已验证环境，不等同于永久保存对应二进制包。严格归档时应另外保存当前镜像，例如使用 `docker save uav-sim:jammy-harmonic -o uav-sim-image.tar`，并记录归档的 SHA256；归档不应进入源码仓库。

更新应显式进行：更新子模块提交、重新解析 Python 依赖或重建系统镜像之后，重新运行 `scripts/doctor.sh` 与两个场景的 `scripts/smoke_test.sh --full`，再更新环境记录。
