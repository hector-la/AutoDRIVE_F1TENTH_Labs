#!/usr/bin/env python3
"""
Follow The Gap (FTG), version "normal" — para mapear con slam_toolbox sin
usar teleop.

Portado desde https://github.com/hector-la/follow-the-gap-f1tenth
(src/gap_node.py) — el algoritmo (preprocesar -> punto mas cercano ->
burbuja -> gap mas grande -> punto objetivo) es identico, puro numpy, sin
dependencias de ROS mas alla de rclpy.

Los parametros del algoritmo arrancaron copiados tal cual del repo
(tuneados para el mapa Sao Paulo de ese otro proyecto), pero varios se
retunearon el 19/08/2026 tras probar en este circuito y chocar repetido
en la misma curva cerrada: rango_max 6.8->3.0, fov_recorte 85->100 grados
(mirar mas angosto pero mas cerca evita apuntar a un punto que queda
detras de la pared en la curva), zona_muerta 1.5->20 grados y
alpha_suavizado 0.50->0.4 (menos reactivo, evitaba oscilacion en recta).
radio_burbuja se probo en 80 pero tapaba el gap bueno en un pasillo
angosto y empeoro el choque — quedo en 52 (valor del repo). Con este set
ya no choca en esa curva.

Lo que SI cambia, porque este workspace habla con AutoDRIVE (Unity), no
con f1tenth_gym:
  - Entrada: mismo tipo de mensaje (sensor_msgs/LaserScan), pero en
    /autodrive/f1tenth_1/lidar en vez de /scan.
  - Salida: AutoDRIVE no usa AckermannDriveStamped — usa dos Float32
    normalizados en [-1, 1] (throttle_command, steering_command), como
    teleop_hold.py. steering_angle (rad, tope 0.41 igual que el original)
    se normaliza dividiendo por ese mismo tope.
  - Velocidades: el original usa m/s reales (vel_recta=7.0, vel_curva=1.30)
    pensados para f1tenth_gym. Aca se reemplazan por los valores lentos ya
    probados para mapeo (throttle_recta=0.18, throttle_curva=0.10,
    normalizados) — mapear rapido genera drift y deforma el mapa; mas
    lento = scans mas consistentes y mejor scan-matching.
  - Se quito el contador de vueltas por odometria (usaba /ego_racecar/odom,
    que no existe aqui) — no hace falta para mapear.
"""

import math
import signal
import time
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float32


class ReactiveFollowGap(Node):
    def __init__(self):
        super().__init__('gap_node')
        self.get_logger().info("FTG (gap_node, modo mapeo lento) iniciado")

        qos = QoSProfile(depth=1)
        self.create_subscription(LaserScan, '/autodrive/f1tenth_1/lidar', self.lidar_callback, 10)
        self.pub_throttle = self.create_publisher(Float32, '/autodrive/f1tenth_1/throttle_command', qos)
        self.pub_steering = self.create_publisher(Float32, '/autodrive/f1tenth_1/steering_command', qos)

        # --- PARÁMETROS DEL ALGORITMO (copiados tal cual de gap_node.py) ---
        # rango_max/fov vueltos a los valores viejos probados en este circuito
        # (ftg_slam original) — con 6.8m/85° el auto apuntaba a un punto lejano
        # que quedaba detrás de la pared en la curva cerrada, cortando la
        # esquina interior. radio_burbuja vuelto a 52 (repo) — 80 tapaba el
        # gap bueno en ese pasillo angosto y empeoró el choque.
        self.rango_max = 3.0
        self.radio_burbuja = 52
        self.ventana_suavizado = 3
        self.umbral_gap = 1.7
        self.fov_recorte = math.radians(100)

        # --- VELOCIDADES: normalizadas [-1, 1], bajas a propósito para mapear ---
        # (la prueba a 1.0/0.19 — full throttle, misma proporción que el
        # repo original — se probó el 19/08/2026 y chocó; de vuelta a lento)
        self.throttle_recta = 0.18
        self.throttle_curva = 0.10

        # --- ANTI-OSCILACIÓN ---
        # zona_muerta y alpha vueltos a los valores tuneados para este circuito
        # (ftg_slam original) en vez de los del repo (1.5°/0.50) — con esos el
        # steering oscilaba en recta antes de llegar a chocar.
        self.steer_max_rad = 0.41             # tope físico usado para normalizar a [-1, 1]
        self.zona_muerta = math.radians(20)
        self.alpha_suavizado = 0.4
        self.steering_previo = 0.0

        self.idx_inicio = None
        self.idx_fin = None

    # ----------------------------------------------------------
    def preprocess_lidar(self, ranges):
        proc = np.array(ranges, dtype=np.float64)
        proc[np.isinf(proc)] = 0.0
        proc[np.isnan(proc)] = 0.0
        proc[proc > self.rango_max] = self.rango_max
        if self.ventana_suavizado > 1:
            kernel = np.ones(self.ventana_suavizado) / self.ventana_suavizado
            proc = np.convolve(proc, kernel, mode='same')
        return proc

    # ----------------------------------------------------------
    def find_max_gap(self, free_space_ranges):
        libre = free_space_ranges > self.umbral_gap
        mejor_inicio, mejor_fin, mejor_largo = 0, 0, 0
        inicio_actual = None

        for i, es_libre in enumerate(libre):
            if es_libre:
                if inicio_actual is None:
                    inicio_actual = i
            else:
                if inicio_actual is not None:
                    largo = i - inicio_actual
                    if largo > mejor_largo:
                        mejor_largo = largo
                        mejor_inicio, mejor_fin = inicio_actual, i - 1
                    inicio_actual = None

        if inicio_actual is not None:
            largo = len(libre) - inicio_actual
            if largo > mejor_largo:
                mejor_inicio, mejor_fin = inicio_actual, len(libre) - 1

        return mejor_inicio, mejor_fin

    # ----------------------------------------------------------
    def find_best_point(self, start_i, end_i):
        return (start_i + end_i) // 2

    # ----------------------------------------------------------
    def lidar_callback(self, data):
        angle_min = data.angle_min
        angle_increment = data.angle_increment

        if self.idx_inicio is None:
            centro = len(data.ranges) // 2
            n_rayos = int(self.fov_recorte / angle_increment)
            self.idx_inicio = max(0, centro - n_rayos)
            self.idx_fin = min(len(data.ranges), centro + n_rayos)

        proc = self.preprocess_lidar(data.ranges)
        frente = proc[self.idx_inicio:self.idx_fin]

        idx_cercano = np.argmin(frente)
        ini_burbuja = max(0, idx_cercano - self.radio_burbuja)
        fin_burbuja = min(len(frente), idx_cercano + self.radio_burbuja)
        frente[ini_burbuja:fin_burbuja] = 0.0

        gap_inicio, gap_fin = self.find_max_gap(frente)
        idx_objetivo = self.find_best_point(gap_inicio, gap_fin)

        idx_global = idx_objetivo + self.idx_inicio
        steering_angle = angle_min + idx_global * angle_increment

        if abs(steering_angle) < self.zona_muerta:
            steering_angle = 0.0

        steering_angle = (self.alpha_suavizado * steering_angle +
                          (1 - self.alpha_suavizado) * self.steering_previo)
        self.steering_previo = steering_angle
        steering_angle = max(-self.steer_max_rad, min(self.steer_max_rad, steering_angle))

        # Velocidad: interpolación lineal entre recta y curva, igual lógica que el original
        factor_giro = abs(steering_angle) / self.steer_max_rad
        throttle = self.throttle_recta - (self.throttle_recta - self.throttle_curva) * factor_giro

        # Normalizar steering de rad a [-1, 1]
        steering_norm = steering_angle / self.steer_max_rad

        throttle_msg = Float32(data=float(max(-1.0, min(1.0, throttle))))
        steering_msg = Float32(data=float(max(-1.0, min(1.0, steering_norm))))
        self.pub_throttle.publish(throttle_msg)
        self.pub_steering.publish(steering_msg)


def _stop_vehicle(node):
    """Publica throttle/steering en 0 varias veces, con un sleep entre medio
    para darle tiempo al DDS de realmente mandarlos antes de que el proceso
    muera. NO usa spin_once() aca: publicar no necesita spinear (eso es solo
    para recibir callbacks), y llamar spin_once() desde un signal handler que
    dispara en medio de un rclpy.spin() ya activo es una llamada anidada que
    puede fallar en silencio en vez de esperar — ese era el bug real."""
    stop = Float32(data=0.0)
    for _ in range(5):
        node.pub_throttle.publish(stop)
        node.pub_steering.publish(stop)
        time.sleep(0.03)


def main(args=None):
    # Manejo de señales, dos intentos previos que NO sirvieron (probados con
    # procesos reales, no en teoria) antes de llegar a este:
    #   1) rclpy.init() por defecto: SIGINT/SIGTERM SI interrumpen spin()
    #      (lanzan KeyboardInterrupt / ExternalShutdownException), pero para
    #      cuando eso pasa rclpy.ok() ya es False y el contexto ya esta
    #      invalido — publish() despues falla con
    #      "publisher's context is invalid". El auto nunca recibia el freno.
    #   2) signal_handler_options=NO + signal.signal() propio + rclpy.spin()
    #      bloqueante: el handler de Python NUNCA se ejecuta, porque spin()
    #      bloquea en una espera C sin timeout que no le da chance al
    #      interprete de correr el handler — se queda colgado.
    # Lo que si funciona: desactivar el manejo automatico, pero reemplazar el
    # spin() bloqueante por un loop de spin_once() con timeout CORTO. Entre
    # cada iteracion el interprete si tiene chance de correr el handler, que
    # ademas no hace nada mas que levantar una bandera (nunca publicar directo
    # desde el handler) — recien con el contexto todavia vivo, publicamos el
    # freno desde el loop principal.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = ReactiveFollowGap()

    detener = {'flag': False}

    def _on_shutdown_signal(signum, frame):
        detener['flag'] = True  # cubre Ctrl+C (SIGINT) y `kill <pid>` (SIGTERM)

    signal.signal(signal.SIGINT, _on_shutdown_signal)
    signal.signal(signal.SIGTERM, _on_shutdown_signal)

    try:
        while not detener['flag']:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        _stop_vehicle(node)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
