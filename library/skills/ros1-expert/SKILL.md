---
name: ros1-expert
preamble-tier: 1
version: 1.0.0
description: |
  Use when working on ROS1 (Noetic) robotics projects: nodes, topics, services,
  actions, TF/TF2, debugging tools, rosbag workflows, sensor calibration
  (LiDAR + camera + IMU), common error fixes, and launch file patterns.
  Use when building ROS1 packages with colcon build, diagnosing TF errors,
  replaying rosbags, writing CMakeLists.txt with install() directives, or
  working on calibration pipelines (LiDAR-camera, camera-IMU, LiDAR-IMU).
  Keywords: ros1, noetic, roslaunch, rostopic, rosbag, tf, nodelet, catkin,
  colcon, sensor fusion, lidar camera calibration, imu calibration.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - WebSearch
---

# ROS1 Expert Reference

This skill is a dense reference document. Claude should draw on whichever
sections are relevant to the user's question without reading all sections aloud.

---

## 1. ROS1 Architecture and Core Concepts

### The ROS Graph

Every ROS1 system is a directed computation graph:

- **roscore** -- must be running first. Starts rosmaster (name/registration
  service), rosout (logging aggregator), and the parameter server. One roscore
  per ROS network. It is a single point of failure: if it dies, all nodes lose
  peer discovery (though existing pub/sub connections survive briefly).

- **Nodes** -- single OS processes. Each owns a focused piece of robot
  functionality (one camera driver, one IMU driver, one calibration solver).
  Named by path: `/sensors/imu`, `/calibration/solver`. Nodes register with
  rosmaster on startup.

- **ROS_MASTER_URI** -- env var all nodes use to find roscore.
  Default: `http://localhost:11311`. For multi-machine: set to the roscore
  machine's IP, and set `ROS_IP` (or `ROS_HOSTNAME`) on every machine.

### Communication Patterns

| Pattern | Mechanism | Use case |
|---------|-----------|----------|
| Async streaming | Topics (pub/sub) | Sensor data, odometry, images |
| Synchronous RPC | Services (req/reply) | Configuration, one-shot queries |
| Long-running tasks | Actions (goal/feedback/result) | Calibration runs, navigation |
| Global config | Parameter server | Node parameters, robot description |

### Topics

- **Publisher**: `ros::Publisher pub = nh.advertise<MsgType>("topic", queue_size);`
- **Subscriber**: `ros::Subscriber sub = nh.subscribe("topic", queue_size, callback);`
- Message types are auto-generated from `.msg` files.
- `queue_size` is a FIFO buffer. Too small = dropped messages under load.
  Too large = memory bloat and stale data. For sensor data: 1-10. For
  calibration triggers: 1.
- **Latching**: `nh.advertise<MsgType>("topic", 1, true)` -- the last published
  message is replayed to any new subscriber. Use for `/tf_static`, robot
  description, calibration results.

### Services

- Defined by `.srv` files: request fields `---` response fields.
- Synchronous and blocking in roscpp by default.
- Server: `ros::ServiceServer srv = nh.advertiseService("name", callback);`
- Client: `ros::ServiceClient c = nh.serviceClient<SrvType>("name"); c.call(req, res);`
- Add `c.waitForExistence()` before calling to avoid race on startup.
- **Persistent connections**: `nh.serviceClient<T>("name", true)` keeps TCP
  connection open -- faster for repeated calls but breaks silently if server restarts.

### Actions (actionlib)

Actions are for tasks that take time and need feedback or cancellation.

`.action` file structure:
```
# Goal
int32 num_samples
---
# Result
float64[] calibration_matrix
---
# Feedback
float64 progress_percent
string current_phase
```

Building the package generates 7 message files and 5 topics under
`/action_name/`: `goal`, `cancel`, `status`, `feedback`, `result`.

SimpleActionServer (C++):
```cpp
#include <actionlib/server/simple_action_server.h>
typedef actionlib::SimpleActionServer<my_pkg::CalibrateAction> Server;

void executeCB(const my_pkg::CalibrateGoalConstPtr& goal, Server* as) {
  my_pkg::CalibrateFeedback fb;
  my_pkg::CalibrateResult result;
  ros::Rate r(10);
  for (int i = 0; i < goal->num_samples; i++) {
    if (as->isPreemptRequested() || !ros::ok()) {
      as->setPreempted();
      return;
    }
    fb.progress_percent = (float)i / goal->num_samples * 100.0;
    as->publishFeedback(fb);
    r.sleep();
  }
  as->setSucceeded(result);
}
// IMPORTANT: NodeHandle must exist before constructing Server
ros::NodeHandle nh;
Server server(nh, "calibrate", boost::bind(&executeCB, _1, &server), false);
server.start();
```

States: PENDING -> ACTIVE -> SUCCEEDED/ABORTED/PREEMPTED.

### Parameter Server

- Hierarchical key/value store. Keys are namespaced: `/robot_name/sensor/param`.
- `rosparam set /key value` / `rosparam get /key` / `rosparam dump file.yaml`
- In C++: `nh.param<double>("freq", freq, 10.0);` (with default)
  or `nh.getParam("freq", freq);` (returns false if missing)
- In launch: `<param name="freq" value="10.0"/>`
- Private params (scoped to node): use `~param_name` or `ros::NodeHandle nh("~");`
- Load YAML: `<rosparam file="$(find pkg)/config/params.yaml"/>`
- **Gotcha**: parameters survive node death -- stale params from a crashed node
  persist. Use `rosparam delete /key` or `rosparam load` to reset.

---

## 2. TF / TF2

TF is ROS1's coordinate frame system. TF2 is the current implementation
(available in ROS1 via `tf2_ros`). The old `tf` API still works but TF2 is
preferred.

### Frame Tree

Every robot has a tree of coordinate frames. The root is usually `world` or
`map`. A sensor calibration system typically has:
```
world
  └── base_link
        ├── lidar_frame
        ├── camera_frame
        └── imu_frame
```

Transforms = position + quaternion rotation between parent/child frames.

### Publishing Transforms

**Dynamic** (changes over time):
```cpp
#include <tf2_ros/transform_broadcaster.h>
tf2_ros::TransformBroadcaster br;
geometry_msgs::TransformStamped ts;
ts.header.stamp = ros::Time::now();
ts.header.frame_id = "base_link";
ts.child_frame_id = "lidar_frame";
// fill ts.transform.translation and ts.transform.rotation
br.sendTransform(ts);
```

**Static** (never changes, e.g., sensor extrinsics):
```cpp
#include <tf2_ros/static_transform_broadcaster.h>
tf2_ros::StaticTransformBroadcaster static_br;
// Only need to publish once; latched on /tf_static
static_br.sendTransform(ts);
```

Or from launch file:
```xml
<node pkg="tf2_ros" type="static_transform_publisher" name="cam_tf"
      args="x y z qx qy qz qw parent_frame child_frame"/>
```
Argument order: translation (x y z) then quaternion (qx qy qz qw).
Note: the older `tf` version used roll-pitch-yaw instead of quaternion.

### Lookup Transforms

```cpp
#include <tf2_ros/transform_listener.h>
#include <tf2_ros/buffer.h>

tf2_ros::Buffer tfBuffer;
tf2_ros::TransformListener tfListener(tfBuffer);

// Wait for transform to become available (up to 1 second)
try {
  geometry_msgs::TransformStamped ts =
    tfBuffer.lookupTransform("target_frame", "source_frame",
                              ros::Time(0),          // latest available
                              ros::Duration(1.0));   // timeout
} catch (tf2::TransformException& ex) {
  ROS_WARN("%s", ex.what());
}
```

`ros::Time(0)` = "give me the latest transform." Using a specific timestamp
requires that transform to be in the buffer -- if it has aged out, you get an
extrapolation error.

### TF Debugging Tools

```bash
# Print transform between two frames continuously
rosrun tf tf_echo source_frame target_frame

# TF2 version
ros2 run tf2_ros tf2_echo source_frame target_frame   # (ROS2 syntax for ref)
rosrun tf2_ros tf2_echo source_frame target_frame     # ROS1

# Generate a PDF of the full TF tree
rosrun tf view_frames    # creates frames.pdf in current dir
rosrun tf2_tools view_frames.py

# Monitor TF update rates and delays
rosrun tf tf_monitor

# Check TF connectivity
rosrun tf2_ros tf2_monitor
```

### Common TF Errors

**"Lookup would require extrapolation into the past"**
- Cause: requesting a transform at time T but the oldest available data is newer.
  Usually means use_sim_time mismatch: some nodes on wall clock, others on
  simulated clock from `rosbag play --clock`.
- Fix: ensure all nodes have `use_sim_time:=true` when replaying bags, or use
  `ros::Time(0)` to request latest.

**"Could not find a connection between 'frame_a' and 'frame_b'"**
- Cause: disconnected TF tree. A node that publishes the connecting transform
  has not started, has died, or has a typo in frame IDs.
- Fix: `rosrun tf view_frames` to visualize the tree. Check for typos (case
  sensitive: `Camera` != `camera`).

**"Lookup would require extrapolation into the future"**
- Cause: a node is publishing transforms with timestamps slightly ahead of
  ros::Time::now(), often due to header.stamp = ros::Time::now() + small offset.
- Fix: lower the timestamp or add a small tolerance in the listener.

**"Frame X does not exist"**
- Cause: the publisher for that frame hasn't published yet, or has wrong name.
- Fix: `rostopic echo /tf | grep frame_id` to see what frames are actually published.

---

## 3. Build System (catkin packages + colcon)

### Workspace Layout

```
workspace/
  src/          <- source space: your packages live here
    my_package/
      CMakeLists.txt
      package.xml
      src/
      include/
      launch/
      config/
      msg/
      srv/
      action/
  build/        <- CMake cache per package (never edit directly)
  install/      <- merged install space; source this after building
  log/          <- colcon build/test logs (latest_build, latest_test symlinks)
```

> **This workspace uses `colcon build`.** Even though packages use catkin CMake
> macros (`catkin_package`, `find_package(catkin ...)`), the outer build driver
> is colcon, not catkin_make or catkin_tools. colcon drives each package's
> cmake/make independently (isolated build space per package).

### colcon build — Command Reference

```bash
cd $HOME/workspace/fast_calib_ros1/workspace

# Full workspace build
colcon build

# Release build (always prefer for calibration/SLAM code)
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release

# Build a single package (+ its dependencies)
colcon build --packages-select fast_calib
colcon build --packages-select fast_calib fast_livo2

# Build only packages that changed (incremental)
colcon build --packages-up-to fast_calib

# Skip a package
colcon build --packages-skip gpm_rl_calib

# Limit parallel jobs (useful on low-RAM machines)
colcon build --parallel-workers 4

# Extra verbose — see cmake output live
colcon build --event-handlers console_direct+

# Clean a single package's build artifacts
rm -rf build/fast_calib install/fast_calib

# Full clean
rm -rf build/ install/ log/
```

### Makefile Notes (colcon + catkin packages)

When colcon builds a catkin ROS1 package it:
1. Runs `cmake` in an isolated `build/<pkg>/` directory — generates a
   standard `Makefile` there (not a top-level workspace Makefile).
2. Runs `make` (or `ninja` if configured) inside that directory.
3. Runs `make install` into the shared `install/` prefix.

Key differences vs catkin_make:
- **No top-level `Makefile`** in the workspace root. You cannot run `make`
  from the workspace root — always use `colcon build`.
- **No `devel/` space.** Everything goes into `install/`. Never source
  `devel/setup.bash` — it won't exist.
- **Each package is independent.** Changing one package only requires
  rebuilding that package: `colcon build --packages-select <pkg>`.
- **`COLCON_IGNORE`** — place an empty `COLCON_IGNORE` file in any directory
  to prevent colcon from discovering packages inside it:
  ```bash
  touch src/some_broken_pkg/COLCON_IGNORE
  ```
- **CMake cache per package** lives at `build/<pkg>/CMakeCache.txt`. If you
  change `find_package` paths or cmake flags, delete that file first.

### Sourcing

```bash
# After every colcon build, source the install space
source install/setup.bash    # bash
source install/setup.zsh     # zsh

# Add to ~/.bashrc for permanent effect:
echo "source $HOME/workspace/fast_calib_ros1/workspace/install/setup.bash" >> ~/.bashrc
```

Overlaying workspaces: source ROS base first, then your workspace.
Each `setup.bash` extends `CMAKE_PREFIX_PATH` and `AMENT_PREFIX_PATH` (even
for ROS1 when using colcon).

### CMakeLists.txt Template

```cmake
cmake_minimum_required(VERSION 3.0.2)
project(my_package)

# 1. Find catkin and any catkin packages you depend on
find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  std_msgs
  sensor_msgs
  geometry_msgs
  tf2
  tf2_ros
  cv_bridge
  pcl_ros
  message_generation   # needed if you define msgs/srvs/actions
)

# 2. Find non-catkin system deps
find_package(OpenCV REQUIRED)
find_package(PCL REQUIRED)
find_package(Eigen3 REQUIRED)

# 3. Declare message/service/action files (if any)
add_message_files(FILES MyMsg.msg)
add_service_files(FILES MyService.srv)
add_action_files(FILES MyAction.action)
generate_messages(DEPENDENCIES std_msgs sensor_msgs actionlib_msgs)

# 4. Declare catkin package
catkin_package(
  INCLUDE_DIRS include
  LIBRARIES my_lib
  CATKIN_DEPENDS roscpp sensor_msgs tf2_ros message_runtime
  DEPENDS OpenCV PCL Eigen3
)

# 5. Include dirs
include_directories(
  include
  ${catkin_INCLUDE_DIRS}
  ${OpenCV_INCLUDE_DIRS}
  ${PCL_INCLUDE_DIRS}
  ${EIGEN3_INCLUDE_DIRS}
)

# 6. Build targets
add_executable(my_node src/my_node.cpp)
target_link_libraries(my_node ${catkin_LIBRARIES} ${OpenCV_LIBS} ${PCL_LIBRARIES})
add_dependencies(my_node ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})

add_library(my_lib src/my_lib.cpp)
target_link_libraries(my_lib ${catkin_LIBRARIES})

# -----------------------------------------------------------------------
# 7. INSTALL — REQUIRED when using colcon build
#
# With catkin_make you could rely on devel/ space and skip install().
# With colcon there is NO devel/ space — colcon runs `make install` to
# populate install/. If you omit install() your targets/files will not
# be found after `source install/setup.bash`.
# -----------------------------------------------------------------------

# 7a. C++ executables and libraries
install(TARGETS my_node my_lib
  ARCHIVE DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}   # static libs (.a)
  LIBRARY DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}   # shared libs (.so)
  RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}   # executables
)

# 7b. Python ROS nodes (use catkin_install_python, NOT install(PROGRAMS))
#     catkin_install_python wraps the script in a shim that sources the
#     workspace and calls the real script — required for rosrun/roslaunch.
catkin_install_python(PROGRAMS
  scripts/my_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# 7c. Launch files
install(DIRECTORY launch/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
  FILES_MATCHING PATTERN "*.launch"
)

# 7d. Config / YAML / rviz files — pattern from this workspace:
foreach(dir launch config rviz_cfg)
  install(DIRECTORY ${dir}/
    DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/${dir}
  )
endforeach()

# 7e. Non-ROS Python modules (helper scripts, not rosrun targets)
#     Use plain install(DIRECTORY) with FILES_MATCHING so colcon copies them.
install(DIRECTORY scripts/my_module/
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}/my_module
  FILES_MATCHING PATTERN "*.py"
)

# 7f. Header files (if this package exports headers to other packages)
install(DIRECTORY include/${PROJECT_NAME}/
  DESTINATION ${CATKIN_PACKAGE_INCLUDE_DESTINATION}
)

# 7g. Nodelet plugin XML (if this package provides nodelets)
install(FILES nodelet_plugins.xml
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
```

Key rules:
- `catkin_package()` MUST come before `add_library()`/`add_executable()`.
- `generate_messages()` MUST be called if using `message_generation`.
- `add_dependencies()` ensures message headers are generated before compilation.
- **`install()` is mandatory with colcon** — without it, built targets stay in
  `build/<pkg>/` and are never copied to `install/`, so `rosrun`/`roslaunch`
  will not find them.
- Use `catkin_install_python()` for ROS node scripts (not bare `install(PROGRAMS)`).
- The catkin destination variables resolve to paths under `install/`:
  - `CATKIN_PACKAGE_BIN_DESTINATION` → `lib/<pkg>/`
  - `CATKIN_PACKAGE_LIB_DESTINATION` → `lib/`
  - `CATKIN_PACKAGE_SHARE_DESTINATION` → `share/<pkg>/`
  - `CATKIN_PACKAGE_INCLUDE_DESTINATION` → `include/<pkg>/`
- For nodelets: install the plugin XML and register it (see Nodelets section).

### package.xml (format 2)

```xml
<?xml version="1.0"?>
<package format="2">
  <name>my_package</name>
  <version>0.1.0</version>
  <description>Brief description</description>
  <maintainer email="you@example.com">Your Name</maintainer>
  <license>MIT</license>

  <buildtool_depend>catkin</buildtool_depend>

  <!-- Build + run time deps -->
  <depend>roscpp</depend>
  <depend>sensor_msgs</depend>
  <depend>tf2_ros</depend>
  <depend>cv_bridge</depend>
  <depend>pcl_ros</depend>

  <!-- Only needed at build time -->
  <build_depend>message_generation</build_depend>
  <!-- Only needed at run time -->
  <exec_depend>message_runtime</exec_depend>
</package>
```

---

## 4. Launch Files

Launch files start multiple nodes and set parameters in one command:
`roslaunch package_name file.launch [arg:=value ...]`

### Full Syntax Reference

```xml
<launch>
  <!-- ========== Arguments ========== -->
  <!-- Declare an arg with default; override on CLI: topic:=/my/topic -->
  <arg name="topic" default="/sensor/lidar"/>
  <!-- Required arg (no default): must be passed on CLI -->
  <arg name="bag_file"/>
  <!-- Boolean arg for conditionals -->
  <arg name="use_rviz" default="false"/>

  <!-- ========== Parameters ========== -->
  <!-- Scalar param on parameter server -->
  <param name="robot_description" command="$(find xacro)/xacro $(find robot)/urdf/robot.urdf.xacro"/>
  <!-- Load entire YAML file -->
  <rosparam file="$(find my_pkg)/config/params.yaml" command="load"/>
  <!-- Delete a param -->
  <rosparam command="delete" param="/old_param"/>

  <!-- ========== Nodes ========== -->
  <node pkg="my_pkg" type="my_node" name="solver_node" output="screen"
        required="false" respawn="true" respawn_delay="2.0"
        launch-prefix="xterm -e gdb --args">
    <!-- Private params (scoped to this node) -->
    <param name="freq" value="10.0"/>
    <param name="frame_id" value="base_link"/>
    <!-- Remap topic/service names for this node only -->
    <remap from="input" to="$(arg topic)"/>
    <remap from="/clock" to="/bag_clock"/>
  </node>

  <!-- ========== Conditionals ========== -->
  <group if="$(arg use_rviz)">
    <node pkg="rviz" type="rviz" name="rviz"
          args="-d $(find my_pkg)/rviz/config.rviz"/>
  </group>
  <node pkg="some_pkg" type="node" name="n" unless="$(arg use_rviz)"/>

  <!-- ========== Namespaces ========== -->
  <group ns="sensor_suite">
    <!-- All nodes here get namespace /sensor_suite/ -->
    <node pkg="camera_driver" type="driver" name="camera"/>
    <node pkg="lidar_driver"  type="driver" name="lidar"/>
  </group>

  <!-- ========== Including other launch files ========== -->
  <include file="$(find other_pkg)/launch/sensors.launch">
    <arg name="freq" value="20.0"/>
  </include>

  <!-- ========== Environment variables ========== -->
  <env name="ROSCONSOLE_CONFIG_FILE" value="$(find my_pkg)/config/rosconsole.conf"/>

  <!-- ========== Static TF ========== -->
  <node pkg="tf2_ros" type="static_transform_publisher" name="lidar_to_cam"
        args="0.1 0.0 0.05 0.0 0.0 0.0 1.0 lidar_frame camera_frame"/>
  <!--     tx  ty   tz   qx  qy  qz  qw  parent       child -->
</launch>
```

### Substitution Expressions

| Expression | Meaning |
|-----------|---------|
| `$(find pkg)` | Absolute path to ROS package |
| `$(arg name)` | Value of an `<arg>` |
| `$(env VAR)` | Shell environment variable |
| `$(optenv VAR default)` | Env var with fallback |
| `$(eval expr)` | Python expression, e.g. `$(eval arg('x') * 2)` |
| `$(dirname)` | Directory containing this launch file |

### node Attributes

| Attribute | Meaning |
|-----------|---------|
| `output="screen"` | Print stdout/stderr to terminal |
| `output="log"` | Write to `~/.ros/log/` (default) |
| `required="true"` | Kill all nodes if this one dies |
| `respawn="true"` | Restart if this node dies |
| `launch-prefix="valgrind"` | Prefix the exec command |
| `clear_params="true"` | Delete node's private params before start |

---

## 5. Debugging Tools

### CLI Tools

```bash
# ===== rosnode =====
rosnode list                         # list all active nodes
rosnode info /node_name              # pubs, subs, services, URI, PID
rosnode ping /node_name              # check connectivity/latency
rosnode kill /node_name              # kill a node

# ===== rostopic =====
rostopic list                        # all active topics
rostopic list -v                     # with pub/sub counts and types
rostopic echo /topic                 # print messages
rostopic echo /topic --noarr         # suppress arrays
rostopic echo /topic -n 1            # print one message and exit
rostopic hz /topic                   # measure publish rate
rostopic bw /topic                   # measure bandwidth
rostopic type /topic                 # show message type
rostopic info /topic                 # publishers, subscribers, type
rostopic pub /topic std_msgs/String "data: 'hello'" -r 1   # publish at 1 Hz
rostopic pub /topic std_msgs/String "data: 'hello'" --once # once and quit

# ===== rosservice =====
rosservice list
rosservice type /service_name
rosservice info /service_name
rosservice call /service_name "{arg1: val, arg2: val}"
rosservice find sensor_msgs/SetCameraInfo   # find services by type

# ===== rosparam =====
rosparam list
rosparam get /param
rosparam set /param value
rosparam dump params.yaml
rosparam load params.yaml /optional_ns

# ===== roswtf =====
roswtf                               # system-wide diagnostics
roswtf my_launch.launch             # check a specific launch file
# Common findings: hostname resolves to 127.0.1.1 (add to /etc/hosts),
# orphan nodes, topic mismatches, disconnected graph components

# ===== rosrun/roslaunch =====
rosrun package_name executable_name
rosrun package_name executable_name _param:=value topic:=/remapped
roslaunch package_name file.launch arg:=value
roslaunch --screen package_name file.launch   # force all output to terminal
roslaunch --log package_name file.launch      # log everything
```

### rqt Tools

```bash
rqt_graph           # visualize node/topic graph (running nodes + connections)
rqt_console         # view/filter log messages (levels: DEBUG INFO WARN ERROR FATAL)
rqt_plot            # plot numeric topic values live
rqt_image_view      # display camera images
rqt_bag             # GUI for rosbag inspection
rqt_tf_tree         # visualize TF tree
rqt                 # launch rqt framework and load any plugin
```

For `rqt_graph`: uncheck "Leaf topics only" and "Dead sinks" to see the full
graph. Nodes shown as ovals, topics as rectangles.

### rviz

Key displays for calibration debugging:
- **PointCloud2**: visualize lidar scans, check frame_id
- **Image**: camera feed, check header timestamps
- **TF**: show all frames as axes in 3D (crowded but complete)
- **Camera**: project image onto 3D scene (needs CameraInfo)
- **Marker / MarkerArray**: custom overlays from calibration nodes

Fixed Frame matters: set it to the frame your sensors are relative to
(`base_link`, `lidar_frame`, etc.). Mismatched fixed frame = everything at origin.

---

## 6. rosbag Workflows

### Recording

```bash
# Record all topics
rosbag record -a -O all_sensors.bag

# Record specific topics (critical for large sensor datasets)
rosbag record -O calib_data.bag \
  /camera/image_raw \
  /camera/camera_info \
  /velodyne_points \
  /imu/data \
  /tf \
  /tf_static

# Record with compression (reduces size ~50-70% for point clouds)
rosbag record -O calib.bag --lz4 /velodyne_points /camera/image_raw

# Record with max file size splitting
rosbag record -O session.bag --split --size 1024 -a   # 1 GB splits

# Record with max duration splitting
rosbag record -O session.bag --split --duration 60 -a  # 60-second files
```

### Inspection

```bash
rosbag info calib.bag
# Shows: duration, start/end time, message counts, topic list, compression ratio

rosbag check calib.bag      # verify bag integrity
```

### Playback

```bash
rosbag play calib.bag

# CRITICAL for nodes using ros::Time::now(): publish /clock
rosbag play calib.bag --clock

# Slow down or speed up
rosbag play calib.bag --clock -r 0.5    # half speed
rosbag play calib.bag --clock -r 2.0    # double speed

# Start at offset, play only N seconds
rosbag play calib.bag -s 10 -u 30       # skip first 10s, play 30s

# Loop continuously
rosbag play calib.bag -l

# Play specific topics only
rosbag play calib.bag --topics /camera/image_raw /imu/data

# Pause at start (press SPACE to unpause)
rosbag play calib.bag --pause

# Remap topics during playback
rosbag play calib.bag /old_topic:=/new_topic
```

**use_sim_time**: when replaying bags with `--clock`, every node MUST have
`/use_sim_time=true` set on the parameter server, or their `ros::Time::now()`
will not be synchronized to the bag's clock. Set globally:
```bash
rosparam set /use_sim_time true
rosbag play calib.bag --clock
```
Or in launch:
```xml
<param name="/use_sim_time" value="true"/>
```

### Filtering and Editing

```bash
# Filter by topics (creates new bag)
rosbag filter input.bag output.bag \
  "topic in ['/camera/image_raw', '/imu/data', '/tf', '/tf_static']"

# Filter by time range
rosbag filter input.bag output.bag "t.secs >= 1700000100 and t.secs <= 1700000200"

# Filter by topic AND time
rosbag filter input.bag output.bag \
  "topic == '/velodyne_points' and t.secs >= 1700000100"

# Compress existing bag
rosbag compress --lz4 input.bag     # creates input.orig.bag backup

# Decompress
rosbag decompress input.bag

# Merge multiple bags (pipe-based approach)
# Use rosbag_merge or play into a new record session

# Fix bag (repair corrupted index)
rosbag reindex bad.bag
```

### Bag Analysis in Python

```python
import rosbag
import numpy as np

with rosbag.Bag('calib.bag') as bag:
    # List topics
    info = bag.get_type_and_topic_info()
    for topic, tinfo in info.topics.items():
        print(f"{topic}: {tinfo.msg_type}, {tinfo.message_count} msgs")

    # Iterate messages
    for topic, msg, t in bag.read_messages(topics=['/imu/data']):
        # t is rospy.Time
        print(t.to_sec(), msg.linear_acceleration.x)

    # Get time range
    print("Start:", bag.get_start_time())
    print("End:",   bag.get_end_time())
```

---

## 7. Message Synchronization (message_filters)

Critical for sensor fusion and calibration -- aligning camera images with lidar
scans or IMU data.

### ExactTime (same timestamp required)

```cpp
#include <message_filters/subscriber.h>
#include <message_filters/synchronizer.h>
#include <message_filters/sync_policies/exact_time.h>
#include <sensor_msgs/Image.h>
#include <sensor_msgs/PointCloud2.h>

typedef message_filters::sync_policies::ExactTime<
    sensor_msgs::Image, sensor_msgs::PointCloud2> ExactPolicy;

message_filters::Subscriber<sensor_msgs::Image>      img_sub(nh, "image", 10);
message_filters::Subscriber<sensor_msgs::PointCloud2> pc_sub(nh, "points", 10);
message_filters::Synchronizer<ExactPolicy> sync(ExactPolicy(10), img_sub, pc_sub);
sync.registerCallback(boost::bind(&callback, _1, _2));
```

### ApproximateTime (most useful for real sensors)

```cpp
#include <message_filters/sync_policies/approximate_time.h>

typedef message_filters::sync_policies::ApproximateTime<
    sensor_msgs::Image, sensor_msgs::PointCloud2> ApproxPolicy;

message_filters::Synchronizer<ApproxPolicy> sync(ApproxPolicy(10), img_sub, pc_sub);
// queue_size=10; increase if you're dropping pairs under heavy load
sync.registerCallback(boost::bind(&callback, _1, _2));
```

Python version:
```python
from message_filters import ApproximateTimeSynchronizer, Subscriber
import rospy
from sensor_msgs.msg import Image, PointCloud2

img_sub = Subscriber('/camera/image_raw', Image)
pc_sub  = Subscriber('/velodyne_points', PointCloud2)
ats = ApproximateTimeSynchronizer([img_sub, pc_sub], queue_size=10, slop=0.1)
# slop=0.1 means timestamps within 100ms are considered synchronized
ats.registerCallback(callback)
rospy.spin()
```

**Gotcha**: if one topic publishes much faster than the other, increase queue_size.
The synchronizer drops older messages once the queue fills. If callbacks stop
firing, check that both topics are publishing and that `slop` is large enough.

---

## 8. Nodelets

Nodelets are plugins loaded into a shared process (nodelet manager). Messages
between nodelets in the same manager are passed as `boost::shared_ptr` -- zero
copy, no serialization. Critical for high-bandwidth pipelines (cameras at 30 Hz,
lidar at 20 Hz).

### Writing a Nodelet

```cpp
#include <nodelet/nodelet.h>
#include <pluginlib/class_list_macros.h>
#include <ros/ros.h>
#include <sensor_msgs/PointCloud2.h>

namespace my_pkg {
class PointCloudFilter : public nodelet::Nodelet {
public:
  virtual void onInit() {
    ros::NodeHandle& nh = getNodeHandle();
    ros::NodeHandle& pnh = getPrivateNodeHandle();
    pnh.param<double>("voxel_size", voxel_size_, 0.1);
    sub_ = nh.subscribe<sensor_msgs::PointCloud2>(
        "input", 10, &PointCloudFilter::callback, this);
    pub_ = nh.advertise<sensor_msgs::PointCloud2>("output", 10);
  }
private:
  void callback(const sensor_msgs::PointCloud2::ConstPtr& msg) {
    // Zero-copy: msg is shared_ptr, no copy made if published to nodelet peer
    pub_.publish(msg);
  }
  ros::Subscriber sub_;
  ros::Publisher  pub_;
  double voxel_size_;
};
} // namespace my_pkg

PLUGINLIB_EXPORT_CLASS(my_pkg::PointCloudFilter, nodelet::Nodelet)
```

Register in `nodelet_plugins.xml`:
```xml
<library path="lib/libmy_pkg">
  <class name="my_pkg/PointCloudFilter" type="my_pkg::PointCloudFilter"
         base_class_type="nodelet::Nodelet">
    <description>Filters point clouds</description>
  </class>
</library>
```

Register in `package.xml`:
```xml
<export>
  <nodelet plugin="${prefix}/nodelet_plugins.xml"/>
</export>
```

Launch with a nodelet manager:
```xml
<node pkg="nodelet" type="nodelet" name="manager" args="manager" output="screen"/>
<node pkg="nodelet" type="nodelet" name="filter"
      args="load my_pkg/PointCloudFilter manager" output="screen">
  <param name="voxel_size" value="0.05"/>
  <remap from="input"  to="/velodyne_points"/>
  <remap from="output" to="/velodyne_filtered"/>
</node>
```

**Performance notes**:
- Zero-copy only works within ONE nodelet manager (one process).
- Two managers = two processes = serialized transport (no shared ptr).
- All nodelets share a thread pool. One slow callback blocks others unless you
  use `CallbackQueue` with multiple threads.
- For CPU-bound nodelets, sometimes separate processes (regular nodes) are faster
  than a shared manager with thread contention.

---

## 9. C++ Node Patterns (roscpp)

### Basic Node Structure

```cpp
#include <ros/ros.h>
#include <sensor_msgs/Imu.h>
#include <sensor_msgs/PointCloud2.h>

class CalibNode {
public:
  CalibNode(ros::NodeHandle& nh, ros::NodeHandle& pnh) {
    // Load parameters
    pnh.param<std::string>("output_frame", output_frame_, "base_link");
    pnh.param<double>("sample_freq", freq_, 10.0);
    double timeout;
    if (!pnh.getParam("timeout", timeout)) {
      ROS_WARN("timeout not set, using default 5.0");
      timeout = 5.0;
    }

    // Advertise before subscribing (avoid missing first messages)
    pub_ = nh.advertise<sensor_msgs::PointCloud2>("output", 10);

    // Wait for service before calling
    ros::service::waitForService("/set_camera_info", 5.0);

    // Subscribe
    imu_sub_ = nh.subscribe("imu", 100, &CalibNode::imuCallback, this);
    pc_sub_  = nh.subscribe("points", 10, &CalibNode::pcCallback, this);

    // Timer (prefer over while loop + sleep)
    timer_ = nh.createTimer(ros::Duration(1.0 / freq_), &CalibNode::timerCB, this);
  }

private:
  void imuCallback(const sensor_msgs::Imu::ConstPtr& msg) {
    // msg is const shared_ptr -- don't modify; copy if you need to change it
  }
  void pcCallback(const sensor_msgs::PointCloud2::ConstPtr& msg) {}
  void timerCB(const ros::TimerEvent& e) {}

  ros::Publisher  pub_;
  ros::Subscriber imu_sub_, pc_sub_;
  ros::Timer      timer_;
  std::string     output_frame_;
  double          freq_;
};

int main(int argc, char** argv) {
  ros::init(argc, argv, "calib_node");
  ros::NodeHandle nh, pnh("~");
  CalibNode node(nh, pnh);
  // Single-threaded: callbacks run one at a time
  ros::spin();
  // Multi-threaded: N threads for callbacks
  // ros::AsyncSpinner spinner(4); spinner.start(); ros::waitForShutdown();
  return 0;
}
```

### Spinner Types

| Spinner | Behavior | Use when |
|---------|----------|----------|
| `ros::spin()` | Single thread, blocks | Simple nodes, order matters |
| `ros::spinOnce()` | Process pending callbacks once | Manual loop control |
| `ros::AsyncSpinner(N)` | N threads, concurrent callbacks | High-throughput, independent callbacks |
| `ros::MultiThreadedSpinner(N)` | Like AsyncSpinner but blocking | Same as above but blocks main thread |

**Warning**: `AsyncSpinner` with shared state requires mutexes. Callbacks for the
same subscriber run on different threads and can interleave.

### NodeHandle Namespaces

```cpp
ros::NodeHandle nh;          // global: /topic
ros::NodeHandle pnh("~");   // private: /node_name/topic
ros::NodeHandle nnh("ns");  // namespaced: /ns/topic

// Mix namespaces
auto pub = nh.advertise<Msg>("out", 1);    // publishes to /out
auto sub = pnh.subscribe("in", 1, &CB);   // subscribes to /my_node/in
```

---

## 10. Python Node Patterns (rospy)

```python
#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Imu, PointCloud2
from std_srvs.srv import Trigger, TriggerResponse
import threading

class CalibNode:
    def __init__(self):
        # init_node MUST come before any ros calls
        rospy.init_node('calib_node', anonymous=False)

        # Private params (prefix ~)
        self.freq = rospy.get_param('~freq', 10.0)
        self.frame_id = rospy.get_param('~frame_id', 'base_link')

        # Publisher
        self.pub = rospy.Publisher('output', PointCloud2, queue_size=10)

        # Subscriber
        self.imu_sub = rospy.Subscriber('imu', Imu, self.imu_cb, queue_size=100)

        # Service server
        self.srv = rospy.Service('trigger_calibration', Trigger, self.trigger_cb)

        # Service client
        rospy.wait_for_service('/set_camera_info')
        self.set_cam_info = rospy.ServiceProxy('/set_camera_info',
                                               sensor_msgs.srv.SetCameraInfo)

        # Timer
        self.timer = rospy.Timer(rospy.Duration(1.0 / self.freq), self.timer_cb)

        self.lock = threading.Lock()

    def imu_cb(self, msg):
        with self.lock:
            pass  # protect shared state

    def trigger_cb(self, req):
        return TriggerResponse(success=True, message="Calibration started")

    def timer_cb(self, event):
        # event.current_real, event.last_real, event.current_expected
        pass

if __name__ == '__main__':
    node = CalibNode()
    rospy.spin()
```

**rospy gotchas**:
- `rospy.init_node()` must be called once per process, before any pub/sub.
- `anonymous=True` appends a random suffix to the node name (useful for
  multiple instances of the same script).
- `rospy.spin()` blocks until node is shut down. For a loop:
  ```python
  rate = rospy.Rate(10)  # 10 Hz
  while not rospy.is_shutdown():
      do_work()
      rate.sleep()  # sleeps the RIGHT amount to maintain 10 Hz
  ```
- Mixing Anaconda Python with ROS Python = broken `import rospy`. ROS installs
  to the system Python. Fix: `export PYTHONPATH=/opt/ros/noetic/lib/python3/dist-packages:$PYTHONPATH`

---

## 11. Sensor Calibration Workflows

### Intrinsic Camera Calibration (camera_calibration)

```bash
# Record checkerboard images (move board slowly, cover full frame)
rosrun camera_calibration cameracalibrator.py \
  --size 8x6 \          # inner corners (squares - 1)
  --square 0.025 \      # square size in meters
  --camera_name camera \
  image:=/camera/image_raw \
  camera:=/camera

# Outputs: ost.yaml with D (distortion), K (intrinsic), R, P matrices
# Supported patterns: chessboard, circles, acircles (asymmetric circles)
```

Required calibration motions: tilt left/right, tilt up/down, move toward/away,
rotate around optical axis, cover all 4 corners + center with the pattern.
"CALIBRATE" button activates when sufficient data is collected.

### IMU Intrinsic Calibration (Allan Variance)

Determines noise density and bias instability parameters needed by Kalibr and
most VIO/LIO systems.

```bash
# 1. Record stationary IMU for 3+ hours (15-24 hours is better)
rosbag record -O imu_static.bag /imu/data

# 2. Compute Allan deviation (allan_variance_ros)
rosrun allan_variance_ros allan_variance /path/to/imu_static.bag /imu/data
# Outputs: imu.yaml

# 3. Alternative: imu_utils
roslaunch imu_utils imu_calib.launch imu_topic:=/imu/data imu_name:=my_imu \
  data_save_path:=/tmp/ max_time_min:=120
```

Output `imu.yaml` format (required by Kalibr):
```yaml
#Accelerometers
accelerometer_noise_density: 1.86e-03   #[ m/s^2/sqrt(Hz) ] (sigma)
accelerometer_random_walk:   4.33e-04   #[ m/s^3/sqrt(Hz) ] (sigma)
#Gyroscopes
gyroscope_noise_density:     1.87e-04   #[ rad/s/sqrt(Hz) ]
gyroscope_random_walk:       2.66e-05   #[ rad/s^2/sqrt(Hz) ]
update_rate:                 200.0      #[ Hz ]
```

Units: IMU linear acceleration in m/s^2, angular velocity in rad/s.
Covariance diagonal in sensor_msgs/Imu: set from datasheet if not computing online.

### Camera-IMU Calibration (Kalibr)

Estimates the rigid body transform T_cam_imu (spatial) and time offset (temporal).

```bash
# 1. Record calibration bag
# Camera: 20 Hz, IMU: 200 Hz (ratio >=10 recommended)
# Move the sensor rig (not the target) in front of an AprilGrid
# Excite all 6 DOF: roll, pitch, yaw, x, y, z translation
rosbag record -O cam_imu_calib.bag /camera/image_raw /imu/data

# 2. Prepare target YAML (AprilGrid recommended over checkerboard)
# target.yaml:
# target_type: 'aprilgrid'
# tagCols: 6
# tagRows: 6
# tagSize: 0.088  # meters, size of each tag
# tagSpacing: 0.3 # ratio: gap / tagSize

# 3. Run calibration
kalibr_calibrate_imu_camera \
  --bag cam_imu_calib.bag \
  --cam camchain.yaml \        # output from camera intrinsic calib
  --imu imu.yaml \             # output from Allan variance
  --target target.yaml

# 4. Output: camchain-imucam-[bag].yaml
# Contains: T_cam_imu (4x4), timeshift_cam_imu (seconds)
```

Common Kalibr failures:
- IMU data has bursty timestamps (buffered transport) -- check with
  `rostopic echo /imu/data | grep header.stamp`
- Not enough motion -- excite all axes, especially rotation
- Target partially occluded -- keep entire AprilGrid in frame
- Checkerboard flip ambiguity -- use AprilGrid for robustness

### LiDAR-Camera Extrinsic Calibration

**Target-based (heethesh/lidar_camera_calibration)**:
```bash
# Requires checkerboard visible in both camera and LiDAR FOV
# Place checkerboard at ~2-4m distance
roslaunch lidar_camera_calibration find_transform.launch
# Interactive GUI: select 4 corners in image, click corresponding LiDAR points
# Uses PnP + Levenberg-Marquardt optimization
```

**Target-less (direct_visual_lidar_calibration)**:
```bash
# Requires ROS1 or ROS2, works with any LiDAR model
# Minimum: 1 LiDAR-camera data pair (more is better)
rosrun direct_visual_lidar_calibration preprocess \
  --data_path /path/to/bag \
  --image_topic /camera/image_raw \
  --points_topic /velodyne_points

rosrun direct_visual_lidar_calibration calibrate \
  --data_path /path/to/data
```

**OA-LICalib** (LiDAR-IMU, in this workspace at `src/OA-LICalib/`):
Calibrates spatial-temporal extrinsics between LiDAR and IMU without targets.
Uses continuous-time trajectory optimization on B-splines.

### Publishing Calibration Results as TF

Once you have T_cam_lidar (4x4 homogeneous transform), publish it as TF:
```python
import numpy as np
from geometry_msgs.msg import TransformStamped
import tf2_ros
import tf_conversions  # converts between rotation representations

T = np.array([[...]])  # 4x4 homogeneous
q = tf_conversions.transformations.quaternion_from_matrix(T)
t = T[:3, 3]

br = tf2_ros.StaticTransformBroadcaster()
ts = TransformStamped()
ts.header.stamp = rospy.Time.now()
ts.header.frame_id = "lidar_frame"
ts.child_frame_id  = "camera_frame"
ts.transform.translation.x = t[0]
ts.transform.translation.y = t[1]
ts.transform.translation.z = t[2]
ts.transform.rotation.x = q[0]
ts.transform.rotation.y = q[1]
ts.transform.rotation.z = q[2]
ts.transform.rotation.w = q[3]
br.sendTransform(ts)
```

---

## 12. Common Sensor Message Types

### sensor_msgs/Imu

```
Header header
  uint32 seq
  time stamp
  string frame_id
geometry_msgs/Quaternion orientation
float64[9] orientation_covariance      # row-major, 0 = unknown
geometry_msgs/Vector3 angular_velocity  # rad/s
float64[9] angular_velocity_covariance
geometry_msgs/Vector3 linear_acceleration  # m/s^2 (not g's!)
float64[9] linear_acceleration_covariance
```

Set covariance diagonal to -1 if the measurement is unknown/invalid.

### sensor_msgs/PointCloud2

Key fields: `header.frame_id`, `header.stamp`, `height`, `width`,
`fields` (describes each field: x, y, z, intensity, ring, timestamp...),
`is_dense` (false if NaN points present), `data` (raw bytes).

```python
import sensor_msgs.point_cloud2 as pc2
for p in pc2.read_points(msg, field_names=("x","y","z","intensity"), skip_nans=True):
    x, y, z, i = p
```

### sensor_msgs/Image vs sensor_msgs/CompressedImage

`Image`: raw pixels, `encoding` field specifies format (bgr8, rgb8, mono8,
16UC1, 32FC1...). Large messages; use for processing.

`CompressedImage`: JPEG or PNG compressed. Smaller; use for recording.
Bridge:
```python
from cv_bridge import CvBridge
bridge = CvBridge()
cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
ros_image = bridge.cv2_to_imgmsg(cv_image, encoding='bgr8')
```

### sensor_msgs/CameraInfo

Contains: `K` (3x3 intrinsic), `D` (distortion coefficients), `R` (rectification),
`P` (projection for stereo). Must have same `header.stamp` as corresponding Image.
Published by camera driver; stored/retrieved via `/set_camera_info` service.

---

## 13. Common Errors and Fixes

### Build Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `[my_msgs/MyMsg.h] No such file` | Message not generated yet | Add `add_dependencies(target ${PROJECT_NAME}_generate_messages_cpp)` |
| `could not find package 'X'` | Missing ROS package | `sudo apt install ros-noetic-X` (use hyphens) |
| `colcon: command not found` | colcon not installed | `sudo apt install python3-colcon-common-extensions` |
| `No such file: install/setup.bash` | Not built yet | Run `colcon build` first |
| `CMake Error: target ... requires the language dialect "CXX14"` | C++ standard not set | Add `set(CMAKE_CXX_STANDARD 14)` before `find_package` |
| `undefined reference to symbol` | Missing `target_link_libraries` | Add the missing lib to `target_link_libraries(target ...)` |

### Runtime Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `[rosmaster] ROS_MASTER_URI ... is not accessible` | roscore not running, or wrong URI | `roscore` in another terminal; check `echo $ROS_MASTER_URI` |
| `ImportError: No module named rospy` | Wrong Python / not sourced | `source /opt/ros/noetic/setup.bash`; check Anaconda not shadowing |
| `No module named 'my_pkg.msg'` | Not built or install space not sourced | `colcon build --packages-select my_pkg && source install/setup.bash` |
| `Lookup would require extrapolation into the past` | use_sim_time mismatch | Set `rosparam set /use_sim_time true` before bag play |
| `Could not find a connection between frames` | TF tree disconnected | `rosrun tf view_frames` to diagnose; check frame_id strings |
| `Failed to transform Pointcloud from frame X to Y` | TF not available at that timestamp | Use `ros::Time(0)` or add timeout to lookupTransform |
| `WARN: Inbound TCP/IP connection failed` | Network/firewall issue | Check ROS_IP, ROS_HOSTNAME, ROS_MASTER_URI; `roswtf` |
| `[FATAL] Nodelet ... could not be found` | Plugin not registered or lib not built | Check `nodelet_plugins.xml`, rebuild, check export in package.xml |
| `terminate called after throwing ... bad_alloc` | Memory exhaustion | Reduce queue sizes; add voxel filter before large point cloud processing |
| `ros::Time::now() returned 0` | use_sim_time=true but no /clock publisher | Either `rosbag play --clock` or set `use_sim_time false` |

### TF-Specific Errors

```
[ WARN] [1234567890.000]: TF_REPEATED_DATA
```
Publishing the same transform too fast. Reduce publish rate or add deduplication.

```
[ WARN] [1234567890.000]: TF_OLD_DATA
```
Publishing transform with timestamp older than what's already in the buffer.
Often caused by processing delays; check your timestamp source.

```
[ERROR] Transform cache is full, dropping old entries
```
Default TF buffer is 10 seconds. Increase it:
```cpp
tf2_ros::Buffer tfBuffer(ros::Duration(30.0));  // 30-second buffer
```

---

## 14. ROS1 vs ROS2 Key Differences

Since many online resources now default to ROS2, know what does NOT apply to ROS1:

| Concept | ROS1 (Noetic) | ROS2 (Humble+) |
|---------|---------------|----------------|
| Discovery | rosmaster (central) | DDS (distributed) |
| Middleware | Custom TCPROS/UDPROS | DDS (pluggable: FastDDS, CycloneDDS) |
| Build tool | catkin_make / catkin build (typical) — **this project uses colcon** | colcon |
| CMake macros | catkin_package, catkin_INCLUDE_DIRS | ament_cmake, ament_target_dependencies |
| Node class | Free function + NodeHandle | Inherit from rclcpp::Node |
| Parameters | Global parameter server | Per-node parameters |
| QoS | Not configurable | Fully configurable (reliability, durability, history) |
| Lifecycle nodes | Not native | Built-in (unconfigured/inactive/active) |
| Executors | spin() / AsyncSpinner | SingleThreaded / MultiThreaded / StaticSingleThreaded |
| Security | None | DDS-Security (SROS2) |
| Bag format | .bag (custom) | .mcap or .db3 (sqlite) |
| CLI prefix | ros*, rqt* | ros2 topic/service/node... |
| Python | rospy | rclpy |
| C++ | roscpp | rclcpp |
| EOL | May 2025 (Noetic) | ROS2 Jazzy: May 2029 |

**Things to avoid confusing**:
- ROS2 has no `roscore` / `rosmaster` -- do not run it in a ROS2 system.
- This project uses `colcon build` for ROS1 packages — unusual but valid.
  Do not confuse this with ROS2's colcon; the packages are still catkin/ROS1.
- ROS2 launch files use Python (`.launch.py`) by default, not XML (though XML is
  also supported with different syntax).
- `rclcpp::spin()` and `ros::spin()` look the same but work differently.
- ros1_bridge allows ROS1/ROS2 interop but adds latency and complexity.

---

## 15. Environment Variables Reference

```bash
export ROS_DISTRO=noetic
export ROS_MASTER_URI=http://localhost:11311   # roscore address
export ROS_IP=192.168.1.100                   # this machine's IP (for multi-machine)
export ROS_HOSTNAME=robot.local               # use hostname instead of IP
export ROS_PACKAGE_PATH=/extra/pkgs:$ROS_PACKAGE_PATH  # add package search path
export ROSCONSOLE_FORMAT='[${severity}] [${time}] [${node}]: ${message}'
export ROSCONSOLE_CONFIG_FILE=/path/to/rosconsole.conf  # logging config

# For multi-machine robotics:
# On roscore machine:
export ROS_MASTER_URI=http://192.168.1.50:11311
export ROS_IP=192.168.1.50
# On remote machine:
export ROS_MASTER_URI=http://192.168.1.50:11311
export ROS_IP=192.168.1.101
```

Logging level config (`rosconsole.conf`):
```
# Set all nodes to INFO, specific node to DEBUG
log4j.logger.ros=INFO
log4j.logger.ros.my_pkg.calib_node=DEBUG
```

---

## 16. Quick Diagnostics Checklist

When something is not working, run through this in order:

1. `roscore` running? `ps aux | grep rosmaster`
2. Workspace sourced? `echo $ROS_PACKAGE_PATH`
3. `rosnode list` -- is the node running?
4. `rostopic list` -- are topics being published?
5. `rostopic hz /topic` -- is it at the expected rate?
6. `rostopic echo /topic -n 1` -- is the data valid? Check `frame_id`, `stamp`.
7. `rosrun tf view_frames` -- is the TF tree complete?
8. `roswtf` -- any warnings or errors?
9. `rqt_graph` -- are nodes connected as expected?
10. `rqt_console` -- any WARN/ERROR log messages?
11. Check timestamps: are `header.stamp` values reasonable vs `ros::Time::now()`?
12. Check `use_sim_time`: `rosparam get /use_sim_time` -- should be false when not
    replaying bags, true when replaying with `--clock`.

---

## 17. This Workspace

The workspace at `$HOME/workspace/fast_calib_ros1/workspace/` contains
multiple calibration-focused ROS1 packages under `src/`:

- `fast_calib` -- primary fast calibration package
- `OA-LICalib` -- LiDAR-IMU calibration via continuous-time trajectory
- `gril-calib` -- another LiDAR-IMU calibration approach
- `lidar_imu_init` -- initialization for LiDAR-IMU systems
- `AKF-LIO` -- Adaptive Kalman Filter LiDAR-Inertial Odometry
- `fast_livo2` -- fast LiDAR-Inertial-Visual Odometry v2
- `Point-LIO` -- point-level LiDAR-Inertial Odometry
- `Voxel-SLAM` -- voxel-based SLAM
- `rpg_vikit` -- vision utility kit (RPG)
- `driver/` -- sensor drivers
- `dag/` -- directed acyclic graph utilities
- `learn-to-calibrate` -- learning-based calibration

Build command for this workspace:
```bash
cd $HOME/workspace/fast_calib_ros1/workspace

# This project uses colcon (not catkin_make or catkin build)
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release
colcon build --packages-select fast_calib       # build single package
colcon build --parallel-workers 4               # limit parallelism

# Source after build
source install/setup.bash
```

> **Important:** Despite being a ROS1 workspace, this project uses `colcon`
> (the ROS2 build tool). colcon supports catkin packages via the
> `colcon-ros` extension. Always use `source install/setup.bash` (not
> `devel/setup.bash`) after a colcon build.
