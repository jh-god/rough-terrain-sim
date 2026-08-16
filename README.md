# rough_terrain_sim

ROS 2 Humble과 Gazebo Fortress용 울퉁불퉁한 노면 시뮬레이션 패키지입니다.
50 m × 50 m PNG heightmap 지형을 불러오며, Clearpath Husky A200,
Jackal J100 또는 FW-max를 선택해 스폰할 수 있습니다.
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

FW-max를 사용하려면 `fwmax_ws`의 `isrl_robot_description` 패키지를 먼저
빌드해야 합니다. `rough_terrain_sim`은 해당 패키지의 DAE mesh를 복사하지
않고 직접 참조합니다.

```bash
cd ~/fwmax_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select isrl_robot_description --symlink-install
source install/setup.bash
```

## 빌드

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
# FW-max를 사용할 경우 이 workspace를 underlay로 먼저 source합니다.
source ~/fwmax_ws/install/setup.bash
colcon build --packages-select rough_terrain_sim --symlink-install
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

# FW-max Pro (4륜 skid-steer 근사 모델)
ros2 launch rough_terrain_sim rough_terrain.launch.py robot:=fwmax

# 로봇 없이 지형만 실행
ros2 launch rough_terrain_sim rough_terrain.launch.py robot:=none
```

Gazebo가 열리면 카메라는 지형의 기본 스폰 구역 부근을 바라봅니다.
로봇은 Gazebo 시작 약 3초 후 생성됩니다.

## 스폰 위치와 자세

기본 스폰 위치는 현재 기본 heightmap의 완만한 구역입니다.

| 인자 | 기본값 | 설명 |
| --- | ---: | --- |
| `robot_x` | `-7.2` | x 위치 [m] |
| `robot_y` | `-3.2` | y 위치 [m] |
| `robot_z` | `4.2` | z 위치 [m] |
| `robot_yaw` | `0.0` | yaw [rad] |

예시:

```bash
ros2 launch rough_terrain_sim rough_terrain.launch.py \
  robot:=jackal robot_x:=-6.0 robot_y:=-4.0 robot_z:=4.2 robot_yaw:=1.57
```

새 heightmap을 생성한 경우 해당 위치의 지형 높이에 맞춰 `robot_z`를
조정하세요. 너무 높은 값은 특히 작은 Jackal이 낙하하며 전복될 수 있습니다.

## FW-max skid-steer 모델

FW-max의 실제 구동계는 4륜 독립 구동·독립 조향 swerve 방식이지만, 이
패키지에서는 네 바퀴의 조향축을 고정한 4WD skid-steer 방식으로
근사합니다. 따라서 `/cmd_vel`의 `linear.x`와 `angular.z`만 사용하며
swerve의 횡이동을 위한 `linear.y`는 지원하지 않습니다.

- 전체 질량: 125 kg
- 전체 질량중심: `base_link` 원점
- 휠베이스: 0.60 m
- 윤거: 0.45 m
- 바퀴 반경: 0.125 m
- 외형: `isrl_robot_description/meshes/isrl_fwmax_pro.dae`
- 물리 충돌: 단순화한 차체 box와 네 개의 cylinder 바퀴

Gazebo의 DiffDrive 시스템이 좌우 각 두 개의 바퀴를 구동하며, WheelSlip
시스템이 skid 회전에 필요한 횡방향 미끄러짐을 제공합니다. `/odom`,
`/tf`, `/joint_states`는 ROS 2로 bridge됩니다.

## 키보드 조작

Gazebo를 실행한 상태에서 새 터미널을 열고 workspace를 source합니다.

```bash
source /opt/ros/humble/setup.bash
source ~/fwmax_ws/install/setup.bash  # FW-max를 실행할 때
source ~/ros2_ws/install/setup.bash
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

생성 결과는 단일 채널 `16-bit grayscale PNG`이며 픽셀값 `0–65535`는
정규화된 높이를 나타냅니다. 실제 Gazebo 지형의 높이 범위는 사용하는
heightmap과 `models/rough_terrain/model.sdf`의 `<size>` 세 번째 값으로
결정됩니다. 생성 시 지정한 `max_elevation_m`와 이 값을 동일하게 맞춰야
의도한 높이로 표현됩니다. 16-bit 이미지를 Gazebo에서 실행할 때는 패치가
적용된 `ignition-common4` 라이브러리를 활성화해야 합니다.

생성 후 빌드하고 Gazebo를 재시작합니다.

```bash
cd ~/ros2_ws
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

FW-max 근사 모델도 같은 초기값을
`urdf/fwmax_skid_steer.urdf.xacro`에서 사용합니다. FW-max의 값은 시스템
설치 파일이 아니라 이 패키지의 Xacro에서 조정합니다.

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
├── README.md
├── package.xml
├── setup.py
├── setup.cfg
├── launch/
│   └── rough_terrain.launch.py
├── worlds/
│   └── rough_terrain.sdf
├── models/rough_terrain/
│   ├── model.config
│   ├── model.sdf
│   ├── heightmaps/
│   │   ├── terrain_heightmap_1024_gray16.png  # 현재 사용 중
│   │   ├── rough_terrain.png
│   │   ├── rough_terrain_8bit.png
│   │   └── rough_terrain_16bit.png
│   └── textures/
│       ├── dirt.png
│       ├── dirt_realistic.png
│       ├── dirt_realistic_normal.png
│       └── flat_normal.png
├── config/
│   ├── husky/
│   │   ├── robot.yaml
│   │   └── ouster_128_bridge.yaml
│   └── jackal/
│       └── robot.yaml
├── urdf/
│   ├── husky_ouster_os1_128.urdf.xacro
│   └── fwmax_skid_steer.urdf.xacro
├── rviz/
│   └── vis.rviz
├── rough_terrain_sim/
│   ├── __init__.py
│   ├── generate_heightmap.py
│   ├── generate_heightmap_16bit.py
│   └── camera_pointcloud_frame_fix.py
├── resource/
│   └── rough_terrain_sim
└── sample/
    └── sample.png
```
