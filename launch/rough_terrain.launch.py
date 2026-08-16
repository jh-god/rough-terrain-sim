"""Launch the 50 m x 50 m rough-terrain world in Gazebo Fortress."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition, LaunchConfigurationEquals
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    EnvironmentVariable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory('rough_terrain_sim')
    world_path = os.path.join(package_share, 'worlds', 'rough_terrain.sdf')
    rviz_config_path = os.path.join(package_share, 'rviz', 'vis.rviz')
    fwmax_xacro_path = os.path.join(
        package_share, 'urdf', 'fwmax_skid_steer.urdf.xacro')
    models_path = os.path.join(package_share, 'models')
    husky_setup_path = os.path.join(package_share, 'config', 'husky')
    ouster_bridge_config = os.path.join(
        husky_setup_path, 'ouster_128_bridge.yaml')
    jackal_setup_path = os.path.join(package_share, 'config', 'jackal')
    gazebo_args = [
        '-r ',
        '-v 3 ',
        world_path,
    ]
    fwmax_robot_description = Command(['xacro ', fwmax_xacro_path])

    husky_spawn = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                get_package_share_directory('clearpath_gz'),
                'launch',
                'robot_spawn.launch.py',
            ])
        ),
        launch_arguments={
            'setup_path': husky_setup_path,
            'world': 'rough_terrain_world',
            'x': LaunchConfiguration('robot_x'),
            'y': LaunchConfiguration('robot_y'),
            # Spawn above the terrain and let physics settle the Husky
            # naturally. The required z value depends on the loaded heightmap
            # and the height range configured in the terrain model SDF.
            'z': LaunchConfiguration('robot_z'),
            'yaw': LaunchConfiguration('robot_yaw'),
            'generate': 'true',
            # This package starts RViz with its own sim.rviz configuration.
            # Keep Clearpath's default RViz disabled to avoid two windows.
            'rviz': 'false',
        }.items(),
        condition=LaunchConfigurationEquals('robot', 'husky'),
    )

    jackal_spawn = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                get_package_share_directory('clearpath_gz'),
                'launch',
                'robot_spawn.launch.py',
            ])
        ),
        launch_arguments={
            'setup_path': jackal_setup_path,
            'world': 'rough_terrain_world',
            'x': LaunchConfiguration('robot_x'),
            'y': LaunchConfiguration('robot_y'),
            'z': LaunchConfiguration('robot_z'),
            'yaw': LaunchConfiguration('robot_yaw'),
            'generate': 'true',
            'rviz': 'false',
        }.items(),
        condition=LaunchConfigurationEquals('robot', 'jackal'),
    )

    fwmax_spawn = Node(
        package='ros_gz_sim',
        executable='create',
        name='fwmax_spawn',
        output='screen',
        arguments=[
            '-world', 'rough_terrain_world',
            '-name', 'fwmax',
            '-x', LaunchConfiguration('robot_x'),
            '-y', LaunchConfiguration('robot_y'),
            '-z', LaunchConfiguration('robot_z'),
            '-Y', LaunchConfiguration('robot_yaw'),
            '-topic', 'robot_description',
        ],
        condition=LaunchConfigurationEquals('robot', 'fwmax'),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'robot', default_value='husky',
            choices=['husky', 'jackal', 'fwmax', 'none'],
            description=(
                'Robot to spawn: Clearpath Husky A200, Jackal J100, '
                'FW-max skid-steer approximation, or none.'
            ),
        ),
        DeclareLaunchArgument(
            'rviz', default_value='true',
            description='Start RViz2 with the package simulation configuration.',
        ),
        # The bundled heightmap is steep around its centre. These defaults
        # place the robot on a low-slope patch before it enters rough terrain.
        DeclareLaunchArgument('robot_x', default_value='-7.2', description='Robot spawn x position in metres.'),
        DeclareLaunchArgument('robot_y', default_value='-3.2', description='Robot spawn y position in metres.'),
        DeclareLaunchArgument(
            'robot_z', default_value='4.2',
            description='Robot spawn z position in metres.',
        ),
        DeclareLaunchArgument('robot_yaw', default_value='0.0', description='Robot spawn yaw in radians.'),
        # Fortress accepts both variable names. Set both so this launch file also
        # works when invoked directly outside the ros_gz_sim path discovery flow.
        SetEnvironmentVariable(
            name='IGN_GAZEBO_RESOURCE_PATH',
            value=[EnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', default_value=''), ':', models_path],
        ),
        SetEnvironmentVariable(
            name='GZ_SIM_RESOURCE_PATH',
            value=[EnvironmentVariable('GZ_SIM_RESOURCE_PATH', default_value=''), ':', models_path],
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([
                    get_package_share_directory('ros_gz_sim'),
                    'launch',
                    'gz_sim.launch.py',
                ])
            ),
            launch_arguments={
                'gz_args': gazebo_args,
                'gz_version': '6',
            }.items(),
        ),
        # Clearpath's controllers run with use_sim_time=True. Bridge the
        # Fortress simulation clock so their command timeouts and update loop
        # advance in this custom world just as they do in clearpath_gz's
        # standard simulation launch.
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='clock_bridge',
            output='screen',
            arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'],
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='fwmax_robot_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'robot_description': fwmax_robot_description,
            }],
            condition=LaunchConfigurationEquals('robot', 'fwmax'),
        ),
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='fwmax_gz_bridge',
            output='screen',
            arguments=[
                '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
                '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
                '/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
                (
                    '/world/rough_terrain_world/model/fwmax/joint_state'
                    '@sensor_msgs/msg/JointState[ignition.msgs.Model'
                ),
            ],
            remappings=[
                (
                    '/world/rough_terrain_world/model/fwmax/joint_state',
                    '/joint_states',
                ),
            ],
            parameters=[{'use_sim_time': True}],
            condition=LaunchConfigurationEquals('robot', 'fwmax'),
        ),
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='ouster_128_gz_bridge',
            namespace='sensors',
            output='screen',
            parameters=[
                {
                    'use_sim_time': True,
                    'config_file': ouster_bridge_config,
                },
            ],
            condition=LaunchConfigurationEquals('robot', 'husky'),
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='ouster_128_static_tf',
            output='screen',
            arguments=[
                '--frame-id', 'lidar3d_0_link',
                '--child-frame-id', 'robot/base_link/lidar3d_0',
            ],
            parameters=[{'use_sim_time': True}],
            condition=LaunchConfigurationEquals('robot', 'husky'),
        ),
        Node(
            package='rough_terrain_sim',
            executable='camera_pointcloud_frame_fix',
            name='camera_pointcloud_frame_fix',
            output='screen',
            parameters=[{'use_sim_time': True}],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_path],
            parameters=[{'use_sim_time': True}],
            condition=IfCondition(LaunchConfiguration('rviz')),
        ),
        TimerAction(
            period=3.0,
            actions=[husky_spawn, jackal_spawn, fwmax_spawn],
        ),
    ])
