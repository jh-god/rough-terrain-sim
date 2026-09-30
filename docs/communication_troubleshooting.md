# ROS 2 센서 통신 문제 해결

[README로 돌아가기](../README.md)

Gazebo 센서 데이터가 끊기거나, RViz 표시가 늦거나, `ros2 topic hz`가 거의
출력되지 않을 때 사용하는 점검 안내입니다. ROS 2 Humble과 CycloneDDS 환경을
기준으로 하며, 아래 도메인 번호와 버퍼 크기는 이 환경에서 검증한 **예시**입니다.
모든 사용자에게 필요한 설정이나 하드 실시간 동작을 보장하는 설정은 아닙니다.

## 1. 점검 순서

1. 시뮬레이터, RViz, 진단 터미널의 ROS 환경이 같은지 확인합니다.
2. 외부 노드가 섞여 있지 않은지, `/clock` 발행자가 하나인지 확인합니다.
3. UDP 수신 버퍼 드롭이 증가하는지 확인하고, 필요할 때만 버퍼를 조정합니다.
4. 큰 센서 토픽은 하나씩 실제 수신 주기와 지연을 측정합니다.
5. 정상 동작을 확인한 설정만 영구 적용합니다.

설정 변경 전에는 기존 값을 기록해 두세요.

```bash
printenv ROS_DOMAIN_ID ROS_LOCALHOST_ONLY RMW_IMPLEMENTATION CYCLONEDDS_URI
sysctl net.core.rmem_max net.core.rmem_default
```

`printenv`에 표시되지 않는 변수는 현재 셸에 설정되지 않은 변수입니다.
실행 중인 노드는 이 터미널과 다른 환경을 물려받았을 수도 있습니다.

## 2. ROS 통신 영역과 `/clock` 확인

```bash
ros2 node list
ros2 topic info /clock --verbose
```

이 패키지로 시뮬레이션 하나만 실행했다면 `/clock`은 보통 `clock_bridge` 하나가
발행해야 합니다. `Publisher count: 1`인지, 발행 노드가 예상한 노드인지 확인합니다.
다른 시뮬레이터나 외부 노드가 같은 도메인에 있으면 의도하지 않은 토픽과 시간이
섞일 수 있습니다. `topic info`는 통신 상대의 발견 여부를 보여 주며, 실제 데이터가
정상 수신된다는 증거는 아닙니다.

외부 노드가 보인다면 사용하지 않는 도메인을 정하고, 시뮬레이션에 참여하는
**모든 터미널**에서 동일하게 설정합니다. 아래의 `5`는 예시입니다.

```bash
export ROS_DOMAIN_ID=5
export ROS_LOCALHOST_ONLY=0
```

도메인을 변경한 뒤에는 기존 시뮬레이션과 RViz를 종료하고, 새 환경이 적용된
터미널에서 다시 실행합니다. 기존 CLI daemon의 환경이 달랐다면 해당 환경에서
`ros2 daemon stop`으로 종료한 뒤 새 환경에서 CLI를 다시 사용합니다.

서로 다른 도메인은 일반적인 DDS 발견·통신 영역을 분리하지만 보안 경계는
아닙니다. 여러 PC를 연결할 때는 참여 PC의 도메인을 맞추고 네트워크 설정도
확인해야 합니다. [ROS 2 Domain ID 안내](https://docs.ros.org/en/humble/Concepts/Intermediate/About-Domain-ID.html)

### `ROS_LOCALHOST_ONLY=1`에서 로봇이 spawn되지 않는 경우

로컬 통신만 허용하는 설정 자체가 잘못된 것은 아닙니다. 다만 이 환경의
CycloneDDS 0.10.5에서는 다음 로그와 함께 노드 생성이 실패했습니다.

```text
selected interface "lo" is not multicast-capable: disabling multicast
Failed to find a free participant index for domain ...
```

이 경우는 `/clock` 중복 발행 문제가 아니라 DDS participant 할당 문제입니다.
이 설치본의 기본 `MaxAutoParticipantIndex`는 `9`였으며, multicast를 사용할 수
없는 조건에서 자동 할당 범위가 부족해질 수 있습니다. 이는 “ROS 노드는 최대
10개”라는 뜻은 아닙니다. 한 프로세스의 participant와 ROS 노드는 같은 개념이
아니며, 기본값과 동작도 버전·설정에 따라 다릅니다.

이 환경에서는 별도 도메인을 유지하면서 `ROS_LOCALHOST_ONLY=0`으로 실행해
spawn을 정상화했습니다. 반드시 localhost로 제한해야 한다면 해당 버전의
participant 범위와 discovery 설정을 별도로 검토하세요.
[CycloneDDS 관련 이슈](https://github.com/eclipse-cyclonedds/cyclonedds/issues/1400)

## 3. Linux UDP 수신 버퍼 확인 및 임시 조정

먼저 시뮬레이션 실행 중 드롭이 계속 증가하는지 확인합니다.

```bash
nstat -az UdpRcvbufErrors
ss -u -a -n -m -p
```

몇 초 뒤 다시 실행해서 차이를 비교합니다. `nstat`의 값은 시스템 전체의 누적
카운터이므로, 큰 값 하나만 보고 현재 ROS 문제라고 판단하면 안 됩니다.
`ss`에서는 RViz나 point cloud 처리 프로세스의 소켓을 찾아 `skmem`의 `rb`
(수신 버퍼 한도)와 `d`(드롭 카운터)를 확인합니다. 다른 사용자의 프로세스 정보는
권한에 따라 보이지 않을 수 있습니다. `Recv-Q`가 순간적으로 0인 것만으로는
드롭이 없었다고 판단할 수 없습니다.

이 환경에서는 기존 `net.core.rmem_max=212992` 상태에서 큰 point cloud를
받는 프로세스의 UDP 드롭 증가가 관찰되었습니다. 다음 설정으로 수신 버퍼
상한을 32 MiB로 늘렸습니다. 시스템 전체에 적용되는 관리자 설정입니다.

```bash
sudo sysctl -w net.core.rmem_max=33554432
```

이 값은 소켓별 요청 가능한 상한이며, 모든 소켓에 즉시 32 MiB씩 할당하는
설정은 아닙니다. 실제 메모리 사용은 늘어날 수 있습니다. 여기서는 CycloneDDS가
버퍼를 명시적으로 요청하므로 `net.core.rmem_default`는 변경하지 않습니다.

### CycloneDDS에도 버퍼 크기 요청

`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`를 지정하는 것만으로 아래 버퍼 설정이
적용되지는 않습니다. 다음 예시는 CycloneDDS를 사용하는 경우에만 해당합니다.
다른 RMW를 사용하는 환경에서 이 절차 때문에 무조건 RMW를 바꿀 필요는 없습니다.

설정 파일을 엽니다. 기존 파일이나 `CYCLONEDDS_URI`가 있다면 덮어쓰지 말고
현재 설정에 필요한 항목만 병합하세요.

```bash
mkdir -p ~/.config/cyclonedds
nano ~/.config/cyclonedds/ros2.xml
```

새 파일의 최소 예시는 다음과 같습니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CycloneDDS xmlns="https://cdds.io/config">
  <Domain Id="any">
    <Internal>
      <SocketReceiveBufferSize min="16MiB"/>
    </Internal>
  </Domain>
</CycloneDDS>
```

이 환경에서 사용한 CycloneDDS 0.10.5 형식입니다. XML 대소문자를 지키고,
다른 버전에서 파싱 오류가 발생하면 해당 버전의 설정 문서를 확인하세요.
`min`은 최소 요구 크기이므로 OS에서 확보할 수 없다면 초기화가 실패할 수 있습니다.

시뮬레이션, RViz 및 진단 도구를 실행할 터미널에 적용합니다.

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://${HOME}/.config/cyclonedds/ros2.xml"
```

환경변수는 이미 실행 중인 프로세스에 적용되지 않습니다. 관련 노드를 모두
종료한 뒤 위 설정을 가진 터미널에서 다시 실행해야 합니다. 진단 도구도 같은
설정을 사용해야 측정 도구 자체의 작은 버퍼가 병목이 되는 것을 피할 수 있습니다.

Linux는 소켓 수신 버퍼를 내부 회계상 두 배로 표시할 수 있습니다. 이 환경에서는
16 MiB 요청 후 `ss`에 `rb33554432`가 표시되었습니다. 재실행 후에는 버퍼 값뿐
아니라 드롭 증가 여부와 실제 센서 수신 상태도 다시 확인합니다.
상한을 계속 올리는 대신, 드롭이 남으면 센서 데이터량·CPU 부하·수신 처리 속도도
함께 점검하세요. [ROS 2 DDS 튜닝 안내](https://docs.ros.org/en/humble/How-To-Guides/DDS-tuning.html)

## 4. 실제 수신 주기와 지연 측정

### `topic hz`만으로 판단하지 않기

```bash
ros2 topic info /sensors/lidar3d_0/points --verbose
ros2 topic hz /sensors/lidar3d_0/points --window 100
```

이 환경의 Humble `topic hz`는 Sensor Data QoS의 Best Effort 구독을 사용했고,
QoS를 바꾸는 CLI 옵션이 없었습니다. 버전별 옵션은 `ros2 topic hz --help`로
확인하세요. `--window 100`은 통계에 사용하는 표본 수이지, 최초 출력 전에
반드시 100개를 기다리는 옵션이 아닙니다.

여기서 센서 발행자와 RViz는 Reliable이었으며, `topic hz`가 거의 출력되지 않아도
별도의 Reliable 구독에서는 정상 수신을 확인했습니다. **Reliable 발행자와
Best Effort 구독자는 QoS 호환 관계**이므로 이 현상을 곧바로 QoS 불일치라고
부르면 안 됩니다. 구독 조건, 대용량 메시지의 패킷 손실, 측정 도구 부하 등을
구분해야 합니다. 서로 다른 depth 값도 그 자체로 호환성 오류는 아닙니다.
[ROS 2 QoS 호환성 안내](https://docs.ros.org/en/humble/Concepts/Intermediate/About-Quality-of-Service-Settings.html)

또한 `topic hz`를 Ctrl+C로 종료한 뒤 `topic info`를 실행하면 해당 진단 구독자가
목록에서 사라지는 것은 정상입니다. 전체 point cloud 내용을 터미널에 출력하거나
여러 측정 도구를 동시에 실행하면 진단 자체가 추가 부하를 만듭니다.

### Reliable 구독으로 측정하기

다음 코드는 파일을 추가하지 않고 실행하는 일회성 진단입니다. 발행자가
Reliable인지 먼저 확인하세요. Best Effort 발행자는 이 Reliable 구독과 호환되지
않습니다. 시뮬레이션을 실행하고 초기 로딩이 끝난 뒤, 같은 ROS 환경의 터미널에서
**토픽 하나씩** 측정합니다. 필요하면 workspace 경로를 바꾸세요.

```bash
source /opt/ros/humble/setup.bash
source ~/gazebo_ws/install/setup.bash
/usr/bin/python3 - /sensors/lidar3d_0/points <<'PY'
import statistics
import sys
import time

import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2

topic = sys.argv[1]
rclpy.init(args=[])
node = rclpy.create_node('sensor_delay_probe')
latest_clock = None
clock_received = None
clock_first = None
clock_last = None
samples = []
start = time.monotonic()

def on_clock(msg):
    global latest_clock, clock_received, clock_first, clock_last
    now = time.monotonic()
    latest_clock = msg.clock.sec + msg.clock.nanosec * 1e-9
    clock_received = now
    if now - start >= 2:
        clock_last = (now, latest_clock)
        if clock_first is None:
            clock_first = clock_last

def on_cloud(msg):
    now = time.monotonic()
    if now - start < 2:
        return
    stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
    delay = None
    if clock_received is not None and now - clock_received < 0.2:
        delay = (latest_clock - stamp) * 1000
    samples.append((now, delay))

clock_sub = node.create_subscription(
    Clock, '/clock', on_clock,
    QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))
cloud_sub = node.create_subscription(
    PointCloud2, topic, on_cloud,
    QoSProfile(depth=5, reliability=ReliabilityPolicy.RELIABLE))

print(f'Measuring {topic}: 2 s warm-up + 20 s measurement', flush=True)
try:
    while time.monotonic() - start < 22:
        rclpy.spin_once(node, timeout_sec=0.1)
    print(f'Received: {len(samples)} messages')
    if len(samples) >= 2:
        span = samples[-1][0] - samples[0][0]
        gaps = [(b[0] - a[0]) * 1000
                for a, b in zip(samples, samples[1:])]
        if span > 0:
            print(f'Wall-time rate: {(len(samples)-1)/span:.2f} Hz')
        print(f'Max arrival gap: {max(gaps):.1f} ms')
    delays = sorted(d for _, d in samples if d is not None)
    if delays:
        print(f'Delay mean: {statistics.mean(delays):.1f} ms')
        print(f'Delay p95:  {delays[int((len(delays)-1)*0.95)]:.1f} ms')
        print(f'Delay max:  {max(delays):.1f} ms')
    else:
        print('Delay unavailable: no usable cloud/clock pairs')
    print(f'Samples without fresh clock: {len(samples)-len(delays)}')
    if clock_first and clock_last[0] > clock_first[0]:
        rtf = ((clock_last[1] - clock_first[1]) /
               (clock_last[0] - clock_first[0]))
        print(f'Observed clock RTF: {rtf:.3f}')
except KeyboardInterrupt:
    pass
finally:
    node.destroy_node()
    rclpy.shutdown()
PY
```

카메라를 검사하려면 위 명령의 `/sensors/lidar3d_0/points`를
`/sensors/camera_0/points`, `/sensors/camera_0/points_aligned`로 각각 바꿔
한 번씩 실행합니다. 로봇이나 센서 설정에 따라 토픽 이름이 다르므로
`ros2 topic list`로 실제 이름을 확인하세요.

결과는 다음과 같이 해석합니다.

- `Wall-time rate`: 실제 벽시계 시간 기준 수신 빈도입니다.
- `Max arrival gap`: 연속 수신 사이의 가장 긴 간격입니다. 평균 주기가 정상이어도
  이 값이 크면 중간에 끊김이 있었을 수 있습니다.
- `Delay`: 최근 수신한 `/clock`에서 센서 `header.stamp`를 뺀 값입니다.
  시뮬레이션 시간 기준의 근사 데이터 나이이며, 네트워크만의 지연이나 RViz 화면
  표시 지연은 아닙니다. 시뮬레이션 stamp에서 PC의 epoch 시간을 직접 빼면 안 됩니다.
- `Samples without fresh clock`: 최근 0.2초 안에 `/clock`을 수신하지 못해
  지연 계산에서 제외한 표본 수입니다. 이 값이 많으면 `/clock`부터 점검합니다.
- `Observed clock RTF`: 수신한 시뮬레이션 시간의 진행량 / 실제 시간의 진행량입니다.
  센서 설정이 시뮬레이션 시간 기준 10 Hz이고 RTF가 0.98이면 실제 약 9.8 Hz 수신은
  자연스러운 결과입니다.

`/clock`과 센서 콜백의 도착 순서 때문에 작은 음수 지연이 나올 수 있습니다.
이 코드는 최신 수신 clock을 사용하는 간이 측정이므로, clock 자체가 지연되면
지연과 RTF 추정도 부정확해질 수 있습니다. 측정 중 일시정지·월드 리셋·시간 역행이
있었다면 해당 결과를 버리고 다시 측정하세요. 시뮬레이터의 RTF와 비교하고,
단일 20초 측정만으로 장시간 무손실을 보장하지는 마세요.

### 이 환경에서 정상화 후 확인한 예시

LiDAR 설정 10 Hz에 대해 다음 결과를 얻었습니다.

```text
Received: 195 messages
Wall-time rate: 9.77 Hz
Max arrival gap: 126.1 ms
Delay mean: 17.2 ms
Delay p95:  25.0 ms
Delay max:  34.0 ms
Samples without fresh clock: 0
Observed clock RTF: 0.977
```

`10 × 0.977 ≈ 9.77 Hz`로 기대 수신 빈도와 일치하며, 이 측정 구간에서는 큰
지연 누적이 관찰되지 않았습니다. 카메라 원본 및 정렬 point cloud도 별도 측정에서
정상 수신을 확인했습니다. 위 수치는 합격 기준이 아니라 해당 실행의 참고값입니다.

이번 문제에서는 서로 다른 항목을 구분해 해결했습니다.

| 관찰한 현상 | 조치와 확인 |
| --- | --- |
| 예상하지 않은 외부 노드와 추가 `/clock` 발행자 관찰 | 별도 ROS 도메인 사용 후 예상한 노드와 단일 `/clock` 확인 |
| localhost 제한 시 participant 할당 실패 및 spawn 실패 | 별도 도메인을 유지하고 `ROS_LOCALHOST_ONLY=0`으로 재실행 |
| 대용량 센서 수신 프로세스에서 UDP 수신 드롭 증가 | Linux 수신 버퍼 상한과 CycloneDDS 요청 크기를 함께 조정 후 재확인 |
| `topic hz` 출력이 거의 없음 | 실제 소비자와 같은 Reliable 조건으로 수신 빈도·지연을 별도 측정 |

외부 발행자의 정확한 출처나 모든 증상의 단일 원인을 확정한 것은 아닙니다.
정상화 과정에서 센서 모델이나 패키지의 운영 QoS 코드는 변경하지 않았습니다.
추가 진단 구독 등 부하 조건이 달라지면 드롭이 재발할 수 있으므로 실제 사용할
노드를 함께 실행한 상태에서도 확인하세요. 수신 지표가 정상인데 RViz만 늦으면
그다음에는 TF, 렌더링 부하, RViz 표시 설정을 분리해서 점검합니다.

## 5. 새 터미널과 재부팅 후에도 유지하기

임시 설정으로 정상 동작을 확인한 뒤 적용합니다.

### Linux 설정

별도 설정 파일을 엽니다. 이미 파일이 있다면 기존 내용을 보존합니다.

```bash
sudo nano /etc/sysctl.d/90-ros2-udp-buffer.conf
```

다음 한 줄을 추가합니다.

```ini
net.core.rmem_max = 33554432
```

현재 실행에도 적용하고 확인합니다.

```bash
sudo sysctl -p /etc/sysctl.d/90-ros2-udp-buffer.conf
sysctl net.core.rmem_max
```

다른 sysctl 설정 파일에서 같은 값을 덮어쓸 수 있으므로 재부팅 후에도 실제 값을
확인하세요.

### ROS 환경변수

`~/.bashrc`의 기존 ROS 환경 설정 부분에 다음 내용을 추가하거나 기존 값을
수정합니다. 이미 있는 항목을 중복 추가하지 말고, 도메인 번호는 환경에 맞게
선택하세요. XML 파일은 3절에서 작성한 파일을 그대로 사용합니다.

```bash
export ROS_DOMAIN_ID=5
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://${HOME}/.config/cyclonedds/ros2.xml"
```

새 터미널을 열거나 `source ~/.bashrc`를 실행한 다음 관련 노드를 재시작합니다.
`.bashrc`는 대화형 Bash용이므로 systemd 서비스, 컨테이너, IDE에서 실행하는
프로세스에는 해당 실행 환경에 별도 설정이 필요할 수 있습니다.

재부팅 후 확인할 항목은 다음과 같습니다.

```bash
printenv ROS_DOMAIN_ID ROS_LOCALHOST_ONLY RMW_IMPLEMENTATION CYCLONEDDS_URI
sysctl net.core.rmem_max
```

시뮬레이션 실행 후에는 `/clock` 발행자, 소켓 버퍼와 드롭 증가 여부, 센서 수신
주기·지연까지 다시 확인합니다. 패키지를 다시 빌드할 필요는 없습니다.

## 6. 원복하기

1. 시뮬레이션, RViz와 진단 도구를 종료합니다.
2. `~/.bashrc`에서 이번에 추가한 항목만 제거하거나 기존 값으로 복원합니다.
   기존 CycloneDDS XML이 있었다면 추가한 버퍼 항목만 원복합니다.
3. 현재 셸에도 기존 환경변수 값을 복원합니다. 원래 `CYCLONEDDS_URI`가 없었다면
   `unset CYCLONEDDS_URI`를 사용합니다. `.bashrc`에서 줄을 지우고 다시 source하는
   것만으로는 현재 셸의 기존 export 값이 없어지지 않습니다.
4. `/etc/sysctl.d/90-ros2-udp-buffer.conf`에서 이번에 추가한 항목만 제거하거나
   기존 값으로 복원합니다. 다른 항목은 보존합니다.
5. `sudo sysctl -w net.core.rmem_max=기록해둔_기존값` 형식으로 실제 숫자를 넣어
   현재 커널 값도 복원합니다. `212992`는 이번 환경의 변경 전 값일 뿐,
   모든 시스템의 원래 값은 아닙니다.
6. 복원된 환경에서 노드를 다시 실행합니다.

sysctl 설정 파일을 지우거나 수정하는 것만으로 현재 커널 값이 되돌아가지는
않습니다. 또한 CycloneDDS의 큰 최소 버퍼 요청을 남겨 둔 채 커널 상한부터 낮추면
다음 실행이 실패할 수 있으므로, XML과 환경변수도 함께 원복하세요.
