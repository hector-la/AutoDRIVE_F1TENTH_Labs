#!/usr/bin/env python3
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    map_yaml_arg = DeclareLaunchArgument(
        'map',
        description='Ruta absoluta al .yaml del mapa guardado'
    )

    # --- Bridge de AutoDRIVE + RViz (igual que simulator_bringup_rviz.launch.py) ---
    incoming_bridge = Node(
        package='autodrive_f1tenth',
        executable='autodrive_incoming_bridge',
        name='autodrive_incoming_bridge',
        emulate_tty=True,
        output='screen',
    )
    outgoing_bridge = Node(
        package='autodrive_f1tenth',
        executable='autodrive_outgoing_bridge',
        name='autodrive_outgoing_bridge',
        emulate_tty=True,
        output='screen',
    )
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz',
        arguments=['-d', [FindPackageShare('autodrive_f1tenth'), '/rviz', '/simulator.rviz']],
    )

    # --- Mapa guardado, activado automáticamente ---
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'yaml_filename': LaunchConfiguration('map')}],
    )
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map',
        output='screen',
        parameters=[{
            'autostart': True,
            'node_names': ['map_server'],
        }],
    )

    return LaunchDescription([
        map_yaml_arg,
        incoming_bridge,
        outgoing_bridge,
        rviz,
        # map_server publica /map una sola vez, al activarse — si RViz todavía no
        # se termino de suscribir en ese instante, se pierde ese mensaje para
        # siempre (el display Map de RViz usa QoS VOLATILE, que no recibe el
        # historico cacheado de un publisher TRANSIENT_LOCAL como map_server,
        # solo lo que se publique despues de que ya esta suscripto). Por eso
        # retrasamos map_server/lifecycle_manager unos segundos: le da tiempo a
        # RViz de arrancar y suscribirse ANTES de que salga esa unica publicacion.
        TimerAction(period=5.0, actions=[map_server, lifecycle_manager]),
    ])



