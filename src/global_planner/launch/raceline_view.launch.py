#!/usr/bin/env python3
# Levanta bridge + RViz + mapa real (bridge_with_map.launch.py del paquete
# `controllers`) y le suma el publicador de la raceline (Dijkstra + Fem-pos)
# generada por ~/Global_Planner/f1tenth/autodrive_dijkstra_smooth.py.
#
#   ros2 launch global_planner raceline_view.launch.py
#
# (usa los defaults: mapa real guardado + raceline de este repo). Para
# apuntar a otro mapa/CSV: map:=... csv_path:=...
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    gp_share = get_package_share_directory('global_planner')
    controllers_share = get_package_share_directory('controllers')

    map_arg = DeclareLaunchArgument(
        'map',
        default_value=os.path.expanduser(
            '~/autodrive/f1tenth_ws/maps/autodrive_maps_of.yaml'),
        description='Ruta absoluta al .yaml del mapa guardado por slam_toolbox'
    )
    csv_path_arg = DeclareLaunchArgument(
        'csv_path',
        default_value=os.path.join(gp_share, 'racelines', 'dijkstra_autodrive_of.csv'),
        description='CSV de la raceline a publicar (x,y,heading,kappa,v)'
    )

    bridge_with_map = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(controllers_share, 'launch', 'bridge_with_map.launch.py')),
        launch_arguments={'map': LaunchConfiguration('map')}.items(),
    )

    raceline_node = Node(
        package='global_planner',
        executable='raceline_publisher',
        name='raceline_publisher',
        parameters=[{'csv_path': LaunchConfiguration('csv_path'),
                    'frame_id': 'map'}],
        output='screen',
    )

    return LaunchDescription([
        map_arg,
        csv_path_arg,
        bridge_with_map,
        raceline_node,
    ])
