#!/usr/bin/env python3

# ============================================================
# raceline_publisher.py — carga la raceline CSV (Dijkstra + Fem-pos,
# ver ~/Global_Planner/f1tenth/autodrive_dijkstra_smooth.py) y la publica:
#   /raceline          nav_msgs/Path         (para el controlador RPP)
#   /raceline_markers  visualization_msgs/MarkerArray
#                      (LINE_STRIP coloreada por velocidad, RViz)
#
# Port directo de roboracer-f1tenth/src/path_planning/path_planning/
# raceline_publisher.py — mismo contrato de CSV (x,y,heading,kappa,v),
# solo cambia el paquete/frame de destino (AutoDRIVE, frame `map`).
#
# QoS transient_local (latched): quien se suscriba después de la
# publicación también la recibe — la raceline es estática.
#
# Parámetros:
#   csv_path (str)  — ruta al CSV (x,y,heading,kappa,v con header)
#   frame_id (str)  — frame de referencia (default: map)
# ============================================================

import math

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy

from geometry_msgs.msg import Point, PoseStamped
from nav_msgs.msg import Path
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray


def _v_to_color(v, v_min, v_max):
    """Mapea velocidad a color azul (lento) → rojo (rápido)."""
    t = 0.0 if v_max <= v_min else (v - v_min) / (v_max - v_min)
    return ColorRGBA(r=float(t), g=0.2, b=float(1.0 - t), a=1.0)


class RacelinePublisher(Node):
    def __init__(self):
        super().__init__('raceline_publisher')
        self.declare_parameter('csv_path', '')
        self.declare_parameter('frame_id', 'map')

        csv_path = self.get_parameter('csv_path').value
        self.frame_id = self.get_parameter('frame_id').value
        if not csv_path:
            raise RuntimeError("Parámetro 'csv_path' vacío: pásame el CSV de la raceline.")

        # Contrato: x,y,heading,kappa,v (ver track_utils.save_raceline_csv
        # en Global_Planner/f1tenth) — indexado por columna, no por unpack de
        # ancho fijo, por si el CSV suma columnas mas adelante.
        data = np.loadtxt(csv_path, delimiter=',', skiprows=1)
        self.x = data[:, 0]
        self.y = data[:, 1]
        self.heading = data[:, 2]
        self.kappa = data[:, 3]
        self.v = data[:, 4]
        self.get_logger().info(
            f"Raceline cargada: {len(self.x)} waypoints de {csv_path}")

        latched = QoSProfile(depth=1,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.path_pub = self.create_publisher(Path, '/raceline', latched)
        self.marker_pub = self.create_publisher(MarkerArray, '/raceline_markers', latched)

        self._publish()
        # Refresco lento por si un suscriptor volátil llega tarde.
        self.create_timer(5.0, self._publish)

    def _publish(self):
        now = self.get_clock().now().to_msg()

        path = Path()
        path.header.frame_id = self.frame_id
        path.header.stamp = now
        for xi, yi, hi in zip(self.x, self.y, self.heading):
            ps = PoseStamped()
            ps.header = path.header
            ps.pose.position.x = float(xi)
            ps.pose.position.y = float(yi)
            ps.pose.orientation.z = math.sin(hi / 2.0)
            ps.pose.orientation.w = math.cos(hi / 2.0)
            path.poses.append(ps)
        self.path_pub.publish(path)

        line = Marker()
        line.header.frame_id = self.frame_id
        line.header.stamp = now
        line.ns = 'raceline'
        line.id = 0
        line.type = Marker.LINE_STRIP
        line.action = Marker.ADD
        line.scale.x = 0.05
        v_min, v_max = float(self.v.min()), float(self.v.max())
        for xi, yi, vi in zip(self.x, self.y, self.v):
            line.points.append(Point(x=float(xi), y=float(yi), z=0.02))
            line.colors.append(_v_to_color(vi, v_min, v_max))
        # cerrar el lazo visualmente (la raceline es una vuelta cerrada)
        line.points.append(line.points[0])
        line.colors.append(line.colors[0])
        self.marker_pub.publish(MarkerArray(markers=[line]))


def main(args=None):
    rclpy.init(args=args)
    node = RacelinePublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
