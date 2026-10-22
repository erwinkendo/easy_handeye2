"""Eye-in-hand calibration: UR arm (urx-simple-hl) + wrist-mounted RealSense.

Result: the static transform  robot_effector_frame (tool0) -> tracking_base_frame (rs_camera_link).

Start these first (this launch does not start them, and never moves the arm):
  1. The driver, the ONLY process that talks to the arm:
       ros2 launch urx_simple_hl urx_simple_hl_launch.py
  2. robot_state_publisher with your UR description, fed by the driver's joint_states,
     so that  base -> tool0  exists in TF (the driver itself publishes no TF).

Then:
  ros2 launch easy_handeye2 calibrate_urx_realsense.launch.py                    # ChArUco 5x7, DICT_5X5_100 (default)
  ros2 launch easy_handeye2 calibrate_urx_realsense.launch.py target:=marker marker_size:=0.10 marker_dict:=4X4_50

This also starts the RealSense driver and ros_aruco_opencv (aruco_tracker_autostart, branch charuco-board),
which reads /<camera_name>/color/image_raw and publishes <optical frame> -> board_<board_name> (target:=charuco)
or marker_<marker_id> (target:=marker). The board or marker must stay fixed relative to the robot base.

ChArUco board: described in aruco_opencv/config/board_charuco_5x7.yaml (squares 5x7, square 0.030 m, marker
0.015 m, DICT_5X5_100); pass board_descriptions_file:=<yaml> for another one, and board_name:= if its name
differs from "charuco". Measure the printed sizes: they set the scale of the result. Board frame (OpenCV):
origin at the top-left outer corner of the print, X along the squares_x side, Y down the page, Z into the board.

The RealSense driver publishes rs_camera_link -> *_optical_frame itself, so the marker frame is
reachable from rs_camera_link and the calibration comes out directly for rs_camera_link.
Move the arm by hand/pendant (free-hand), take a sample for each pose in the rqt GUI, then compute
and save. Publish the result later with:  ros2 launch easy_handeye2 publish.launch.py name:=<name>

No dummy tool0 -> camera transform is published here (calibrate.launch.py does that for the demo):
rs_camera_link must have a single parent, the one from the saved calibration.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    L = LaunchConfiguration
    args = [
        DeclareLaunchArgument('name', default_value='urx_realsense_eih',
                              description='Identifier of the calibration; use the same one for publish.launch.py'),
        DeclareLaunchArgument('robot_base_frame', default_value='base',
                              description='urx-simple-hl / ur_description RTDE base frame ("base", NOT "base_link")'),
        DeclareLaunchArgument('robot_effector_frame', default_value='tool0',
                              description='UR flange frame the camera is mounted on'),
        DeclareLaunchArgument('tracking_base_frame', default_value='rs_camera_link',
                              description='Camera frame to calibrate (RealSense base link)'),
        DeclareLaunchArgument('target', default_value='charuco', choices=['charuco', 'marker'],
                              description='What the camera looks at: a ChArUco board or a single ArUco marker'),
        DeclareLaunchArgument('board_descriptions_file',
                              default_value=PathJoinSubstitution([FindPackageShare('aruco_opencv'), 'config', 'board_charuco_5x7.yaml']),
                              description='target:=charuco: yaml describing the board (see aruco_opencv/config)'),
        DeclareLaunchArgument('board_name', default_value='charuco',
                              description='target:=charuco: name of the board in that yaml; its tf frame is board_<name>'),
        DeclareLaunchArgument('marker_size', default_value='0.015',
                              description='Side of one printed ArUco marker in metres, black border included. '
                                          'target:=marker: sets the scale of the result. target:=charuco: only scales the '
                                          'per-marker marker_<id> frames; the board size comes from the yaml'),
        DeclareLaunchArgument('marker_id', default_value='0',
                              description='target:=marker: ID of the marker used for calibration; its tf frame is marker_<id>'),
        DeclareLaunchArgument('marker_dict', default_value='5X5_100',
                              description='ArUco dictionary the target was printed with (must match, or nothing is detected)'),
        DeclareLaunchArgument('start_aruco', default_value='true', choices=['true', 'false'],
                              description='Start aruco_opencv here; false if a tracker already publishes the marker frame'),
        DeclareLaunchArgument('start_realsense', default_value='true', choices=['true', 'false'],
                              description='Start realsense2_camera here; false if it already runs'),
        DeclareLaunchArgument('camera_name', default_value='rs_camera',
                              description='realsense2_camera camera_name; its base frame is <camera_name>_link'),
    ]

    # forwarding=False: rs_launch.py warns about every launch argument it does not declare, so it must not
    # inherit ours (marker_size, ...). launch_configurations is evaluated before the clearing and re-set inside.
    realsense = GroupAction(
        [IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([FindPackageShare('realsense2_camera'), 'launch', 'rs_launch.py'])))],
        scoped=True, forwarding=False,
        launch_configurations={
            'camera_name': L('camera_name'),
            'camera_namespace': '',  # topics: /<camera_name>/color/image_raw
            'publish_tf': 'true',  # rs_camera_link -> optical frames, needed to reach the marker from rs_camera_link
        },
        condition=IfCondition(L('start_realsense')),
    )

    # aruco_opencv publishes <optical frame> -> board_<name> / marker_<id>; image topic is the RealSense color stream
    is_charuco = ["'", L('target'), "' == 'charuco'"]
    marker_frame = PythonExpression(["'board_", L('board_name'), "' if "] + is_charuco + [" else 'marker_", L('marker_id'), "'"])
    board_file = PythonExpression(["'", L('board_descriptions_file'), "' if "] + is_charuco + [" else ''"])
    aruco = Node(
        package='aruco_opencv', executable='aruco_tracker_autostart', name='aruco_tracker', output='screen',
        parameters=[PathJoinSubstitution([FindPackageShare('aruco_opencv'), 'config', 'aruco_tracker.yaml']), {
            'cam_base_topic': ['/', L('camera_name'), '/color/image_raw'],
            'marker_size': ParameterValue(L('marker_size'), value_type=float),
            'marker_dict': L('marker_dict'),
            'board_descriptions_path': board_file,  # '' (no boards) for target:=marker
            'output_frame': '',  # keep poses in the camera optical frame
            'publish_tf': True,
        }],
        condition=IfCondition(L('start_aruco')),
    )

    params = {
        'name': L('name'),
        'calibration_type': 'eye_in_hand',
        'tracking_base_frame': L('tracking_base_frame'),
        'tracking_marker_frame': marker_frame,
        'robot_base_frame': L('robot_base_frame'),
        'robot_effector_frame': L('robot_effector_frame'),
    }
    handeye_server = Node(package='easy_handeye2', executable='handeye_server', name='handeye_server',
                          parameters=[params], output='screen')
    # --force-discover: rqt caches its plugin list in ~/.config/ros.org/rqt_gui.ini; a stale cache (after a rebuild or a
    # newly installed dependency) makes it exit with 'found no plugin matching ...' and no window
    handeye_rqt_calibrator = Node(package='easy_handeye2', executable='rqt_calibrator.py',
                                  name='handeye_rqt_calibrator', arguments=['--force-discover'], parameters=[params])

    return LaunchDescription(args + [realsense, aruco, handeye_server, handeye_rqt_calibrator])
