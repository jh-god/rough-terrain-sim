# rough_terrain_sim

ROS 2 Humble과 Gazebo Fortress용 울퉁불퉁한 노면 시뮬레이션 패키지입니다.
50 m × 50 m PNG heightmap 지형을 불러오며, Clearpath Husky A200,
Jackal J100 또는 FW-max를 선택해 스폰할 수 있습니다. FW-max는 기존
skid-steer 근사 모델과 Gear 6 dual-Ackermann 4륜 조향 모델을 선택할 수
있습니다.
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

Clearpath 로봇을 사용하려면 다음 패키지가 설치되어 있어야 합니다.

```bash
sudo apt update
sudo apt install ros-humble-clearpath-simulator
```

FW-max swerve 모드를 사용할 때만 다음 제어 패키지가 추가로 필요합니다.

```bash
sudo apt install \
  ros-humble-gz-ros2-control \
  ros-humble-ros2-controllers
```

FW-max visual DAE는 이 패키지의 `meshes/fwmax/`에 포함되어 있으며,
swerve 모드가 필요하면 같은 workspace에
`fwmax_dual_ackermann_controller` 패키지를 추가해 사용합니다. 별도의
FW-max workspace나 description 패키지는 필요하지 않습니다.

## 빌드

```bash
cd ~/gazebo_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select rough_terrain_sim --symlink-install
source install/setup.bash
```

위 빌드만으로 Husky, Jackal, FW-max skid 모드를 실행할 수 있으며
`fwmax_dual_ackermann_controller` 패키지는 필요하지 않습니다. FW-max
swerve 모드를 사용할 때는 두 패키지를 함께 빌드합니다.

```bash
cd ~/gazebo_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select \
  rough_terrain_sim fwmax_dual_ackermann_controller \
  --symlink-install
source install/setup.bash
```

`launch`, world, model, heightmap을 수정한 뒤에도 위 명령을 다시 실행한
다음 Gazebo를 재시작하세요.

## 실행

기본값은 Husky A200이 포함된 환경입니다.

```bash
ros2 launch rough_terrain_sim rough_terrain.launch.py
```

로봇 종류는 `robot` 인자로 선택합니다.

```bash
# Husky A200
ros2 launch rough_terrain_sim rough_terrain.launch.py robot:=husky

# Jackal J100
ros2 launch rough_terrain_sim rough_terrain.launch.py robot:=jackal

# FW-max Pro (기본값: 4륜 skid-steer 근사 모델)
ros2 launch rough_terrain_sim rough_terrain.launch.py robot:=fwmax

# FW-max Pro (Gear 6 dual-Ackermann 4륜 조향 모델)
ros2 launch rough_terrain_sim rough_terrain.launch.py \
  robot:=fwmax fwmax_drive_mode:=swerve

# 로봇 없이 지형만 실행
ros2 launch rough_terrain_sim rough_terrain.launch.py robot:=none
```

Gazebo가 열리면 카메라는 지형의 기본 스폰 구역 부근을 바라봅니다.
로봇은 Gazebo 시작 약 3초 후 생성됩니다.

주요 launch 인자는 다음과 같습니다.

| 인자 | 기본값 | 설명 |
| --- | --- | --- |
| `robot` | `husky` | `husky`, `jackal`, `fwmax`, `none` 중 선택 |
| `fwmax_drive_mode` | `skid` | FW-max에서만 사용하며 `skid` 또는 `swerve` 선택 |
| `rviz` | `true` | RViz2 실행 여부 |

## 스폰 위치와 자세

기본 스폰 위치는 현재 기본 heightmap의 완만한 구역입니다.

| 인자 | 기본값 | 설명 |
| --- | ---: | --- |
| `robot_x` | `-7.2` | x 위치 [m] |
| `robot_y` | `-3.2` | y 위치 [m] |
| `robot_z` | `3.2` | z 위치 [m] |
| `robot_yaw` | `0.0` | yaw [rad] |

예시:

```bash
ros2 launch rough_terrain_sim rough_terrain.launch.py \
  robot:=jackal robot_x:=-6.0 robot_y:=-4.0 robot_z:=4.2 robot_yaw:=1.57
```

새 heightmap을 생성한 경우 해당 위치의 지형 높이에 맞춰 `robot_z`를
조정하세요. 너무 높은 값은 특히 작은 Jackal이 낙하하며 전복될 수 있습니다.

## FW-max 구동 모델

FW-max의 실제 구동계는 4륜 독립 구동·독립 조향 swerve 방식이지만, 이
패키지는 `fwmax_drive_mode` 인자로 다음 두 모델을 제공합니다.

- `skid` (기본값): 네 조향축을 고정하고 좌우 속도 차와 lateral slip으로
  회전하는 기존 4WD skid-steer 근사
- `swerve`: FW-max Gear 6에 맞춰 `/cmd_vel`의 `linear.x`, `angular.z`를
  네 조향각과 네 바퀴 속도로 변환하는 dual-Ackermann 4륜 조향

두 모드 모두 횡이동을 위한 `linear.y`는 사용하지 않습니다. `swerve`
모드의 제어 노드와 `ros2_control` 설정은 별도
`fwmax_dual_ackermann_controller` 패키지에 있습니다. 이 패키지는 선택적
의존성이므로 Husky, Jackal 또는 FW-max skid 모드만 사용할 때는 workspace에
없어도 됩니다. launch는 `robot:=fwmax fwmax_drive_mode:=swerve`일 때만
제어 패키지를 조회하며, 이때 패키지가 설치되어 있지 않으면 package-not-found
오류로 실행을 중단합니다.

### 공통 차체와 suspension

- 전체 질량: 195.84 kg
- 전체 질량중심: suspension 설계 정적 평형 자세에서 로봇 수평 중심,
  지상 0.255 m (`base_link` 기준 `z=-0.133 m`)
- 휠베이스: 0.60 m
- 윤거: 0.45 m
- 바퀴 반경: 0.125 m
- passive suspension: 바퀴별 수직 prismatic spring-damper
- suspension 이동 범위: 70 mm (`-0.03 ~ +0.04 m`)
- suspension 강성/감쇠: 바퀴당 20,000 N/m, 925 N·s/m
- 외형: `meshes/fwmax/isrl_fwmax_pro.dae`
- 물리 충돌: 단순화한 차체 box와 네 개의 cylinder 바퀴

각 바퀴의 suspension carrier는 차체와 수직 prismatic joint로 연결됩니다.
Spring-damper와 preload를 적용해 평지 정착 시 설계 차고를 유지하며,
swerve 모드에서는 suspension 아래에 Z축 연속 회전 steering joint가
추가됩니다.

### Skid 모드

Gazebo DiffDrive 시스템이 좌우 각 두 바퀴를 구동하고, WheelSlip 시스템이
회전에 필요한 횡방향 미끄러짐을 제공합니다. 기존 FW-max 근사 모델과
같은 동작이며 다음 명령으로 실행합니다.

```bash
ros2 launch rough_terrain_sim rough_terrain.launch.py \
  robot:=fwmax fwmax_drive_mode:=skid
```

### Gear 6 dual-Ackermann 모드

`swerve` 모드는 실제 FW-max ROS/CAN 패키지에서 사용하는 Gear 6 입력에
맞춰 `/cmd_vel`의 `linear.x`와 `angular.z`만 처리합니다. 별도 패키지의
제어 노드가 각 바퀴 위치의 순간 속도 벡터로 네 조향각과 네 바퀴 속도를
계산하고, 두 개의 `ros2_control` forward controller를 통해 다음 관절을
속도 제어합니다.

- 조향: `front_left`, `front_right`, `rear_left`, `rear_right` steering joint
- 구동: `front_left`, `front_right`, `rear_left`, `rear_right` wheel joint

현재 조향각을 `/joint_states`에서 받아 목표각까지 폐루프 제어합니다. 같은
주행 방향을 만드는 `조향각 + π` 해가 더 가까우면 해당 각도를 선택하고
바퀴 회전 방향을 반전하여 불필요한 조향 회전을 줄입니다. 조향 오차가
`0.35 rad` 이상이면 타이어 끌림을 줄이기 위해 바퀴 구동을 잠시 멈추고,
정렬된 후 각 바퀴의 회전반경에 맞는 속도를 적용합니다.

zero Twist가 입력되거나 `/cmd_vel`이 `0.5 s` 동안 갱신되지 않으면 네 바퀴
구동을 정지하고 모든 steering joint를 전방 `0 rad`로 되돌립니다. 정렬
허용오차는 `0.001 rad`, 최대 조향 속도는 `2.5 rad/s`입니다.

```bash
ros2 launch rough_terrain_sim rough_terrain.launch.py \
  robot:=fwmax fwmax_drive_mode:=swerve
```

제어 인터페이스는 다음과 같습니다.

| 구분 | 토픽 | 메시지 |
| --- | --- | --- |
| 차량 명령 입력 | `/cmd_vel` | `geometry_msgs/msg/Twist` |
| 조향 속도 명령 | `/fwmax_steering_controller/commands` | `std_msgs/msg/Float64MultiArray` |
| 바퀴 속도 명령 | `/fwmax_wheel_controller/commands` | `std_msgs/msg/Float64MultiArray` |
| 관절 상태 | `/joint_states` | `sensor_msgs/msg/JointState` |

### Odometry

두 모드 모두 `/odom`, `/tf`, `/joint_states`를 제공합니다. `skid` 모드의
`odom → base_footprint`는 DiffDrive가 계산한 평면 odometry입니다.

`swerve` 모드에서는 Gazebo의 월드 기준 3D pose를
`/ground_truth/odom`으로 보존합니다. `fwmax_dual_ackermann_controller`
패키지의 `fwmax_planar_odometry` 노드는 처음 수신한 x, y, yaw를 원점으로
저장하고, 이후 pose를 이 초기 좌표계로 변환하여 `/odom`과
`odom → base_footprint` TF로 발행합니다. Navigation에 사용하는 이
odometry에는 x, y, yaw만 포함되며 z, roll, pitch는 0입니다.

원본 DAE에는 차체와 함께 고정된 바퀴 형상이 포함되어 있습니다. 실제로
상하 이동·조향하고 지면과 접촉하는 검은 cylinder 바퀴와 DAE 바퀴가
겹쳐 보일 수 있지만 물리 동작에는 영향이 없습니다.

## FW-max 센서와 TF

FW-max 모델에는 Ouster 64채널 LiDAR와 Intel RealSense D435가 포함되어
있으며, 두 센서는 skid와 swerve 모드에서 동일하게 동작합니다.

| TF | xyz [m] | rpy [rad] | 비고 |
| --- | --- | --- | --- |
| `base_link → os_sensor` | `0.32 0.0 0.505` | `0.0 0.0 0.0` | Ouster, 수직 64채널 |
| `base_link → camera_link` | `0.41 0.01 0.335` | `0.0 0.7854 0.0` | RealSense D435 |

Ouster는 `clearpath_sensors_description`의 OS1 macro를 사용하며
`samples_v=64`로 설정되어 있습니다. `os_sensor`는 imported measurement
frame과 같은 위치의 alias frame입니다. RealSense macro 내부 frame
offset을 보정해 위 표의 `camera_link` 변환이 유지되도록 구성했습니다.

ROS 2에서 사용하는 주요 센서 토픽은 다음과 같습니다.

| 센서 데이터 | ROS 2 토픽 |
| --- | --- |
| Ouster LaserScan | `/sensors/os1_64/scan` |
| Ouster PointCloud2 | `/sensors/os1_64/points` |
| RGB 영상 | `/sensors/camera/color/image` |
| Depth 영상 | `/sensors/camera/depth/image` |
| RGB CameraInfo | `/sensors/camera/color/camera_info` |
| Depth CameraInfo | `/sensors/camera/depth/camera_info` |
| 카메라 원본 PointCloud2 | `/sensors/camera/points` |
| frame 보정 PointCloud2 | `/sensors/camera/points_aligned` |

Gazebo Fortress RGB-D point cloud의 frame 표기가 실제 point 배열 방향과
맞지 않는 경우를 보정하기 위해 `camera_pointcloud_frame_fix` 노드가 원본
cloud를 `camera_link` frame의 `/sensors/camera/points_aligned`로 다시
발행합니다.

## 키보드 조작

Gazebo를 실행한 상태에서 새 터미널을 열고 workspace를 source합니다.

```bash
source /opt/ros/humble/setup.bash
source ~/gazebo_ws/install/setup.bash
```

Husky와 Jackal:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/platform/cmd_vel_unstamped
```

FW-max:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

teleop을 실행한 터미널에 포커스를 둔 뒤 `i`, `,`, `j`, `l` 키로 조작합니다.

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
  --output ~/gazebo_ws/src/rough-terrain-sim/models/rough_terrain/heightmaps/rough_terrain_8bit.png
```

### 16-bit

```bash
ros2 run rough_terrain_sim generate_rough_heightmap_16bit \
  --seed 42 \
  --width-m 50 --height-m 50 \
  --max-elevation-m 3.17 \
  --roughness 0.65 \
  --smoothing-sigma 0.30 \
  --output ~/gazebo_ws/src/rough-terrain-sim/models/rough_terrain/heightmaps/rough_terrain_16bit.png
```

생성 결과는 단일 채널 `16-bit grayscale PNG`이며 픽셀값 `0–65535`는
정규화된 높이를 나타냅니다. 실제 Gazebo 지형의 높이 범위는 사용하는
heightmap과 `models/rough_terrain/model.sdf`의 `<size>` 세 번째 값으로
결정됩니다. 생성 시 지정한 `max_elevation_m`와 이 값을 동일하게 맞춰야
의도한 높이로 표현됩니다. 16-bit 이미지를 Gazebo에서 실행할 때는 패치가
적용된 `ignition-common4` 라이브러리를 활성화해야 합니다.

생성 후 빌드하고 Gazebo를 재시작합니다.

```bash
cd ~/gazebo_ws
colcon build --packages-select rough_terrain_sim --symlink-install
source install/setup.bash
```

지형의 가로·세로 크기와 높이 범위는
`models/rough_terrain/model.sdf`의 `<size>`에서 정합니다. 현재 설정은
`<size>50 50 3.17</size>`이며, 세 번째 값 `3.17`은 현재 불러오는
heightmap의 최대 고도 범위에 맞춘 값입니다. 다른 heightmap으로 교체할
때는 그 이미지가 표현하려는 높이에 맞춰 이 값을 함께 수정해야 합니다.

## 노면 마찰과 wheel slip

지형의 ODE 마찰계수는 `models/rough_terrain/model.sdf`에 있습니다.

```xml
<mu>1.2</mu>
<mu2>1.2</mu2>
```

현재 값 `1.2`는 건조한 단단한 흙 또는 아스팔트에 가까운 시작점이며,
모든 로봇에 공통 적용됩니다.

Clearpath 로봇은 별도로 WheelSlip 플러그인을 사용합니다. 이는 노면
마찰계수가 아니라 바퀴가 미끄러지는 정도를 정하는 값입니다. 접지력을
높이고 싶다면 다음 값을 사용해 볼 수 있습니다.

```xml
<slip_compliance_longitudinal>0.1</slip_compliance_longitudinal>
<slip_compliance_lateral>0.2</slip_compliance_lateral>
```

FW-max의 `skid` 모드는 같은 초기값을 사용하며, `swerve` 모드는 lateral
slip compliance를 `0.02`로 낮춥니다. 두 값 모두
`urdf/fwmax_skid_steer.urdf.xacro`에서 관리합니다.

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
gazebo_ws/src/
├── fwmax_dual_ackermann_controller/
│   ├── config/fwmax_controllers.yaml
│   ├── fwmax_dual_ackermann_controller/
│   │   ├── controller.py
│   │   ├── fwmax_planar_odometry.py
│   │   ├── kinematics.py
│   │   └── planar_odometry.py
│   └── test/
│       ├── test_kinematics.py
│       └── test_planar_odometry.py
└── rough-terrain-sim/
    ├── README.md
    ├── launch/rough_terrain.launch.py
    ├── worlds/rough_terrain.sdf
    ├── models/rough_terrain/
    │   ├── model.sdf
    │   ├── heightmaps/
    │   └── textures/
    ├── config/
    │   ├── fwmax/sensors_bridge.yaml
    │   ├── husky/
    │   └── jackal/
    ├── meshes/fwmax/isrl_fwmax_pro.dae
    ├── urdf/
    │   ├── fwmax_skid_steer.urdf.xacro
    │   └── husky_ouster_os1_128.urdf.xacro
    ├── rough_terrain_sim/
    │   ├── camera_pointcloud_frame_fix.py
    │   ├── generate_heightmap.py
    │   └── generate_heightmap_16bit.py
    └── rviz/vis.rviz
```
