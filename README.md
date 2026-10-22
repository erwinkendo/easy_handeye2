
# easy_handeye2: automated, hardware-independent Hand-Eye Calibration for ROS2

<img src="docs/img/eye_on_base_ndi_pic.png" width="345"/> <img src="docs/img/05_calibrated_rviz.png" width="475"/> 


This package provides functionality and a GUI to: 
- **sample** the robot position and tracking system output via `tf`,
- **compute** the eye-on-base or eye-in-hand calibration matrix through the OpenCV library's hand-eye calibration algorithms (e.g. Tsai-Lenz),
- **store** the result of the calibration,
- **publish** the result of the calibration procedure as a `tf` transform at each subsequent system startup,
- **evaluate** the accuracy of the resulting calibration matrix,
- (optional) automatically **move** a robot around a starting pose via `MoveIt!` to acquire the samples. 

The intended result is to make it easy and straightforward to perform the calibration, and to keep it up-to-date throughout the system. 
Two launch files are provided to be run, respectively to perform the calibration and check its result. 
A further launch file can be integrated into your own launch files, to make use of the result of the calibration in a transparent way: 
if the calibration is performed again, the updated result will be used without further action required.    

You can try out this software in a simulator, through the 
[easy_handeye2_demo package](https://github.com/marcoesposito1988/easy_handeye2_demo). This package also serves as an 
example for integrating `easy_handeye2` into your own launch scripts.

This is a port of [easy_handeye](https://github.com/IFL-CAMP/easy_handeye) to ROS2.

## News
- version 0.5.0
    - port to ROS2
    - addition of rqt evaluator script
 

## Use Cases

If you are unfamiliar with Tsai's hand-eye calibration [1], it can be used in two ways:

- **eye-in-hand** to compute the static transform between the reference frames of
  a robot's hand effector and that of a tracking system, e.g. the optical frame
  of an RGB camera used to track AR markers. In this case, the camera is
  mounted on the end-effector, and you place the visual target so that it is
  fixed relative to the base of the robot; for example, you can place an AR marker on a table.
- **eye-on-base** to compute the static transform from a robot's base to a tracking system, e.g. the
  optical frame of a camera standing on a tripod next to the robot. In this case you can attach a marker,
  e.g. an AR marker, to the end-effector of the robot.
  
A relevant example of an eye-on-base calibration is finding the position of an RGBD camera with respect to a robot for object collision avoidance, e.g. [with MoveIt!](http://docs.ros.org/indigo/api/moveit_tutorials/html/doc/pr2_tutorials/planning/src/doc/perception_configuration.html): an [example launch file](docs/example_launch/ur5_kinect_calibration.launch) is provided to perform this common task between an Universal Robot and a Kinect through aruco. eye-on-hand can be used for [vision-guided tasks](https://youtu.be/nBTflbxYGkI?t=24s).

The (arguably) best part is, that you do not have to care about the placement of the auxiliary marker
(the one on the table in the eye-in-hand case, or on the robot in the eye-on-base case). The algorithm
will "erase" that transformation out, and only return the transformation you are interested in.


eye-on-base             |  eye-on-hand
:-------------------------:|:-------------------------:
![](docs/img/eye_on_base_aruco_pic.png)  |  ![](docs/img/eye_on_hand_aruco_pic.png)

## Getting started

- clone this repository into your catkin workspace:
```
cd ~/easy_handeye2_ws/src  # replace with path to your workspace
git clone https://github.com/marcoesposito1988/easy_handeye2
```

- satisfy dependencies
```
cd ..  # now we are inside ~/easy_handeye2_ws
rosdep install -iyr --from-paths src
```

- build
```
colcon build
```

## Usage

Two launch files, one for computing and one for publishing the calibration respectively,
are provided to be included in your own. The default arguments should be
overridden to specify the correct tf reference frames, and to avoid conflicts when using
multiple calibrations at once.

The suggested integration is:
- create a new `handeye_calibrate.launch.py` file, which includes the robot's and tracking system's launch files, as well as 
`easy_handeye`'s `calibrate.launch.py` as illustrated below in the next section "Calibration"
- in each of your launch files where you need the result of the calibration, include `easy_handeye`'s `publish.launch.py` 
as illustrated below in the section "Publishing" 

### Calibration

For both use cases, you can either launch the `calibrate.launch.py`
launch file, or you can include it in another launchfile as shown below. Either
way, the launch file will bring up a calibration script. By default, the script will interactively ask you
to accept or discard each sample. At the end, the parameters will be saved in a yaml file.

#### eye-in-hand

```xml
<launch>
  <!-- (start your robot's MoveIt! stack, e.g. include its moveit_planning_execution.launch.py) -->
  <!-- (start your tracking system's ROS driver) -->

  <include file="$(find easy_handeye2)/launch/calibrate.launch.py">
    <arg name="calibration_type" value="eye_in_hand"/>

    <!-- you can choose any identifier, as long as you use the same for publishing the calibration -->
    <arg name="name" value="my_eih_calib"/>

    <!-- fill in the following parameters according to your robot's published tf frames -->
    <arg name="robot_base_frame" value="/base_link"/>
    <arg name="robot_effector_frame" value="/ee_link"/>

    <!-- fill in the following parameters according to your tracking system's published tf frames -->
    <arg name="tracking_base_frame" value="/optical_origin"/>
    <arg name="tracking_marker_frame" value="/optical_target"/>
  </include>
</launch>
```

#### eye-on-base

```xml
<launch>
  <!-- (start your robot's MoveIt! stack, e.g. include its moveit_planning_execution.launch) -->
  <!-- (start your tracking system's ROS driver) -->

  <include file="$(find easy_handeye2)/launch/calibrate.launch.py">
    <arg name="calibration_type" value="eye_on_base"/>
    <arg name="name" value="my_eob_calib"/>

    <!-- fill in the following parameters according to your robot's published tf frames -->
    <arg name="robot_base_frame" value="/base_link"/>
    <arg name="robot_effector_frame" value="/ee_link"/>

    <!-- fill in the following parameters according to your tracking system's published tf frames -->
    <arg name="tracking_base_frame" value="/optical_origin"/>
    <arg name="tracking_marker_frame" value="/optical_target"/>
  </include>
</launch>
```


#### Example: UR (urx-simple-hl) + RealSense + ChArUco board

`calibrate_urx_realsense.launch.py` is a ready-made eye-in-hand calibration for a UR arm driven with a wrist-mounted RealSense. It starts the RealSense driver
(`rs_camera`), the board tracker, `handeye_server` and the rqt GUI, and calibrates `tool0` -> `rs_camera_link`.

It uses the ChArUco support of the **`charuco-board` branch of the
[ros_aruco_opencv fork](https://github.com/erwinkendo/ros_aruco_opencv/tree/charuco-board)**; upstream
`fictionlab/ros_aruco_opencv` and the released `ros-<distro>-aruco-opencv` package only detect single markers and grid boards. Build it from source in
the same workspace (it needs OpenCV < 4.7, e.g. the one of ROS 2 Jazzy):

```bash
cd ~/ros2_ws/src
git clone -b charuco-board git@github.com:erwinkendo/ros_aruco_opencv.git
cd .. && colcon build --packages-select aruco_opencv_msgs aruco_opencv easy_handeye2
```

Start the arm driver and a `robot_state_publisher` that provides `base` -> `tool0` first (the GUI does not appear until that transform
and the board in the camera view are both available), then:

```bash
# ChArUco 5x7, square 0.030 m, marker 0.015 m, DICT_5X5_100 (aruco_opencv/config/board_charuco_5x7.yaml)
ros2 launch easy_handeye2 calibrate_urx_realsense.launch.py

# another board: describe it in a yaml like the one above, then
ros2 launch easy_handeye2 calibrate_urx_realsense.launch.py board_descriptions_file:=<yaml> board_name:=<name> marker_dict:=<dict>

# a single ArUco marker instead of a board
ros2 launch easy_handeye2 calibrate_urx_realsense.launch.py target:=marker marker_size:=0.10 marker_dict:=4X4_50
```

The board frame follows OpenCV's convention (origin at the top-left outer corner of the print, X along `squares_x`, Y down the page, Z into
the board) and is published as `board_<name>`. Measure the printed square and marker sizes: they set the scale of the result.
The rqt GUI needs the `rqt_py_common` package (declared in `package.xml`); the launch file starts it with `--force-discover` so a stale
rqt plugin cache cannot make it exit without a window.

#### Moving the robot

**WARNING**: this will only be available for Iron, and is work-in-progress

A GUI for automatic robot movement is provided by the `rqt_easy_handeye` package. Please refer to [its documentation](rqt_easy_handeye/README.md).

This is optional, and can be disabled in both aforementioned cases with:
```xml
<launch>
  <include file="$(find easy_handeye2)/launch/calibrate.launch.py">
      <!-- other arguments, as described above... -->
      
      <arg name="freehand_robot_movement" value="true" />
  </include>
</launch>
```

It will then be the user's responsibility to make the robot publish its own pose into `tf`. Please check that the robot's pose is updated correctly in 
RViz before starting to acquire samples (the robot driver may not work while the teaching mode button is pressed, etc).

The same applies to the validity of the samples. For the calibration to be found reliably, the end effector must be rotated as much as possible 
(up to 90°) about each axis, in both directions. Translating the end effector is not necessary, but can't hurt either.

<img src="docs/img/02_plan_movements.png" width="345"/> <img src="docs/img/04_plan_show.png" width="495"/>

#### Tips for accuracy

The following tips are given in [1], paragraph 1.3.2.

- Maximize rotation between poses.
- Minimize the distance from the target to the camera of the tracking system.
- Minimize the translation between poses.
- Use redundant poses.
- Calibrate the camera intrinsics if necessary / applicable.
- Calibrate the robot if necessary / applicable.

### Publishing
The `publish.launch.py` starts a node that publishes the transformation found during calibration in `tf`.
The parameters are automatically loaded from the yaml file, according to the specified namespace.
For convenience, you can include this file within your own launch script. You can include this file multiple times to 
publish many calibrations simultaneously; the following example publishes one eye-on-base and one eye-in-hand calibration:
```xml
<launch>
  <!-- (start your robot's MoveIt! stack, e.g. include its moveit_planning_execution.launch) -->
  <!-- (start your tracking system's ROS driver) -->

  <include file="$(find easy_handeye2)/launch/publish.launch.py">
    <arg name="name" value="my_eob_calib"/> <!-- use the same name that you used during calibration! -->
  </include>
  <include file="$(find easy_handeye2)/launch/publish.launch.py">
    <arg name="name" value="my_eih_calib"/> <!-- use the same name that you used during calibration! -->
  </include>
</launch>
```
You can have any number of calibrations at once (provided you specify distinct namespaces). 
If you perform again any calibration, you do not need to do anything: the next time you start the system, 
the publisher will automatically fetch the latest information. You can also manually restart the publisher 
nodes (e.g. with `rqt_launch`), if you don't want to shut down the whole system.

### FAQ
#### Why is the calibration wrong?
Please check the [troubleshooting](docs/troubleshooting.md)

#### How can I ...
##### Calibrate an RGBD camera (e.g. Kinect, Xtion, ...) with a robot for automatic object collision avoidance with MoveIt! ?
This is a perfect example of an eye-on-base calibration. You can take a look at this [example launch file](docs/example_launch/ur5_kinect_calibration.launch) written for an UR5 and a Kinect via aruco_ros, or [example for LWR iiwa with Xtion/Kinect ](docs/example_launch/iiwa_kinect_xtion_calibration.launch).
##### Disable the automatic robotic movements GUI?
You can pass the argument `freehand_robot_movement:=true` to `calibrate.launch`.
##### Calibrate one robot against multiple tracking systems?
You can just override the `name` argument of `calibrate.launch.py` to be always different, such that they will never collide. Using the same `namespace` as argument to multiple inclusions of `publish.launch` will allow you to publish each calibration in `tf`.
##### Find the transformation between the bases of two robots?
You could perform the eye-on-base calibration against the same tracking system, and concatenate the results.
##### Find the transformation between two tracking systems?
You could perform the eye-on-base calibration against the same robot, and concatenate the results. This will work also if the tracking systems are completely different and do not use the same markers.

## References

[1] *Tsai, Roger Y., and Reimar K. Lenz. "A new technique for fully autonomous
and efficient 3D robotics hand/eye calibration." Robotics and Automation, IEEE
Transactions on 5.3 (1989): 345-358.*
