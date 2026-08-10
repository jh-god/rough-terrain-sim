from glob import glob
import os

from setuptools import find_packages, setup


package_name = 'rough_terrain_sim'


def model_data_files():
    """Install every Gazebo model and its nested assets."""
    data_files = []
    for directory, _, filenames in os.walk('models'):
        if not filenames:
            continue
        sources = [
            os.path.join(directory, filename)
            for filename in filenames
            if os.path.isfile(os.path.join(directory, filename))
        ]
        if not sources:
            continue
        destination = os.path.join('share', package_name, directory)
        data_files.append((destination, sources))
    return data_files


setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config', 'husky'), glob('config/husky/*.yaml')),
        (os.path.join('share', package_name, 'config', 'jackal'), glob('config/jackal/*.yaml')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.xacro')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')),
    ] + model_data_files(),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rough_terrain_sim maintainer',
    maintainer_email='maintainer@example.com',
    description='Gazebo Fortress rough-terrain simulation environment for ROS 2 Humble.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'generate_rough_heightmap = rough_terrain_sim.generate_heightmap:main',
            'generate_rough_heightmap_16bit = '
            'rough_terrain_sim.generate_heightmap_16bit:main',
            'camera_pointcloud_frame_fix = '
            'rough_terrain_sim.camera_pointcloud_frame_fix:main',
        ],
    },
)
