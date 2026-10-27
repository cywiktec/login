cmake_minimum_required(VERSION 3.8)
project(guardian_interfaces)

find_package(ament_cmake REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "ros2_msgs/GuardianState.msg"
  "ros2_msgs/HealthStatus.msg"
  "ros2_msgs/BatteryStatus.msg"
  "ros2_srvs/SendCommand.srv"
  "ros2_srvs/TakeSnapshot.srv"
  "ros2_srvs/Recover.srv"
  "ros2_actions/ExecuteMission.action"
  DEPENDENCIES builtin_interfaces
)

ament_package()
