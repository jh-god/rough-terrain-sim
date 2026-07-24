"""Launch the 20 m x 20 m rough-terrain world in Gazebo Fortress."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import LaunchConfigurationEquals
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory('rough_terrain_sim')
    world_path = os.path.join(package_share, 'worlds', 'rough_terrain.sdf')
    models_path = os.path.join(package_share, 'models')
    husky_setup_path = os.path.join(package_share, 'config', 'husky')
    jackal_setup_path = os.path.join(package_share, 'config', 'jackal')
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
        }.items(),
        condition=LaunchConfigurationEquals('robot', 'jackal'),
    )

    initial_camera = ExecuteProcess(
        cmd=[
            'ign', 'topic',
            '-t', '/gui/camera/view_control',
            '-m', 'ignition.msgs.GUICamera',
            '-p', (
                'pose { position { x: -14.0 y: -5.5 z: 7.0 } '
                'orientation { y: 0.319309 w: 0.947651 } } '
                'view_controller: "orbit"'
            ),
        ],
        output='log',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'robot', default_value='husky',
            choices=['husky', 'jackal', 'none'],
            description='Robot to spawn: Clearpath Husky A200, Jackal J100, or none.',
        ),
        # The bundled heightmap is steep around its centre. These defaults
        # place the robot on a low-slope patch before it enters rough terrain.
        DeclareLaunchArgument('robot_x', default_value='-7.2', description='Robot spawn x position in metres.'),
        DeclareLaunchArgument('robot_y', default_value='-3.2', description='Robot spawn y position in metres.'),
        DeclareLaunchArgument(
            'robot_z', default_value='1.8',
            description='Robot spawn z position in ㅇmetres.',
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
        # The default GUI camera faces the world origin. Move it to an orbit
        # view that looks towards the default spawn pose before the robot is
        # created three seconds later.
        TimerAction(period=1.5, actions=[initial_camera]),
        TimerAction(
            period=3.0,
            actions=[husky_spawn, jackal_spawn],
        ),
    ])
