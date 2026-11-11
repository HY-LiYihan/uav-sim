# 可载入 uav-sim 的开源地图 / 场景调研

日期：2026-11-12  
目标工程：PX4 SITL + Gazebo Harmonic（gz-sim 8.15）+ X500  
结论范围：能在当前 `scenes/` + `worlds/` + `GZ_SIM_RESOURCE_PATH` 机制下作为**世界地图**载入的资源；不是 QGroundControl 的 2D 底图。

## 结论摘要

首选 **OpenRobotics 的 KSQL San Carlos Airport（CC-BY 4.0）**：约 2.9 km × 2.8 km 的真实机场 + 周边建筑，压缩包 26 MB、解压 54 MB，静态网格带碰撞，不需要 Gazebo 插件。注意它的 `model.sdf` 仍写绝对 Fuel URI，必须先改写成 `model://` 才能断网加载；改写后断网加载 0 错误。它比 Baylands 小一个数量级，又比 Sonoma 更像无人机任务场景。

Sonoma Raceway（CC0）曾作为最轻的候选评估（8.5 MB 压缩、14 MB 解压、加载 0 错误），但已按当前需求从工程中移除；当前保留的是 KSQL 与 Baylands 两个场景。

如果要“大范围自然地形”，**Baylands（CC-BY 4.0）** 最大最真实，PX4 已经自带对应世界；但它 151 MB 压缩、393 MB 解压，且模型仍使用旧版 OGRE 材质脚本和绝对 Fuel URL，离线化前需要改写，不能算开箱即用。

如果要“任意真实地点”，用 **gazebo_terrain_generator（BSD-3-Clause）** 生成 SDF 1.9 世界；它强依赖 Mapbox token，且高程图碰撞要求 DART/bullet，与本项目当前的 ODE 物理配置不同，需要单独验收。

如果要“开源城市几何”，用 **OSM2World（MIT）** 把 OSM 导出为 glTF/OBJ，再进 Gazebo；Gazebo 支持 glTF/glb，但坐标轴、比例、材质和 ODbL 署名要自己处理。

不建议直接引入：SubT 世界（Fortress 时代插件，Harmonic 中找不到 `libignition-gazebo-*`）、`gazebo_models_worlds_collection`（GPL-3.0 + Gazebo Classic 写法）、AWS RoboMaker 世界（已归档、许可不清）、terraforge-gazebo（无许可证）、AirSim/FlightGoggles/Isaac Sim（不同引擎）。

## 1. 筛选条件

当前项目的约束不是“能不能打开 SDF”，而是以下几条同时成立：

1. **Harmonic 兼容**：`gz-sim 8.15`，SDF 1.9 最稳；旧 SDF 可以解析，但旧插件名、OGRE `.material` 脚本、Gazebo Classic 的 `GAZEBO_MODEL_PATH` 语义都可能失效。
2. **可离线复现**：项目要求资源有来源、许可证、固定版本和 SHA256，启动阶段不下载最新资源。Fuel 资源必须先落地，不能只写一个 `https://fuel...` include。
3. **PX4 可用**：世界要有 `spherical_coordinates`（GPS/EKF 需要）、给 X500 留出净空出生点、地面/建筑有碰撞。
4. **许可可再分发**：优先 CC0 / CC-BY / Apache-2.0 / BSD；避免 CC-BY-NC-ND（禁止商用和衍生）和许可不明。
5. **性能可控**：大网格 + trimesh 碰撞会拖慢物理和渲染；RTX 3090 能渲染不等于实时因子能保持 1.0。

## 2. 候选对比

| 优先级 | 资源 | 类型 | 许可 | 压缩 / 解压体积 | 实测结果 | 适用场景 |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | [KSQL San Carlos Airport](https://fuel.gazebosim.org/1.0/OpenRobotics/models/ksql_airport) | 室外机场 + 周边建筑 | CC-BY 4.0 | 26 MB / 54 MB | 断网 + 本地 URI 改写后 0 错误 | 起降、进近、巡检、相机/雷达 |
| — | [Sonoma Raceway](https://fuel.gazebosim.org/1.0/OpenRobotics/models/Sonoma%20Raceway) | 室外赛道 | CC0 1.0 | 8.5 MB / 14 MB | 已移除（未保留） | 仅保留评估记录 |
| P2 | [Baylands](https://fuel.gazebosim.org/1.0/OpenRobotics/models/baylands) | 大范围湿地/机场 | CC-BY 4.0 | 151 MB / 393 MB | 断网 + 本地 URI 改写后 0 错误，2 类材质脚本警告（共 4 条） | 大范围自然场景 |
| P3 | [Depot](https://fuel.gazebosim.org/1.0/OpenRobotics/models/Depot) | 室内仓库 | CC-BY 4.0 | 82 MB | 静态检查：SDF 1.6 + 旧插件名 + OGRE 脚本 | 室内巡检（需迁移） |
| P4 | [SubT Urban/Cave](https://fuel.gazebosim.org/1.0/OpenRobotics/worlds) | 城市/洞穴 | CC-BY 4.0 | 世界 0.1–27 MB，模型另计 | 插件 `libignition-gazebo-wind-effects-system.so` 在 Harmonic 中不存在 | 地下/城市搜救（需迁移） |
| P5 | [gazebo_terrain_generator](https://github.com/saiaravind19/gazebo_terrain_generator) | 生成器 | BSD-3-Clause | 工具 | 未在本项目实测 | 任意真实地点地形 |
| P6 | [OSM2World](https://github.com/tordanik/OSM2World) | 生成器 | MIT | 工具 | 未在本项目实测 | OSM 城市 → glTF/OBJ |

> 体积为 Fuel 元数据中的压缩包大小 / 本地解压后 `du` 大小；“实测”是在 `uav-sim:jammy-harmonic` 镜像中执行 `gz sim -s -r -v 4 --iterations 60` 的服务端加载 + 60 步物理，不含 GUI 渲染、相机传感器和 PX4 起飞验证。

## 3. 分项说明

### 3.1 KSQL San Carlos Airport（首选）

**是什么**：OpenRobotics 发布的 San Carlos Airport（KSQL，加州）模型，包含机场跑道、滑行道、建筑和周边建筑（模型网格命名为 `map_5_osm_buildings`）。地形网格约 2.9 km × 2.8 km，高程 0–65 m；建筑网格约 3 km 范围。

**为什么适合本项目**：

- 纯静态 DAE 网格，`model.sdf` 只有 visual + collision，没有 Gazebo 系统插件，不依赖 PX4 之外的运行时。
- 场景尺度适合 X500 的起降、进近、航点、航拍和避障演示；比 Sonoma 更像“机场任务”，比 Baylands 轻。
- CC-BY 4.0，署名即可再分发；Fuel 上有版本号（v3）可记录。

**实测**：

```bash
# Fuel URL 直接 include：能加载，但 DAE 里的绝对 model:// 纹理路径解析失败
gz sim -s -r -v 4 --iterations 60 /tmp/ksql_test.sdf
# [Err] Unable to find file with URI
#   [model://ksql_airport/media/textures/SanCarlosAirport_Sat.png]

# 把模型放到 GZ_SIM_RESOURCE_PATH 下，用 model://ksql_airport 加载：0 错误
GZ_SIM_RESOURCE_PATH=/tmp/gzmodels gz sim -s -r -v 4 --iterations 60 /tmp/ksql_local.sdf
```

**关键坑（两层）**：

1. `model.sdf` 的网格 URI 是绝对 Fuel URL，例如 `https://fuel.gazebosim.org/1.0/openrobotics/models/ksql_airport/3/files/media/SanCarlosAirport_Terrain.DAE`。仅仅复制到本地不会改写它；断网时必须把该前缀替换为 `model://ksql_airport/`。
2. 模型 DAE 的纹理引用是 `model://ksql_airport/media/textures/SanCarlosAirport_Sat.png`（绝对模型路径），不是相对路径。通过 Fuel URL 加载时，纹理解析器不会自动把 Fuel 缓存目录加入资源路径，于是贴图丢失；把模型实体放到 `models/` 或 `assets/cache/maps/` 并加入 `GZ_SIM_RESOURCE_PATH` 即可解决。

本次落地时对三个模型统一做了 URI 改写，并用 `docker run --network none` 复测，KSQL 为 0 错误。

**出生点**：模型内部 `<pose>0 0 -3.5</pose>`，跑道大致在世界原点附近。建议先 `spawn_xyz: [0, 0, 0.3]`，用一次 5 m 起飞确认没有落在建筑/地形里；如果落在建筑上，沿跑道方向平移。

**许可**：CC-BY 4.0，需要在 `assets/README.md` 或场景说明中保留作者/来源。

### 3.2 Sonoma Raceway（已移除，仅保留评估记录）

Sonoma 曾作为轻量候选评估：CC0、8.5 MB 压缩、14 MB 解压、OBJ + MTL，断网加载 0 错误。按当前场景组合（KSQL + Baylands），已删除 `scenes/sonoma_raceway.yaml`、`worlds/sonoma_raceway.sdf` 和 `assets/cache/maps/sonoma_raceway/`。

如以后需要重新引入，按 4.1 的 Fuel 下载和 URI 改写流程重新拉取；注意赛道有起伏，出生点要按网格高度校准，不能直接沿用 `0.3 m`。

### 3.3 Baylands（大而重，需清理）

**是什么**：PX4 官方 `baylands.sdf` 已经引用的 OpenRobotics 湿地/机场模型，压缩 151 MB、解压 393 MB。PX4 的世界文件已经在 `third_party/PX4-Autopilot/Tools/simulation/gz/worlds/baylands.sdf`，加一个 scene YAML 就能启动。

**实测**：本地解压 + URI 改写 + `GZ_SIM_RESOURCE_PATH`，断网加载 0 错误；但出现：

```text
[Wrn] Gazebo does not support Ogre material scripts.
[Wrn] Custom material scripts are not supported.
```

**两个离线化问题**：

1. `model.sdf` 里的网格 URI 仍是绝对 Fuel URL，例如
   `https://fuel.gazebosim.org/1.0/openrobotics/models/baylands/3/files/media/baylands_01.DAE`。
   本地拷贝不会自动改写这些 URI；严格离线需要在解压后批量替换为 `model://baylands/media/...`。
2. 材质使用 OGRE `.material` 脚本，gz-sim 8 不支持，脚本会被忽略，视觉表现不保证；要好看需要转成 PBR/DAE 内嵌材质，工作量不小。

**结论**：如果只是想要“马上有一个大场景”，PX4 自带 world + 首次 Fuel 下载最省事；如果要纳入项目的可复现资源清单，Baylands 需要额外的 URI/材质清理，优先级低于 KSQL。

### 3.4 室内/地下选项

- **Depot**（82 MB，CC-BY 4.0）：大型室内仓库，PBR 资产，适合室内巡检；但 `model.sdf` 是 SDF 1.6，含 `ignition-gazebo-joint-controller-system` 旧插件名和 OGRE 材质脚本，需要迁移后才能作为 Harmonic 世界使用。
- **SubT Urban/Cave/Tunnel**（CC-BY 4.0）：DARPA SubT 虚拟赛道资产，世界文件 0.1–27 MB，但依赖大量模型。它们是 Ignition Fortress 时代产物，世界内使用 `libignition-gazebo-wind-effects-system.so`；当前 Harmonic 镜像里没有 `libignition-gazebo-*` 库（实测 `find /usr/lib -name '*ignition-gazebo*'` 为 0），按原样加载会报插件缺失错误，必须先迁移。适合“愿意做插件名/URI 迁移”的地下或城市搜救场景。
- **Warehouse / Tugbot in Warehouse**：许可是 CC-BY-NC-ND 4.0，禁止商用和衍生，不适合作为开源项目的默认可分发资源，建议避开。

### 3.5 生成式方案

#### gazebo_terrain_generator（BSD-3-Clause）

- 输入：地图上画多边形、选出生点；输出 SDF 1.9 + heightmap + 卫星纹理 + 拉伸的 Mapbox Streets 建筑，直接面向 Harmonic。
- 优点：任意真实地点；输出就是 Gazebo 世界，接入成本低于自己写转换器；仓库活跃（2026-11 仍有提交）。
- 限制：
  - 需要 **Mapbox API token**，高程和建筑矢量都走 Mapbox API；不是纯离线/纯开源数据链。
  - 卫星影像和 Mapbox 数据的再分发受服务条款限制，不适合把生成结果直接提交到公开仓库。
  - 高程图碰撞在 ODE 下表现不好，模板明确要求 DART + bullet；本项目当前世界用 ODE，需要改物理配置并重新验证 PX4 的传感器/控制。
- 适合：本地验证“我的城市/山区”效果，或作为内部场景，不作为默认分发资源。

#### OSM2World（MIT）

- 输入 `.osm.pbf`，输出 glTF/glb、OBJ、POV-Ray，甚至 3D Tiles；Gazebo 的 `gz-common` MeshManager 支持 `gltf`/`glb`（Assimp 路径）。
- 优点：代码 MIT、默认样式 CC0，数据来自 OSM（ODbL，需署名/相同方式共享）；城市建筑几何比手写 SDF 强。
- 限制：没有地形高程；输出坐标系/轴向、单位、材质需要转换；建筑碰撞要么用凸包简化，要么接受 trimesh 开销；OSM 数据质量参差。
- 适合：需要“真实城市街区”且愿意做一次转换管线的情况。

### 3.6 不建议直接引入

| 项目 | 原因 |
| --- | --- |
| [leonhartyao/gazebo_models_worlds_collection](https://github.com/leonhartyao/gazebo_models_worlds_collection) | 394 个模型、50 个世界，含 `city_osm_roundabout`、`small_city`、`yosemite`、无人机赛道等；但整体 GPL-3.0，世界是 SDF 1.4/1.6 + `GAZEBO_MODEL_PATH` + ROS1 插件 + OGRE 脚本，不能直接放进 Harmonic；GPL 也会影响项目分发。适合当素材库/参考，不适合当依赖。 |
| [AWS RoboMaker worlds](https://github.com/aws-robotics/aws-robomaker-small-house-world) | 仓库已归档，许可文件不清晰；Gazebo Classic 时代资产。 |
| [terraforge-gazebo](https://github.com/r3tr056/terraforge-gazebo) | 无 LICENSE，无法合法再分发；星标很少，未验证。 |
| SubT 世界 | 许可清晰（CC-BY 4.0），但 Fortress 插件/URI 需要迁移，不是 drop-in。 |
| AirSim / FlightGoggles / Isaac Sim | Unreal/Unity/Omniverse 引擎，不能作为 Gazebo 世界载入；若换引擎，是另一套项目。 |

## 4. 接入本项目的具体步骤（以 KSQL 为例）

### 4.1 落地模型

Fuel 的规范下载方式是 `gz fuel download`。在项目镜像里执行，避免宿主机没装 Gazebo：

```bash
mkdir -p assets/cache/maps

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  uav-sim:jammy-harmonic \
  bash -lc '
    gz fuel download -u "https://fuel.gazebosim.org/1.0/OpenRobotics/models/ksql_airport"
    rm -rf /workspace/assets/cache/maps/ksql_airport
    mkdir -p /workspace/assets/cache/maps/ksql_airport
    cp -r /tmp/.gz/fuel/fuel.gazebosim.org/openrobotics/models/ksql_airport/3/. \
          /workspace/assets/cache/maps/ksql_airport/
  '
```

`assets/cache/` 已在 `.gitignore` 中，不会把 54 MB 提交进 Git。

下载后的 `model.sdf` 仍可能带绝对 Fuel URI，需要改成 `model://` 才能真正断网加载。三个模型统一处理：

```bash
python3 - <<'PY'
from pathlib import Path
repls = {
    'ksql_airport': ('https://fuel.gazebosim.org/1.0/openrobotics/models/ksql_airport/3/files/', 'model://ksql_airport/'),
    'baylands': ('https://fuel.gazebosim.org/1.0/openrobotics/models/baylands/3/files/', 'model://baylands/'),
}
for name, (old, new) in repls.items():
    p = Path('assets/cache/maps') / name / 'model.sdf'
    text = p.read_text()
    p.write_text(text.replace(old, new))
    print(name, 'remaining https://fuel:', p.read_text().count('https://fuel'))
PY
```

验证：

```bash
docker run --rm --network none \
  -v "$PWD:/workspace" -w /workspace \
  -e GZ_SIM_RESOURCE_PATH=/workspace/models:/workspace/worlds:/workspace/assets/cache/maps \
  uav-sim:jammy-harmonic \
  bash -lc 'for w in ksql_airport baylands; do
    gz sim -s -r --iterations 30 /workspace/worlds/$w.sdf >/tmp/$w.log 2>&1
    echo "$w exit=$? err=$(grep -c "\[Err\]" /tmp/$w.log)"
  done'
```

然后让 Gazebo 能找到 `model://ksql_airport`。两种做法：

**A. 加资源路径（推荐，语义清楚）**：修改 `scripts/container_start.sh`：

```bash
export GZ_SIM_RESOURCE_PATH="/workspace/models:/workspace/worlds:/workspace/assets/cache/maps:${GZ_SIM_RESOURCE_PATH:-}"
```

**B. 不改脚本**：在 `models/` 下建符号链接：

```bash
ln -s ../assets/cache/maps/ksql_airport models/ksql_airport
```

`/workspace/models` 已经在 `GZ_SIM_RESOURCE_PATH` 里，符号链接会在容器内解析到 `assets/cache/maps/ksql_airport`。注意 Windows 宿主对符号链接不友好，团队协作时优先 A。

### 4.2 新增世界

`worlds/ksql_airport.sdf`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sdf version="1.9">
  <world name="ksql_airport">
    <physics name="physics" type="ode">
      <max_step_size>0.004</max_step_size>
      <real_time_factor>1.0</real_time_factor>
      <real_time_update_rate>250</real_time_update_rate>
    </physics>

    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
    <plugin filename="gz-sim-magnetometer-system" name="gz::sim::systems::Magnetometer"/>
    <plugin filename="gz-sim-air-pressure-system" name="gz::sim::systems::AirPressure"/>
    <plugin filename="gz-sim-navsat-system" name="gz::sim::systems::NavSat"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>

    <gravity>0 0 -9.8</gravity>
    <magnetic_field>6e-06 2.3e-05 -4.2e-05</magnetic_field>
    <atmosphere type="adiabatic"/>

    <scene>
      <ambient>0.5 0.5 0.5 1</ambient>
      <background>0.7 0.8 0.9 1</background>
      <shadows>true</shadows>
      <grid>false</grid>
      <sky><clouds>true</clouds></sky>
    </scene>

    <light name="sun" type="directional">
      <pose>0 0 500 0 0 0</pose>
      <cast_shadows>true</cast_shadows>
      <direction>0.001 0.625 -0.78</direction>
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
    </light>

    <include>
      <uri>model://ksql_airport</uri>
      <name>ksql_airport</name>
      <pose>0 0 0 0 0 0</pose>
    </include>

    <spherical_coordinates>
      <surface_model>EARTH_WGS84</surface_model>
      <world_frame_orientation>ENU</world_frame_orientation>
      <latitude_deg>37.5134</latitude_deg>
      <longitude_deg>-122.25</longitude_deg>
      <elevation>3</elevation>
    </spherical_coordinates>
  </world>
</sdf>
```

几点说明：

- 不要给 include 再加 `z` 偏移；模型内部已经用 `<pose>0 0 -3.5</pose>` 把机场面放到大约 0 m。
- `spherical_coordinates` 用 KSQL 的大致经纬度即可满足 GPS 健康；如果要和真实航图对齐，再按机场基准点细调。
- 如果只是做无 GPS 的室内/视觉实验，仍然建议保留 georef，避免 PX4 的全局位置检查失败。

### 4.3 新增场景

`scenes/ksql_airport.yaml`：

```yaml
name: ksql_airport
world_file: worlds/ksql_airport.sdf
world_name: ksql_airport
vehicle:
  model: x500
  spawn_xyz: [0.0, 0.0, 0.3]
  spawn_yaw: 0.0
mavlink:
  sdk_port: 14540
ros:
  enabled: false
```

`scripts/manage.py` 会校验 `world_name` 与 SDF `<world name>` 一致、`spawn_xyz` 是 3 个数、场景名只含字母数字/下划线/横线。

### 4.4 启动与验证

```bash
./scripts/doctor.sh
./scripts/start.sh --scene ksql_airport
uv run python -m control.telemetry --duration 20
./scripts/stop.sh
```

先不要加 `--gui`，确认服务端能稳定启动；再跑 `--gui` 看材质/纹理和帧率。

## 5. 资源固定、许可与体积

### 5.1 清单格式

项目现有的 `assets/manifest.yaml` 只接受**直接的 HTTPS 文件 URL + SHA256**。Fuel 的规范 URL 是资源 API，不是文件 URL，且下载会走签名重定向，不能直接填进 `url` 字段。

两种可行做法：

**A. 发布固定压缩包（推荐，最贴合现有下载器）**

1. 在本地把解压后的目录打成确定性 tar.gz（固定 mtime/owner/顺序）；
2. 上传到 GitHub Release 或内部对象存储，得到稳定的 HTTPS URL；
3. 计算 SHA256，写入清单：

```yaml
resources:
  - id: ksql-airport-v3
    url: https://example.org/uav-sim-assets/ksql_airport-v3.tar.gz
    filename: ksql_airport-v3.tar.gz
    sha256: <64 位十六进制>
    license: CC-BY-4.0
    source: https://fuel.gazebosim.org/1.0/OpenRobotics/models/ksql_airport
```

现有 `fetch_assets.py` 只下载和校验，不自动解压；解压和 `GZ_SIM_RESOURCE_PATH` 仍需按 4.1 处理。

**B. 扩展下载器支持 Fuel**

给 `fetch_assets.py` 增加 `fuel_url` + `version` 模式：调用 `gz fuel download`，校验 Fuel 元数据中的 `version`，再对目录做树哈希。这样能直接跟随 Fuel 版本，不依赖自建压缩包；但需要改代码和测试，属于后续工程工作。

### 5.2 许可注意

- **CC0**：无署名义务，最省事（例如曾评估的 Sonoma）。
- **CC-BY 4.0**（KSQL、Baylands、Depot、SubT）：必须在文档/发布物中保留作者、来源、许可链接；修改过的模型要注明修改。
- **OSM 数据**（OSM2World、KSQL 模型内命名为 OSM 的建筑网格）：ODbL 要求署名，衍生素材可能要求相同方式共享；商用/再分发前要单独评估。
- **Mapbox 数据**（terrain generator）：受 Mapbox 服务条款约束，不适合把生成结果直接公开再分发。
- **CC-BY-NC-ND**（Warehouse、Tugbot in Warehouse）：禁止商用、禁止衍生，直接排除。
- **GPL-3.0**（leonhartyao collection）：如果项目本身不是 GPL，引入其模型/世界可能带来分发义务；只作参考最安全。

### 5.3 体积策略

- 小于 ~10 MB 的模型可以直接进 Git，或走 `assets/cache/`。
- 10–100 MB（KSQL 54 MB）：建议 `assets/cache/` + 固定压缩包；不要直接提交解压目录。
- 大于 100 MB（Baylands 393 MB）：只通过清单下载，且先确认实时因子和显存/内存占用。
- `assets/cache/` 已在 `.gitignore`，`models/` 没有；不要把大模型放进 `models/` 后忘记忽略。

## 6. 验收清单

对新地图至少做以下检查，避免“能加载”被误当成“能飞”：

1. **SDF 解析**：`gz sdf -k worlds/<name>.sdf`（若镜像提供 `gz sdf`），或启动日志无 `[Err]`。
2. **实体存在**：`gz model -m x500_0` / `gz entity list`，确认飞机和地图实体都在。
3. **出生点净空**：5 m 起飞、悬停、降落；确认没有落在建筑顶、树、水面或地形以下。
4. **GPS/坐标**：`control.telemetry` 的全局位置健康；对照世界的 `spherical_coordinates` 检查经纬度符号和量级。
5. **碰撞**：低空掠过跑道/建筑边缘，确认不会穿模；trimesh 碰撞可能很慢，观察实时因子。
6. **性能**：`gz stats` 看 real-time factor；GUI 下看帧率。大场景先在无界面模式测。
7. **传感器**：加相机/雷达后检查遮挡、远裁剪面（`camera_clip/far`）和纹理是否正常。
8. **任务回归**：用 `mission_demo` / `offboard_demo` 在机场空旷区跑一遍；不要在建筑密集区直接跑默认方形航迹。
9. **离线**：断网后重启，确认没有运行时 Fuel 下载；日志中不应出现 `Downloading model`。
10. **许可**：场景 README/`assets/README.md` 写清来源、版本、作者、许可和修改。

## 7. 其他可立即使用的“无下载”世界

PX4 子模块里已经有一些自包含世界，不需要 Fuel，也不需要新模型；加一个 `scenes/*.yaml` 就能用：

| 世界 | 特点 | 备注 |
| --- | --- | --- |
| `kthspacelab` | 室内实验室，内联几何 | 空间较小，适合悬停/室内控制 |
| `walls` | 100 m 地面 + 墙 | 避障/壁面飞行 |
| `lawn` | 平地 + 天空 | 最轻的室外测试 |
| `ridge` | 只有 PX4-gazebo-models 仓库有，非当前子模块 | 需要单独取，或升级 PX4 子模块 |

这些不是“地图项目”，但能在没有新资源的情况下快速扩展场景类型；适合在接入 KSQL 前先验证 scene YAML 流程。

## 8. 当前保留的场景

工程现在保留两个本地场景，均已做过断网加载、GPS 遥测和 3 m 起降验证：

1. `ksql_airport`：CC-BY 4.0、54 MB，默认的“真实机场”场景；同步补 `assets/README.md` 的署名和场景说明。
2. `baylands`：CC-BY 4.0、393 MB + 15 MB 水面，大范围自然场景；启动时有旧版 OGRE 材质脚本警告，不影响碰撞和飞行。

Sonoma 已按需求移除。以后新增地图时，仍按“先 `lawn`/`walls` 验证 scene 机制 → 再接目标地图 → 最后补许可和性能验收”的顺序；如果需要任意城市，再引入 OSM2World 或 terrain generator 的离线管线。

## 9. 参考链接

- Gazebo Fuel 模型：<https://fuel.gazebosim.org/1.0/OpenRobotics/models/ksql_airport>
- Gazebo Fuel 世界列表：<https://fuel.gazebosim.org/1.0/OpenRobotics/worlds>
- Fuel 命令行：<https://gazebosim.org/api/fuel_tools/7/cmdline.html>
- PX4 Gazebo 模型/世界：<https://github.com/PX4/PX4-gazebo-models>
- Gazebo 材质迁移说明：<https://gazebosim.org/api/sim/8/migrationsdf.html>
- gz-common 网格格式（含 glTF/glb）：<https://gazebosim.org/api/common/5/classgz_1_1common_1_1MeshManager.html>
- Sonoma Raceway：<https://fuel.gazebosim.org/1.0/OpenRobotics/models/Sonoma%20Raceway>
- Baylands：<https://fuel.gazebosim.org/1.0/OpenRobotics/models/baylands>
- Depot：<https://fuel.gazebosim.org/1.0/OpenRobotics/models/Depot>
- SubT：<https://github.com/osrf/subt>
- 地形生成器：<https://github.com/saiaravind19/gazebo_terrain_generator>
- OSM2World：<https://github.com/tordanik/OSM2World>
- Gazebo 模型/世界合集：<https://github.com/leonhartyao/gazebo_models_worlds_collection>
