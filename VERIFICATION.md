# 本机安装与验收记录

记录日期：2026-11-12（Asia/Shanghai）。工作区：`/home/liyh/Documents/deepseek-harness/default-workspace/uav-sim`。

## 实际安装环境

| 项目 | 已验证配置 |
| --- | --- |
| 宿主 | Ubuntu 22.04.5 LTS，原有 ROS 2 Humble |
| GPU | 两张 NVIDIA GeForce RTX 3090，驱动 580.178.04 |
| 仿真运行环境 | Docker，Ubuntu 22.04 / Gazebo Harmonic，Gazebo Sim 8.15.0 |
| 镜像 | `uav-sim:jammy-harmonic`，ID 见 `dependencies/environment.json` |
| PX4 | v1.17.0，`d6f12ad1c4f70ad3230afd7d86e971421e02fef4` |
| 官方模型 | PX4 嵌套子模块，`b6127f4ec20de867e215fb5f78ae88b80f371909` |
| Python 控制环境 | 宿主独立 `.venv`，Python 3.10.12，mavsdk-grpc 4.0.5 |
| Python 构建环境 | 容器独立 `.venv-build`，依赖固定于 `dependencies/px4-python-resolved.txt` |
| MAVLink | PX4 本地 UDP 14580 → MAVSDK UDP 14540；SDK gRPC TCP 50051 |

仿真依赖安装在 Docker 镜像中；宿主新增 NVIDIA Container Toolkit，并配置 Docker NVIDIA runtime。既有 ROS 2 Humble 保留，当前控制示例不要求 ROS 桥接。全部 PX4 嵌套子模块已初始化，`make -j4 px4_sitl` 编译成功，包含 Gazebo 桥接及插件。

## 动态飞行验收

以下为真实 PX4 SITL–Gazebo–MAVSDK 闭环运行结果，均成功返回。每项飞行结束后都等待落地与自动上锁。

| 检查 | 官方 default，无界面 | obstacle_course，NVIDIA GUI |
| --- | --- | --- |
| PX4 与世界启动 | 通过 | 通过 |
| MAVSDK 连接、Global/Home 健康及位置遥测 | 通过 | 通过 |
| 起飞至 3 m、悬停 2 s、降落与自动上锁 | 通过 | 通过 |
| Offboard 零速度预发送、进入模式、方形速度航迹、降落 | 通过 | 通过 |
| Mission 上传、进度到达 5/5、降落 | 通过 | 通过 |

默认世界的实际执行命令：

```bash
./scripts/start.sh --scene default
uv run --locked python -m control.telemetry --duration 5
uv run --locked python -m control.takeoff_land --altitude 3 --hover 2
uv run --locked python -m control.offboard_demo
uv run --locked python -m control.mission_demo
./scripts/stop.sh
```

障碍世界的实际执行命令：

```bash
./scripts/smoke_test.sh --scene obstacle_course --full --gui
```

原始日志保留在本机 `logs/`（不进入 Git）：

- `default-telemetry.log`、`default-takeoff-land.log`、`default-offboard.log`、`default-mission.log`。
- 默认世界进程日志：`20261112-052526-977246/`。
- 障碍世界完整验收输出：`obstacle-full-smoke.log` 与 `smoke-obstacle_course-20261112-053023.log`，包含 `PASS: scene=obstacle_course full=1`。
- 障碍世界进程日志：`20261112-053014-631664/`。

运行时 `gz model --list` 查询确认障碍世界含 `ground_plane`、`building_east`、`building_west`、`building_north`、`pillar_1`、`pillar_2`、`pillar_3`、`x500_0`。静态世界检查确认地面、建筑及柱体均有碰撞体。

## 图形与进程生命周期

- `docker run --gpus all ... nvidia-smi` 成功，容器能看到两张 RTX 3090。
- 携带用户 X11 认证的容器 `glxinfo -B` 显示 direct rendering 为 Yes，OpenGL vendor 为 NVIDIA，renderer 为 NVIDIA GeForce RTX 3090，OpenGL 4.6 / 驱动 580.178.04。
- 障碍世界 GUI 服务 `/gui/move_to` 已发现服务提供方；GUI 在完整飞行验收期间保持运行。
- 将启动超时设置为 0.01 秒并启用 `--cleanup-on-failure`，确认失败退出且本次容器被移除，日志仍保留。
- `nan`、`inf`、负数及零超时参数在 Docker 操作前被拒绝。
- 在无飞行的独立测试会话内终止 Gazebo server launcher，确认监控逻辑自动结束仿真容器；随后正常清理测试会话。
- `doctor.sh` 在完整主机权限上下文检查为 0 failures、0 warnings；最终输出保存在 `logs/doctor-final.log`。
- Bash 脚本语法及 Python 3.10 AST 语法检查通过；资源清单为空时资源下载器正常结束，无额外地图下载。

原始上游模型日志可能出现 `gz_frame_id` SDF 扩展提示，MAVSDK 日志可能出现重复 ACK 的 `not-existing command: 176` 提示；上述实际飞行命令均正常完成并落地上锁。

## 使用范围

当前验收覆盖 X500、官方默认世界和本地基础障碍世界。已验证图形界面启动和 NVIDIA 硬件 OpenGL 链路，尚未测量复杂地图帧率。后续增加相机、雷达、大型第三方资源或 ROS 感知/规划时，需要继续验证其兼容性、传感器数据和实时性能。障碍世界本身不提供自动避障；当前不包括无 GPS 室内导航。

大型资源下载、解压和场景注册按 `assets/README.md` 管理。系统包、Python 包及源码提交快照分别保存在 `dependencies/`、根目录锁文件与 Git submodule 中。
