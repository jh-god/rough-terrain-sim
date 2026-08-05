# rough_terrain_sim

ROS 2 Humble과 Gazebo Fortress용 울퉁불퉁한 노면 시뮬레이션 패키지입니다.
50 m × 50 m PNG heightmap 지형을 불러오며, Clearpath Husky A200 또는
Jackal J100을 선택해 스폰할 수 있습니다.
<p align="center">
  <img
    src="sample/sample.png"
    alt="Gazebo Fortress 16-bit heightmap"
    width="500">
</p>

## 요구 사항

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Fortress (`ign gazebo` / Gazebo Sim 6)
- **Recommend** Modified *ignition-common4_4.8.1 package* (https://github.com/jh-god/gz-common.git) \
  16-bit의 heightmap 이미지를 사용할 수 있습니다.
- Clearpath simulator
- Ouster ROS2 driver (https://github.com/ouster-lidar/ouster-ros.git) 

Clearpath 로봇을 사용하려면 다음 패키지가 설치되어 있어야 합니다.

```bash
sudo apt update
sudo apt install ros-humble-clearpath-simulator
```
16-bit 패치 라이브러리를 별도 경로에 설치했다면 Gazebo 실행 전에 활성화합니다. 아래 경로는 설치 위치에 맞게 변경하세요.
```bash
export LD_LIBRARY_PATH="$HOME/opt/ignition-common4-16bit/lib:${LD_LIBRARY_PATH}"
```

## 빌드

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select rough_terrain_sim --symlink-install
source install/setup.bash
```

`launch`, world, model, heightmap을 수정한 뒤에도 위 명령을 다시 실행한
다음 Gazebo를 재시작하세요.

## 실행

기본값은 husky가 불러와 환경입니다.

```bash
ros2 launch rough_terrain_sim rough_terrain.launch.py
```

로봇 종류는 `robot` 인자로 선택합니다.

```bash
# Husky A200
ros2 launch rough_terrain_sim rough_terrain.launch.py robot:=husky

# Jackal J100
ros2 launch rough_terrain_sim rough_terrain.launch.py robot:=jackal

# 로봇 없이 지형만 실행
ros2 launch rough_terrain_sim rough_terrain.launch.py robot:=none
```

Gazebo가 열리면 카메라는 기본 스폰 위치 `(-7.2, -5.5)`를 향합니다.
로봇은 Gazebo 시작 약 3초 후 생성됩니다.

## 스폰 위치와 자세

기본 스폰 위치는 현재 기본 heightmap의 완만한 구역입니다.

| 인자 | 기본값 | 설명 |
| --- | ---: | --- |
| `robot_x` | `-7.2` | x 위치 [m] |
| `robot_y` | `-5.5` | y 위치 [m] |
| `robot_z` | `1.2` | z 위치 [m] |
| `robot_yaw` | `0.0` | yaw [rad] |

예시:

```bash
ros2 launch rough_terrain_sim rough_terrain.launch.py \
  robot:=jackal robot_x:=-6.0 robot_y:=-4.0 robot_z:=1.2 robot_yaw:=1.57
```

새 heightmap을 생성한 경우 해당 위치의 지형 높이에 맞춰 `robot_z`를
조정하세요. 너무 높은 값은 특히 작은 Jackal이 낙하하며 전복될 수 있습니다.

## 키보드 조작

Gazebo를 실행한 상태에서 새 터미널을 열고 workspace를 source합니다.

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/platform/cmd_vel_unstamped
```

teleop을 실행한 터미널에 포커스를 둔 뒤 `i`, `,`, `j`, `l` 키로 조작합니다.
## 센서와 RViz2

- Husky: Intel RealSense RGB-D 카메라와 Ouster OS1-128
- Jackal: Velodyne VLP-16

RViz2는 패키지의 `rviz/vis.rviz` 설정으로 자동 실행됩니다. Fortress의
RGB-D point cloud frame 불일치를 보정하기 위해
`/sensors/camera_0/points`를 `/sensors/camera_0/points_aligned`로
재발행하며, RViz에서는 보정된 토픽을 사용합니다.
## Heightmap Generator

NumPy와 Pillow 기반 생성기는 1024 × 1024 grayscale PNG를 만듭니다.
8-bit와 16-bit 생성기를 각각 제공하며, 같은 파라미터와 `seed`는
동일한 결과를 생성합니다.

### 8-bit

```bash
ros2 run rough_terrain_sim generate_rough_heightmap \
  --seed 42 \
  --width-m 50 --height-m 50 \
  --max-elevation-m 4 \
  --roughness 0.65 \
  --smoothing-sigma 0.30 \
  --output ~/ros2_ws/src/rough_terrain_sim/models/rough_terrain/heightmaps/rough_terrain_8bit.png
```

### 16-bit

```bash
ros2 run rough_terrain_sim generate_rough_heightmap_16bit \
  --seed 42 \
  --width-m 50 --height-m 50 \
  --max-elevation-m 3.17 \
  --roughness 0.65 \
  --smoothing-sigma 0.30 \
  --output ~/ros2_ws/src/rough_terrain_sim/models/rough_terrain/heightmaps/rough_terrain_16bit.png
```

생성 결과는 단일 채널 `16-bit grayscale PNG`이며 픽셀값 `0–65535`가
각각 `0 m`와 `max_elevation_m`에 대응합니다. Gazebo에서 실행할 때는
16-bit 패치가 적용된 `ignition-common4` 라이브러리를 활성화해야 합니다.

생성 후 빌드하고 Gazebo를 재시작합니다.

```bash
cd ~/ros2_ws
colcon build --packages-select rough_terrain_sim --symlink-install
source install/setup.bash
```

지형 물리 크기와 높이 범위는
`models/rough_terrain/model.sdf`의 `<size>50 50 4</size>`에서 정합니다. \
이는 불러올 환경에 따라 수정이 필요합니다.

## 노면 마찰과 wheel slip

지형의 ODE 마찰계수는 `models/rough_terrain/model.sdf`에 있습니다.

```xml
<mu>1.2</mu>
<mu2>1.2</mu2>
```

현재 값 `1.2`는 건조한 단단한 흙 또는 아스팔트에 가까운 시작점이며,
Husky와 Jackal에 공통 적용됩니다.

Clearpath 로봇은 별도로 WheelSlip 플러그인을 사용합니다. 이는 노면
마찰계수가 아니라 바퀴가 미끄러지는 정도를 정하는 값입니다. 접지력을
높이고 싶다면 다음 값을 사용해 볼 수 있습니다.

```xml
<slip_compliance_longitudinal>0.1</slip_compliance_longitudinal>
<slip_compliance_lateral>0.2</slip_compliance_lateral>
```

현재 Clearpath 설치 모델을 직접 바꾸는 명령은 아래와 같습니다. 이 변경은
`apt upgrade`로 Clearpath 패키지가 갱신되면 원복될 수 있으며, 변경 후에는
Gazebo를 완전히 종료하고 다시 실행해야 합니다. `colcon build`는 필요하지
않습니다.

Husky A200:

```bash
sudo sed -i \
  -e 's#<slip_compliance_lateral>1.0</slip_compliance_lateral>#<slip_compliance_lateral>0.2</slip_compliance_lateral>#g' \
  -e 's#<slip_compliance_longitudinal>1.0</slip_compliance_longitudinal>#<slip_compliance_longitudinal>0.1</slip_compliance_longitudinal>#g' \
  /opt/ros/humble/share/clearpath_platform_description/urdf/a200/a200.urdf.xacro
```

Jackal J100:

```bash
sudo sed -i \
  -e 's#<slip_compliance_lateral>1.0</slip_compliance_lateral>#<slip_compliance_lateral>0.2</slip_compliance_lateral>#g' \
  -e 's#<slip_compliance_longitudinal>1.0</slip_compliance_longitudinal>#<slip_compliance_longitudinal>0.1</slip_compliance_longitudinal>#g' \
  /opt/ros/humble/share/clearpath_platform_description/urdf/j100/j100.urdf.xacro
```


## 패키지 구조

```text
rough_terrain_sim/
├── launch/rough_terrain.launch.py
├── worlds/rough_terrain.sdf
├── rviz/vis.rviz
├── urdf/husky_ouster_os1_128.urdf.xacro
├── models/rough_terrain/
│   ├── model.sdf
│   ├── heightmaps/
│   │   ├── rough_terrain_8bit.png
│   │   └── rough_terrain_16bit.png
│   └── textures/
├── config/
│   ├── husky/
│   │   ├── robot.yaml
│   │   └── ouster_128_bridge.yaml
│   └── jackal/robot.yaml
└── rough_terrain_sim/
    ├── generate_heightmap.py
    ├── generate_heightmap_16bit.py
    └── camera_pointcloud_frame_fix.py
```
