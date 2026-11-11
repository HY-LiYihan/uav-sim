# uav-sim

本地 PX4 SITL + Gazebo Harmonic 仿真工程，通过 MAVSDK/MAVLink 控制 X500，使用场景配置切换世界。Gazebo 与 PX4 在 Docker 中运行，Python 控制示例在宿主项目虚拟环境中运行。默认无界面；图形界面按需启用。

## 组件与版本

| 组件 | 配置与职责 |
| --- | --- |
| 仿真容器 | Ubuntu 22.04，镜像 `uav-sim:jammy-harmonic` |
| Gazebo | Harmonic，当前构建中的 Gazebo Sim 8.15.0 |
| 飞控 | PX4 SITL v1.17.0，固定提交 `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`；桥接模块随 PX4 构建 |
| 飞机与官方世界 | PX4 的嵌套 `PX4-gazebo-models` submodule |
| Python | >=3.10，依赖由 `pyproject.toml` 和 `uv.lock` 管理 |
| 控制 SDK | `mavsdk-grpc` 4.0.5，导入 `mavsdk_grpc`；附带 `mavsdk_server` |
| ROS | 核心飞行示例不依赖 ROS；`ros_ws/src` 预留扩展 |
| QGroundControl | 可选，用于检查参数、模式、遥测和手动接管 |

Gazebo 是独立仿真器。宿主安装 ROS 不代表已经安装了 Gazebo；也不需要为了本工程在宿主重新安装一套 ROS。当前 Docker 路线将仿真依赖与宿主 ROS 隔离；宿主 Humble 环境不会自动成为容器中的 ROS–Gazebo 桥接环境。如果以后要加入 ROS 2 感知或规划，需要另外锁定兼容的 ROS、`ros_gz`、消息和桥接版本。

## 前置条件

- Linux 宿主；本工程的 Docker 工作流使用 host network。
- 能访问 Docker daemon 的 Docker CLI；Git；uv。构建过程需要下载系统包、源码和 Python 包。
- 可用磁盘空间：建议预留至少 30–50 GB，实际随编译缓存、镜像和场景资源增长。
- 图形模式需要可用的显示会话、显卡驱动及容器访问能力。软件渲染可用于排查，但不保证复杂地图帧率。
- UDP 14540 用于 MAVSDK，UDP 14550 通常用于 QGroundControl；本地 TCP 50051 用于 SDK 内部 gRPC。一次只运行一个默认控制客户端。

不要因为设备在受限沙箱里不可见，就判断主机没有 GPU。应在实际运行 Docker 的主机权限上下文中确认 `/dev/dri`、`nvidia-smi`、X11 和容器设备访问。当前主机已通过 NVIDIA Container Toolkit 配置与容器内设备检查，两张 RTX 3090 均可供容器使用；这不等同于 GUI 帧率已经通过验收。

新机器需要配置 NVIDIA 容器运行时才执行：

```bash
./scripts/setup_gpu.sh
```

该脚本要求宿主已有可用 NVIDIA 驱动，会通过 sudo 安装/配置 NVIDIA Container Toolkit，可能需要重启 Docker；发现其他运行中容器时会退出并要求另行安排重启。已有可用运行时的主机不必反复运行。默认无界面仿真不要求每次执行这一步。

## 获取、构建和启动

从本工程实际发布地址克隆，并初始化固定提交的 submodule：

```bash
git clone --recurse-submodules <本工程仓库地址> uav-sim
cd uav-sim
```

已有工作副本可以使用：

```bash
git submodule update --init --recursive
```

日常部署不要使用 `git submodule update --remote`，它会将子模块跟随上游分支移动。首次获取网络受限时，可按网络环境设置 `HTTPS_PROXY` 等代理变量；不要把个人代理凭据提交到仓库。

```bash
./scripts/bootstrap.sh
./scripts/doctor.sh
./scripts/build.sh
./scripts/start.sh --scene default
```

`doctor.sh` 是只读检查：核对 Docker daemon、镜像、PX4 源码与模型、虚拟环境、默认端口、显示和设备条件。阻塞项显示 `[FAIL]` 并返回非零；图形不足、端口已被现有客户端占用或尚未编译等情况显示 `[WARN]`，需要按启动目标判断。它不会启动容器、安装依赖或验证飞行。首次编译前出现“PX4 SITL 尚未构建”的提示属于预期。

如果首次配置后尚未生成虚拟环境，可执行：

```bash
uv sync --locked
```

常用运行入口：

```bash
# 默认不启动 Gazebo GUI
./scripts/start.sh --scene default

# 加载本地障碍场景
./scripts/start.sh --scene obstacle_course

# 需要本机显示、认证及设备支持
./scripts/start.sh --scene obstacle_course --gui

# 按需尝试软件渲染；性能取决于场景和主机
./scripts/start.sh --scene obstacle_course --gui --software-rendering

./scripts/status.sh
./scripts/stop.sh
```

切换世界前先停止当前项目仿真。`stop.sh` 的范围仅限本项目容器，不应停止其他 Docker 工作负载。具体可用参数以各脚本 `--help` 为准。

## MAVSDK 控制

仿真运行后，在宿主另一个终端进入仓库根目录：

```bash
uv run python -m control.telemetry --duration 20
uv run python -m control.takeoff_land
uv run python -m control.offboard_demo
uv run python -m control.mission_demo
```

默认地址为 `udpin://0.0.0.0:14540`。容器使用 host network，PX4 的 MAVLink SDK 数据发送到宿主回环地址上的 UDP 14540；MAVSDK 监听该端口。仅开放或监听端口不能证明 PX4 的发送目标已经配置正确，应同时检查 PX4 的 MAVLink 状态和接收端。

| 示例 | 行为 |
| --- | --- |
| `telemetry` | 等待连接和全局/Home 位置健康，定时打印位置，不解锁 |
| `takeoff_land` | 解锁、升至默认 5 m、悬停、降落，等待落地及自动上锁 |
| `offboard_demo` | 起飞后先发送零速度设定值，再进入 Offboard，执行约 3 m 方形航迹后降落 |
| `mission_demo` | 使用真实 Mission 接口上传约 8 m 方形航点任务，起飞、执行并在结束后降落 |

示例通用选项：

```bash
uv run python -m control.takeoff_land --help
uv run python -m control.takeoff_land \
  --address udpin://0.0.0.0:14540 \
  --timeout 60 --landing-timeout 90 --altitude 5 --hover 5
```

连接、健康和起飞等步骤由 `--timeout` 分别限制；任务和 Offboard 执行由 `--flight-timeout` 限制；落地和自动上锁分别由 `--landing-timeout` 限制。超时错误会标出正在等待的步骤。

飞行异常及单次 Ctrl-C 会尝试切换至降落并等待落地、自动上锁。反复中断、强制结束进程或失去通信可能阻止清理完成；出现清理失败提示时，检查 QGroundControl 中的实际飞行状态。控制脚本应先正常结束，再停止仿真容器。

SDK 包名称需要与代码一致：这里使用的是 `mavsdk-grpc`，不是当前具有另一套 API 的原生 `mavsdk` 包。不要将不同教程中的安装命令和导入方式混用。

## 自动冒烟测试

从没有运行本项目仿真的状态开始：

```bash
./scripts/smoke_test.sh --scene default
./scripts/smoke_test.sh --scene obstacle_course --full
# 按需附加 --gui 或 --software-rendering
```

测试启动所选世界，先执行 5 秒遥测，再完成 3 m 起飞、2 秒悬停和降落。`--full` 在此基础上再执行 Offboard 与 Mission 示例（两者默认高度为 5 m）。控制示例串行运行，等待落地和自动上锁后再进入下一项；启动成功后，无论后续测试通过或失败都会尝试停止仿真。

控制输出保存到 `logs/smoke-<scene>-<timestamp>.log`；仿真进程日志保存在该次启动对应的 `logs/<timestamp>/`。冒烟测试使用 `--cleanup-on-failure`，启动失败会清理本次创建的容器，不会停止已有会话。手动运行 `start.sh` 时，启动失败默认保留容器供 `status.sh` 排查，也可显式加入该选项。冒烟测试会实际驱动模拟飞行器，测试成功的范围仅限选择的场景与选项。

## 场景、坐标与资源

- `scenes/default.yaml` 指向 PX4 固定版本的官方默认世界。
- `scenes/obstacle_course.yaml` 指向本地 `worlds/obstacle_course.sdf`，SDF 世界名为 `obstacle_course`。
- 障碍世界使用本地几何体，不依赖在线 Fuel 资源：地面、三栋建筑、三根柱体都有碰撞。中央 x/y 各 +/-15 m 保持空旷，默认出生点为 `[0, 0, 0.3]`。
- PX4 负责生成 X500，世界文件不重复嵌入飞机模型。
- Gazebo 世界采用 ENU（东、北、上）；MAVSDK 本地控制采用 NED（北、东、下）。场景出生偏航单位为弧度，MAVSDK 示例偏航单位为度。

示例从默认出生点运行，采用已知空旷区域内的小范围轨迹。障碍物不会自动赋予 PX4 避障能力。GPS 被仿真以支持基础控制；真实无 GPS 室内导航不在当前验收范围内。

小型模型放在 `models/`，大型资源按来源、许可证、版本和 SHA256 管理；详见 `assets/README.md`。

```bash
./scripts/fetch_assets.sh
```

资源下载器读取 `assets/manifest.yaml`，将下载保存到 `assets/cache/` 并校验 SHA256。清单当前为空，因此命令不会下载额外地图；官方飞机和世界由 PX4 子模块提供。下载器不自动解压，压缩包需要按资源说明手动解压、配置搜索路径并完成地图验收。导入外部地图还需要校验碰撞、材质、比例、出生点、传感器可见性和性能。

## 工程布局与依赖更新

```text
third_party/PX4-Autopilot/  固定提交的飞控及其嵌套模型依赖
control/                   MAVSDK 程序与共享生命周期逻辑
scenes/                    世界、出生点和端口配置
worlds/ models/            自建场景与模型
assets/                    资源来源与管理说明
scripts/                   配置、构建、启停与诊断入口
docker/                    仿真镜像定义
ros_ws/src/                可选 ROS 扩展
pyproject.toml uv.lock     Python 依赖声明与解析锁
```

版本复现由多个层面共同完成：Git submodule 固定源码提交，`uv.lock` 固定 Python 依赖及校验，容器定义固定系统与 Gazebo 系列。仅使用镜像标签或在线 apt 源并不保证未来得到逐字节一致的系统环境；需要严格复现时，还应归档镜像摘要和可用的软件源/镜像。

有意更新 Python 依赖时才运行 `uv lock`，随后检查锁文件差异并重新验证控制接口。正常部署使用 `uv sync --locked`。不要在运行启动阶段自动更新 submodule 或下载最新地图。

## 验证状态与限制

已完成 PX4 v1.17.0（`d6f12ad1c4f70ad3230afd7d86e971421e02fef4`）的实际编译，模型子模块已完整初始化；仿真镜像包含 Ubuntu 22.04 / Gazebo Sim 8.15.0。NVIDIA Container Toolkit 已安装并验证两张 RTX 3090 可用于容器；完整主机权限上下文下 `doctor.sh` 检查为 0 个失败、0 个警告。

宿主 uv 依赖锁定与同步已成功，实际安装的 `mavsdk-grpc` 4.0.5 可以导入全部控制模块，全部使用到的 SDK 方法及构造接口与代码一致。

2026-11-12 已完成以下实际仿真飞行验证：

| 场景与运行方式 | 遥测 | 3 m 起降、落地上锁 | Offboard 方形航迹 | Mission 5/5 后降落 |
| --- | --- | --- | --- | --- |
| 官方默认世界，无界面 | 通过 | 通过 | 通过 | 通过 |
| 本地障碍世界，NVIDIA GPU 图形界面 | 通过 | 通过 | 通过 | 通过 |

障碍世界运行时实体查询确认地面、三栋建筑、三根柱体和 `x500_0` 均存在。容器 X11 认证、GUI 服务和 OpenGL 链路已验证，OpenGL renderer 为 NVIDIA GeForce RTX 3090。启动超时自动清理及无效超时值拒绝也已验证。详细命令与日志位置见 `VERIFICATION.md`。

当前验收覆盖上述两个世界与 X500 的基础控制。GUI 可启动与硬件渲染已通过，尚未对大型复杂地图做帧率基准测试；后续加入相机、雷达或第三方场景后，应重新验证传感器、渲染和实时性能。

## 上游来源

- PX4：https://github.com/PX4/PX4-Autopilot
- 官方 Gazebo 模型：https://github.com/PX4/PX4-gazebo-models
- Gazebo Harmonic：https://gazebosim.org/docs/harmonic/
- MAVSDK gRPC Python：https://github.com/mavlink/MAVSDK-Python
- 发布包：https://pypi.org/project/mavsdk-grpc/4.0.5/

本工程的源码来源以官方仓库为准。如维护者为本地下载加速临时使用 Git 镜像，它只承担传输作用，不替换上游来源或版本依据；最终提交和子模块地址应保持可核验。
