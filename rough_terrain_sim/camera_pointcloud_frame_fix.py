"""Correct the frame ID of the simulated RGB-D camera point cloud."""

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from sensor_msgs.msg import PointCloud2


class CameraPointCloudFrameFix(Node):
    """Republish the camera cloud using the frame its point data follows."""

    def __init__(self):
        super().__init__('camera_pointcloud_frame_fix')

        self.declare_parameter('input_topic', '/sensors/camera_0/points')
        self.declare_parameter(
            'output_topic', '/sensors/camera_0/points_aligned')
        self.declare_parameter(
            'input_frame', 'camera_0_color_optical_frame')
        self.declare_parameter('output_frame', 'camera_0_link')

        input_topic = self.get_parameter(
            'input_topic').get_parameter_value().string_value
        output_topic = self.get_parameter(
            'output_topic').get_parameter_value().string_value
        self.input_frame = self.get_parameter(
            'input_frame').get_parameter_value().string_value
        self.output_frame = self.get_parameter(
            'output_frame').get_parameter_value().string_value
        self.unexpected_frame_reported = False

        output_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.publisher = self.create_publisher(
            PointCloud2, output_topic, output_qos)
        self.subscription = self.create_subscription(
            PointCloud2,
            input_topic,
            self.pointcloud_callback,
            output_qos,
        )

        self.get_logger().info(
            f'Correcting PointCloud2 frame from {self.input_frame} '
            f'to {self.output_frame}: {input_topic} -> {output_topic}')

    def pointcloud_callback(self, message):
        """Correct only the known Fortress RGB-D frame mismatch."""
        if message.header.frame_id == self.input_frame:
            message.header.frame_id = self.output_frame
        elif message.header.frame_id != self.output_frame:
            if not self.unexpected_frame_reported:
                self.get_logger().warning(
                    'Ignoring PointCloud2 with unexpected frame_id '
                    f'"{message.header.frame_id}"')
                self.unexpected_frame_reported = True
            return

        self.publisher.publish(message)


def main(args=None):
    """Run the camera point-cloud frame correction node."""
    rclpy.init(args=args)
    node = CameraPointCloudFrameFix()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
