# AutoDRIVE F1TENTH Labs

Lab de SLAM (mapeo 2D) para el F1TENTH en el simulador [AutoDRIVE](https://github.com/Tinker-Twins/AutoDRIVE), pensado para el club AIRos.

## Requisito previo

Este repo **no instala nada por sí solo** — asume que ya seguiste el starter kit y probaste el teleop que trae AutoDRIVE (`ros2 run autodrive_f1tenth teleop_keyboard`):

👉 **[AutoDRIVE_DevKit_Starter](https://github.com/hector-la/AutoDRIVE_DevKit_Starter)**

Si ya tenés `~/autodrive/f1tenth_ws` compilado y ese teleop funcionando, andá directo al Lab 3 de acá abajo.

## Cómo usar este repo

Son 4 comandos, uno atrás del otro, sin cambiar de carpeta entre medio (los `cp -r` usan rutas relativas a donde clonaste). Parate en cualquier carpeta que **no** sea `~/autodrive/f1tenth_ws` (por ejemplo tu home, `cd ~`) y corré:

```bash
git clone https://github.com/hector-la/AutoDRIVE_F1TENTH_Labs.git
cp -r AutoDRIVE_F1TENTH_Labs/src/controllers ~/autodrive/f1tenth_ws/src/
cp -r AutoDRIVE_F1TENTH_Labs/src/config ~/autodrive/f1tenth_ws/src/
cp -r AutoDRIVE_F1TENTH_Labs/Laboratories ~/autodrive/f1tenth_ws/
```

El primero (`git clone`) descarga el repo entero a una carpeta nueva `AutoDRIVE_F1TENTH_Labs/`. Los otros tres copian, cada uno, solo la carpeta puntual que necesitás dentro de tu workspace real. Una vez copiado, la carpeta clonada ya no hace falta — podés borrarla si querés (`rm -rf AutoDRIVE_F1TENTH_Labs`), tu workspace ya tiene su propia copia independiente.

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

## Laboratorios

- **Lab 3 — SLAM (mapeo 2D):** [`Laboratories/Tutorial_3_SLAM.md`](Laboratories/Tutorial_3_SLAM.md) — instalás `slam_toolbox`, levantás simulador + bridge + `slam_toolbox` + `gap_node` (maneja solo, no hace falta teleop), mapeás el circuito, y guardás el mapa (imagen `.pgm`/`.yaml` + pose-graph nativo de `slam_toolbox`). Explicado paso a paso, con el porqué de cada comando.
  - Versión solo-comandos, para cuando ya hiciste el lab una vez y no necesitás la explicación: [`Laboratories/SLAM_Comandos_Rapidos.md`](Laboratories/SLAM_Comandos_Rapidos.md).

Más labs se van a ir agregando acá a medida que se armen.

## Notas y consideraciones

### Si querés crear tu propio nodo

Esto no es parte del Lab 3 — sirve para cuando quieras programar tu propio controlador (otro algoritmo de Follow The Gap, un wall-follower, PID, pure pursuit, lo que sea) en vez de usar el `gap_node` que ya viene armado. Todos los nodos de control viven en el mismo paquete ROS 2, `controllers`. Para agregar uno propio:

#### 1. Crear el archivo del nodo

En `src/controllers/controllers/`, creá un `.py` nuevo — por ejemplo `mi_nodo.py`:

```bash
cd ~/autodrive/f1tenth_ws
nano src/controllers/controllers/mi_nodo.py
```

Con el boilerplate mínimo (mismo patrón que usa `gap_node.py`: se suscribe al LiDAR, publica throttle/steering):

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float32


class MiNodo(Node):
    def __init__(self):
        super().__init__('nombre_del_nodo')
        self.create_subscription(LaserScan, '/autodrive/f1tenth_1/lidar', self.lidar_cb, 10)
        self.throttle_pub = self.create_publisher(Float32, '/autodrive/f1tenth_1/throttle_command', 1)
        self.steering_pub = self.create_publisher(Float32, '/autodrive/f1tenth_1/steering_command', 1)

    def lidar_cb(self, msg):
        # msg.ranges, msg.angle_min/max/increment — tu lógica acá
        self.throttle_pub.publish(Float32(data=0.0))    # [-1, 1]
        self.steering_pub.publish(Float32(data=0.0))    # [-1, 1]


def main(args=None):
    rclpy.init(args=args)
    node = MiNodo()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

#### 2. Registrar el entrypoint

Abrí `src/controllers/setup.py` y agregá una línea en `entry_points` → `console_scripts` (el formato es `'<comando_que_vas_a_escribir> = controllers.<nombre_del_archivo_sin_.py>:main'`):

```python
    entry_points={
        'console_scripts': [
            'gap_node = controllers.gap_node:main',
            'mi_nodo = controllers.mi_nodo:main',   # ← la línea nueva
        ],
    },
```

Este paso es el que le dice a ROS 2 qué comando (`ros2 run controllers mi_nodo`) corresponde a qué archivo — sin esto, el archivo existe pero no es ejecutable como nodo.

#### 3. Compilar

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

`--symlink-install` es clave: crea un enlace simbólico al `.py` en vez de copiarlo. Gracias a eso, **si después solo editás el contenido del archivo** (sin agregar/quitar nodos ni tocar `setup.py`), los cambios quedan disponibles al instante — no hace falta repetir `colcon build`. Sí hace falta recompilar cuando agregás un archivo nuevo (como ahora) o cambiás algo en `setup.py`.

#### 4. Correrlo

```bash
ros2 run controllers mi_nodo
```

Si da `No executable found`, casi siempre es que faltó el paso 3 (recompilar) después de registrar el entrypoint.

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
