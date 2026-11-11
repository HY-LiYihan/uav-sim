# 场景资源管理

当前 `obstacle_course` 由本地 SDF 几何体组成，无需 Fuel 下载或额外网格。官方 `default` 场景及 X500 使用固定在 PX4 子模块中的官方资源。飞机由 PX4 生成，不嵌入障碍世界。

## 放置资源

- 小型自建模型放到仓库 `models/`；SDF 世界放到 `worlds/`。
- 引用外部资源时，记录原始 URL、作者、许可证、固定提交/发布版本和 SHA256。
- 大型网格、纹理或压缩包使用独立缓存及下载清单；不要将数 GB 的二进制直接提交 Git。
- 启动环境需要将本地 `models/` 和 PX4 的模型目录加入 `GZ_SIM_RESOURCE_PATH`。避免依赖运行时下载最新资源。
- 新地图验收包括网格与纹理路径、米制比例、碰撞几何、出生点、传感器可见性和运行性能。视觉模型不会自动生成准确碰撞体。

## 按清单下载

从仓库根目录执行：

```bash
./scripts/fetch_assets.sh
```

脚本读取 `assets/manifest.yaml` 的 `resources` 列表。当前清单为空，官方 PX4 世界和飞机继续由固定提交的 Git 子模块管理，执行命令不会下载额外资源。

需要增加第三方地图时，清单条目格式如下；替换示例 URL 和校验值后才能使用：

```yaml
resources:
  - id: office-v1
    url: https://example.org/office-v1.tar.gz
    filename: office-v1.tar.gz
    sha256: <经过可信来源核对的64位十六进制SHA256>
    license: CC-BY-4.0
    source: https://example.org/office
```

下载器要求 HTTPS 下载地址、来源和许可证；文件名只能包含字母、数字、点、横线与下划线，并以字母或数字开头。文件保存在 `assets/cache/`。已有缓存会重新核验 SHA256；新下载只有通过校验后才替换目标文件，失败不会发布校验错误的文件。清单记录的 SHA256 必须提前来自可信发布来源。

下载器不自动解压，也不自动注册为可启动场景。压缩包需要按其许可和使用说明解压至指定资源目录，补充模型搜索路径与 `scenes/` 配置，并检查碰撞和性能。不要将大型缓存与归档文件提交 Git。

## 坐标和飞行范围

Gazebo 使用 ENU：x 东、y 北、z 上；MAVSDK Offboard 使用 NED：north 北、east 东、down 下。配置中位置单位为米，出生偏航单位为弧度；MAVSDK 示例偏航单位为度。

障碍场景中央 x/y 各 +/-15 m 保持空旷。建筑与柱体均含碰撞，演示默认在中央 5 m 高度飞行。Mission 演示根据连接时的真实位置建立约 8 m 的方形航线，Offboard 演示约 3 m。请从默认出生点开始运行这些示例；飞控不会因场景存在障碍物而自动避障。

## 控制示例

从仓库根目录执行，一次仅运行一个控制客户端，避免争用 UDP 14540 和 MAVSDK gRPC 50051。

```bash
uv run python -m control.telemetry --duration 20
uv run python -m control.takeoff_land
uv run python -m control.offboard_demo
uv run python -m control.mission_demo
```

默认连接 `udpin://0.0.0.0:14540`。可使用 `--address`、`--timeout`、`--flight-timeout`、`--landing-timeout` 指定连接和等待参数。`--timeout` 分别限制连接、健康及起飞等步骤，`--flight-timeout` 限制 Offboard/任务执行，`--landing-timeout` 分别限制落地和自动上锁等待。

示例使用发布的 `mavsdk-grpc` 4.x API，导入名 `mavsdk_grpc`；与当前 PyPI 上原生 `mavsdk` 包的 API 不同。健康检查要求全局位置及 Home 可用。飞行异常和一次 Ctrl-C 会尝试请求降落并等待落地、自动上锁；通信中断或强制终止时不能保证命令送达，应在 QGroundControl 检查实际状态。持续多次中断会打断清理。

## 上游参考

- PX4 官方世界：https://github.com/PX4/PX4-gazebo-models/blob/main/worlds/default.sdf
- 发布 API：https://github.com/mavlink/MAVSDK-Python/tree/4.0.5
- 发布包：https://pypi.org/project/mavsdk-grpc/4.0.5/

当前障碍世界使用 PX4 官方世界的 0.004 s 步长、250 Hz 更新设置及地理参考；显式配置 Harmonic 的物理、用户命令、场景广播、IMU、磁力计、气压、导航卫星和渲染传感器系统。图形和传感器渲染能力需由宿主或容器环境提供；XML 解析通过不等于 Gazebo 动态验收通过。
