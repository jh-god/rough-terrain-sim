"""Launch the 20 m x 20 m rough-terrain world in Gazebo Fortress."""

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
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory('rough_terrain_sim')
    world_path = os.path.join(package_share, 'worlds', 'rough_terrain.sdf')
    rviz_config_path = os.path.join(package_share, 'rviz', 'vis.rviz')
    models_path = os.path.join(package_share, 'models')
    husky_setup_path = os.path.join(package_share, 'config', 'husky')
    ouster_bridge_config = os.path.join(
        husky_setup_path, 'ouster_128_bridge.yaml')
    jackal_setup_path = os.path.join(package_share, 'config', 'jackal')
    bunker_description_share = get_package_share_directory(
        'bunker_description')
    bunker_xacro_path = os.path.join(
        bunker_description_share, 'urdf', 'bunker.xacro')
    bunker_resource_path = os.path.dirname(bunker_description_share)
    bunker_robot_description = Command([
        FindExecutable(name='xacro'),
        ' ',
        bunker_xacro_path,
    ])
    gazebo_args = [
        '-r ',
        '-v 3 ',
        world_path,
    ]

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
            # The terrain's maximum height is 2 m; spawn above it and let
            # physics settle the Husky naturally onto the ground.
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

    bunker_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        namespace='bunker',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': bunker_robot_description,
            'use_sim_time': True,
        }],
        condition=LaunchConfigurationEquals('robot', 'bunker'),
    )

    bunker_spawn = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-topic', '/bunker/robot_description',
            '-name', 'bunker',
            '-x', LaunchConfiguration('robot_x'),
            '-y', LaunchConfiguration('robot_y'),
            '-z', LaunchConfiguration('robot_z'),
            '-Y', LaunchConfiguration('robot_yaw'),
        ],
        condition=LaunchConfigurationEquals('robot', 'bunker'),
    )

    bunker_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='bunker_gz_bridge',
        output='screen',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
            '/joint_states@sensor_msgs/msg/JointState[ignition.msgs.Model',
        ],
        remappings=[
            ('/cmd_vel', '/platform/cmd_vel'),
            ('/odom', '/platform/odom'),
            ('/joint_states', '/platform/joint_states'),
        ],
        parameters=[{'use_sim_time': True}],
        condition=LaunchConfigurationEquals('robot', 'bunker'),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'robot', default_value='husky',
            choices=['husky', 'jackal', 'bunker', 'none'],
            description=(
                'Robot to spawn: Clearpath Husky A200, Jackal J100, '
                'AgileX BUNKER, or none.'
            ),
        ),
        DeclareLaunchArgument(
            'rviz', default_value='true',
            description='Start RViz2 with the package simulation configuration.',
        ),
        # The bundled heightmap is steep around its centre. These defaults
        # place the robot on a low-slope patch before it enters rough terrain.
        DeclareLaunchArgument('robot_x', default_value='-7.2', description='Robot spawn x position in metres.'),
        DeclareLaunchArgument('robot_y', default_value='-5.5', description='Robot spawn y position in metres.'),
        DeclareLaunchArgument(
            'robot_z', default_value='3.2',
            description='Robot spawn z position in metres.',
        ),
        DeclareLaunchArgument('robot_yaw', default_value='0.0', description='Robot spawn yaw in radians.'),
        # Fortress accepts both variable names. Set both so this launch file also
        # works when invoked directly outside the ros_gz_sim path discovery flow.
        SetEnvironmentVariable(
            name='IGN_GAZEBO_RESOURCE_PATH',
            value=[
                EnvironmentVariable(
                    'IGN_GAZEBO_RESOURCE_PATH', default_value=''),
                ':', models_path,
                ':', bunker_resource_path,
            ],
        ),
        SetEnvironmentVariable(
            name='GZ_SIM_RESOURCE_PATH',
            value=[
                EnvironmentVariable(
                    'GZ_SIM_RESOURCE_PATH', default_value=''),
                ':', models_path,
                ':', bunker_resource_path,
            ],
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
        bunker_state_publisher,
        bunker_bridge,
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
            actions=[husky_spawn, jackal_spawn, bunker_spawn],
        ),
    ])
