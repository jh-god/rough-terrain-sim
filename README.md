# rough_terrain_sim

ROS 2 Humble과 Gazebo Fortress용 울퉁불퉁한 노면 시뮬레이션 패키지입니다.
20 m × 20 m PNG heightmap 지형을 불러오며, Clearpath Husky A200 또는
Jackal J100을 선택해 스폰할 수 있습니다.

## 요구 사항

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Fortress (`ign gazebo` / Gazebo Sim 6)
- Clearpath simulator

Clearpath 로봇을 사용하려면 다음 패키지가 설치되어 있어야 합니다.

```bash
sudo apt update
sudo apt install ros-humble-clearpath-simulator
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

기본값은 Husky A200입니다.

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

Husky:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/a200_0000/platform/cmd_vel_unstamped
```

Jackal:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/j100_0000/platform/cmd_vel_unstamped
```

teleop을 실행한 터미널에 포커스를 둔 뒤 `i`, `,`, `j`, `l` 키로 조작합니다.

## Heightmap 생성

NumPy와 Pillow 기반 생성기는 257 × 257, 8-bit grayscale PNG를 만듭니다.
같은 파라미터와 `seed`는 동일한 결과를 생성합니다.

```bash
ros2 run rough_terrain_sim generate_rough_heightmap \
  --seed 42 \
  --width-m 20 --height-m 20 \
  --max-elevation-m 2 \
  --roughness 0.65 \
  --smoothing-sigma 0.30 \
  --output ~/ros2_ws/src/rough_terrain_sim/models/rough_terrain/heightmaps/rough_terrain.png
```

생성 후 빌드하고 Gazebo를 재시작합니다.

```bash
cd ~/ros2_ws
colcon build --packages-select rough_terrain_sim --symlink-install
source install/setup.bash
```

지형 물리 크기와 높이 범위는
`models/rough_terrain/model.sdf`의 `<size>20 20 2</size>`에서 정합니다.

## 노면 마찰과 wheel slip

지형의 ODE 마찰계수는 `models/rough_terrain/model.sdf`에 있습니다.

```xml
<mu>1.0</mu>
<mu2>1.0</mu2>
```

건조 아스팔트 느낌의 시작점으로는 `1.0 ~ 1.2`가 적당합니다. 이 값은
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

## 노면 시각 재질

지형은 `models/rough_terrain/textures/dirt_realistic.png`의 흙 diffuse
텍스처와 `dirt_realistic_normal.png`의 normal map을 사용합니다. 텍스처
반복 간격은 `models/rough_terrain/model.sdf`의 `<texture><size>`이며,
기본값 `6`은 6 m마다 한 번 반복한다는 뜻입니다. 값이 작을수록 질감이
더 촘촘하게 보입니다.

## 패키지 구조

```text
rough_terrain_sim/
├── launch/rough_terrain.launch.py
├── worlds/rough_terrain.sdf
├── models/rough_terrain/
│   ├── model.sdf
│   ├── heightmaps/rough_terrain.png
│   └── textures/
├── config/husky/robot.yaml
├── config/jackal/robot.yaml
└── rough_terrain_sim/generate_heightmap.py
```
