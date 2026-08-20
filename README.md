# AutoDRIVE F1TENTH Labs

Lab de SLAM (mapeo 2D) para el F1TENTH en el simulador [AutoDRIVE](https://github.com/Tinker-Twins/AutoDRIVE), pensado para el club AIRos.

## Requisito previo

Este repo **no instala nada por sí solo** — asume que ya seguiste el starter kit y probaste el teleop que trae AutoDRIVE (`ros2 run autodrive_f1tenth teleop_keyboard`):

👉 **[AutoDRIVE_DevKit_Starter](https://github.com/hector-la/AutoDRIVE_DevKit_Starter)**

Si ya tenés `~/autodrive/f1tenth_ws` compilado y ese teleop funcionando, andá directo al Lab 3 de acá abajo.

## Cómo usar este repo

Copiá (o cloná y copiá) las carpetas de este repo dentro de tu workspace:

```bash
git clone https://github.com/hector-la/AutoDRIVE_F1TENTH_Labs.git
cp -r AutoDRIVE_F1TENTH_Labs/src/controllers ~/autodrive/f1tenth_ws/src/
cp -r AutoDRIVE_F1TENTH_Labs/src/config ~/autodrive/f1tenth_ws/src/
cp -r AutoDRIVE_F1TENTH_Labs/Laboratories ~/autodrive/f1tenth_ws/
```

Después:

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash
colcon build --symlink-install && source install/setup.bash
```

Verificación rápida (el shebang debe apuntar al venv, no al Python del sistema):

```bash
head -1 install/controllers/lib/controllers/gap_node
# esperado: #!/home/<tu_usuario>/autodrive/f1tenth_ws/venv/bin/python3
```

## Qué hay acá

```
src/
├── controllers/         # paquete ROS 2 con el nodo de control
│   └── controllers/
│       └── gap_node.py      # Follow The Gap — navegación reactiva autónoma, para mapear sin manos
└── config/
    └── mapper_params_online_async.yaml   # config de slam_toolbox para este setup

Laboratories/
├── Tutorial_3_SLAM.md            # Lab 3: SLAM explicado paso a paso, con el porqué de cada comando
└── SLAM_Comandos_Rapidos.md      # la misma guía, solo comandos, para consulta rápida
```

## Lab 3 — SLAM (mapeo 2D)

1. Seguí `Laboratories/Tutorial_3_SLAM.md` de punta a punta (explica cada paso) — o `Laboratories/SLAM_Comandos_Rapidos.md` si ya lo hiciste una vez y solo necesitás los comandos.
2. Vas a: instalar `slam_toolbox`, levantar simulador + bridge + `slam_toolbox` + `gap_node` (maneja solo, no hace falta teleop), mapear el circuito, y guardar el mapa (como imagen `.pgm`/`.yaml` y como pose-graph nativo de `slam_toolbox`).

## Agregar tu propio nodo

El patrón: creás el archivo en `src/controllers/controllers/`, lo registrás como entrypoint en `src/controllers/setup.py`, `colcon build --symlink-install`, y `ros2 run controllers <nombre>`.

```python
class MiNodo(Node):
    def __init__(self):
        super().__init__('nombre_del_nodo')
        self.create_subscription(LaserScan, '/autodrive/f1tenth_1/lidar', self.lidar_cb, 10)
        self.throttle_pub = self.create_publisher(Float32, '/autodrive/f1tenth_1/throttle_command', 1)
        self.steering_pub = self.create_publisher(Float32, '/autodrive/f1tenth_1/steering_command', 1)

    def lidar_cb(self, msg):
        # msg.ranges, msg.angle_min/max/increment
        self.throttle_pub.publish(Float32(data=...))   # [-1, 1]
        self.steering_pub.publish(Float32(data=...))    # [-1, 1]
```

## Tópicos clave (F1TENTH)

| Tópico | Tipo | Dirección |
|---|---|---|
| `/autodrive/f1tenth_1/throttle_command` | `std_msgs/Float32` | → sim |
| `/autodrive/f1tenth_1/steering_command` | `std_msgs/Float32` | → sim |
| `/autodrive/f1tenth_1/lidar` | `sensor_msgs/LaserScan` | ← sim |
| `/autodrive/f1tenth_1/imu` | `sensor_msgs/Imu` | ← sim |
| `/autodrive/f1tenth_1/ips` | `geometry_msgs/Point` | ← sim |
| `/autodrive/f1tenth_1/front_camera` | `sensor_msgs/Image` | ← sim |

TF: `map → f1tenth_1 → {lidar, imu, ips, front_camera, ...}`.

## Créditos

`gap_node.py` porta el algoritmo de [follow-the-gap-f1tenth](https://github.com/hector-la/follow-the-gap-f1tenth). `Tutorial_3_SLAM.md` está adaptado del [Tutorial 3 de nabihandres/AUTODRIVE](https://github.com/nabihandres/AUTODRIVE/blob/main/Tutorial%203%3A%20Simultaneous%20Localization%20and%20Maping.md).
