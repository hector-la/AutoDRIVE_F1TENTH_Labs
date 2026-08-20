# Tutorial 4: Traer una Planificación Global (raceline) a AutoDRIVE

## Qué cubre esto (y qué NO)

Este tutorial **no explica cómo generar una raceline** — no hay Dijkstra, A*, RRT, Cubic-Spline, Fem-pos ni ningún algoritmo de planificación/suavizado acá. Eso es trabajo tuyo, en tu propio proyecto de planificación global (Parte B), separado de este workspace ROS.

Lo que sí cubre: **cómo traer el resultado de esa planificación** (una lista de waypoints ya calculada y suavizada) **a AutoDRIVE**, para que se vea alineada con el mapa y el auto en RViz, y quede disponible como tópico ROS 2 para que un controlador (Pure Pursuit, RPP, MPC, lo que uses) la pueda seguir.

**Prerrequisito:** un mapa ya guardado por SLAM (`Tutorial_3_SLAM.md`, el `.pgm`/`.yaml` en `maps/`) y un proyecto propio, aparte de este workspace ROS, donde vayas a correr tu algoritmo de planificación global + suavizado sobre ese mapa.

## 0. Antes de empezar: llevar el mapa a tu proyecto de planificación

Tu proyecto de planificación **no vive dentro de `~/autodrive/f1tenth_ws`** — es otra carpeta, otro repo, lo que sea que hayas armado para tu algoritmo (Dijkstra, A*, RRT...) y tu suavizado (Cubic-Spline, B-Spline, Fem-pos...). Antes de correr nada ahí, ese proyecto necesita su propia copia del mapa:

```bash
cp ~/autodrive/f1tenth_ws/maps/<tu_mapa>.pgm ~/autodrive/f1tenth_ws/maps/<tu_mapa>.yaml \
   <ruta a la carpeta de mapas de tu proyecto de planificación>
```

Simplemente **copiás los dos archivos tal cual** (el `.pgm` con la imagen del mapa y el `.yaml` con `resolution`/`origin`/umbrales) — no hace falta convertir nada ni tocar el contenido. Tu proyecto de planificación es quien decide cómo organizar sus propias carpetas (`maps/`, `waypoints/`, `plots/`, o lo que uses); esa estructura es tuya, no depende de este tutorial.

**Puede que tu propio proyecto, al procesar ese mapa, genere ahí archivos intermedios** — por ejemplo un `.yaml` propio si tu código espera un formato distinto, imágenes de control (`.png`) mostrando la ruta calculada, un CSV "crudo" antes de suavizar, etc. Todo eso es normal y queda **del lado de tu proyecto de planificación**, no de este repo — no hay nada que traer de vuelta hasta que tengas el resultado final.

Con el mapa copiado, corré ahí tu algoritmo de planificación + suavizado. Al terminar, ese proceso te debería dejar el **resultado final**: la raceline ya calculada y suavizada, exportada como un CSV. Ese CSV es lo único que traemos de vuelta a este repo — el resto de lo que se haya generado en el camino se queda en tu proyecto de planificación.

## El contrato: qué tiene que tener el CSV

Para que el nodo de este tutorial lo pueda leer sin cambios, el CSV necesita:

```csv
x,y,heading,kappa,v
0.765,2.955,-1.5555,0.00466,2.0
0.7688,2.7042,-1.55667,0.00466,2.0
...
```

| Columna | Unidad | Qué es |
|---|---|---|
| `x`, `y` | metros, frame `map` | Posición del waypoint. **Mismo frame que usa el mapa guardado por SLAM** — ver más abajo por qué eso ya viene gratis. |
| `heading` | radianes | Orientación del waypoint (tangente a la trayectoria). Se usa para la pose completa del `Path`, no solo el punto. |
| `kappa` | 1/metro | Curvatura en ese punto (`1/radio`). No la usa el publicador, pero un controlador tipo RPP la puede necesitar para regular velocidad. |
| `v` | m/s | Velocidad objetivo en ese waypoint. Puede ser constante (si tu controlador regula velocidad solo, como hace RPP por curvatura) o un perfil real. |

Con header, separado por comas, sin índice. Si tu planificador solo te da `x,y`, tenés que calcular `heading` (con `atan2` entre puntos consecutivos) y `kappa` (curvatura por diferencias finitas) antes de exportar — no es trabajo de este tutorial, pero es un cálculo de una función, no un algoritmo nuevo.

### Por qué el frame `map` es gratis

AutoDRIVE publica la TF `map → f1tenth_1` en vivo (posición real del auto) y `slam_toolbox`/`map_server` guardan y sirven el mapa en ese mismo frame `map` (ver `resolution`/`origin` del `.yaml`). Si tu planificador calculó los waypoints en metros usando el `resolution`/`origin` de ese mismo `.yaml`, ya salen alineados — no hace falta ninguna transformación extra entre "tu proyecto de planificación" y "AutoDRIVE".

## 1. Crear el paquete ROS 2

```bash
cd ~/autodrive/f1tenth_ws/src
mkdir -p global_planner/global_planner global_planner/launch global_planner/racelines global_planner/resource
touch global_planner/global_planner/__init__.py
touch global_planner/resource/global_planner
```

### `package.xml`
```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>global_planner</name>
  <version>0.0.1</version>
  <description>Publica una raceline (CSV x,y,heading,kappa,v) generada externamente, para RViz y el controlador</description>
  <maintainer email="tu-email@ejemplo.com">tu-nombre</maintainer>
  <license>MIT</license>

  <depend>rclpy</depend>
  <depend>std_msgs</depend>
  <depend>geometry_msgs</depend>
  <depend>nav_msgs</depend>
  <depend>visualization_msgs</depend>

  <test_depend>ament_copyright</test_depend>
  <test_depend>ament_flake8</test_depend>
  <test_depend>ament_pep257</test_depend>
  <test_depend>python3-pytest</test_depend>

  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
```

### `setup.cfg`
```ini
[develop]
script_dir=$base/lib/global_planner
[install]
install_scripts=$base/lib/global_planner
```

### `setup.py`
```python
import os
from glob import glob
from setuptools import find_packages, setup
package_name = 'global_planner'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'racelines'), glob('racelines/*.csv')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='tu-nombre',
    maintainer_email='tu-email@ejemplo.com',
    description='Publica una raceline generada externamente',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'raceline_publisher = global_planner.raceline_publisher:main',
        ],
    },
)
```

`data_files` con `glob('racelines/*.csv')` es lo que hace que cualquier CSV que dejes en `racelines/` se instale junto con el paquete — no hace falta declarar cada archivo a mano.

## 2. El nodo `raceline_publisher`

`global_planner/global_planner/raceline_publisher.py`:

```python
#!/usr/bin/env python3
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

        data = np.loadtxt(csv_path, delimiter=',', skiprows=1)
        self.x, self.y = data[:, 0], data[:, 1]
        self.heading, self.kappa, self.v = data[:, 2], data[:, 3], data[:, 4]
        self.get_logger().info(f"Raceline cargada: {len(self.x)} waypoints de {csv_path}")

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.path_pub = self.create_publisher(Path, '/raceline', latched)
        self.marker_pub = self.create_publisher(MarkerArray, '/raceline_markers', latched)

        self._publish()
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
        line.points.append(line.points[0])   # cierra el lazo visualmente
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
```

### Qué hace, en dos frases
Lee el CSV **una vez** al arrancar (no vuelve a tocar el archivo) y publica dos tópicos, latcheados (`TRANSIENT_LOCAL` — igual que `map_server`, así un suscriptor que llega tarde igual recibe el último mensaje):
- **`/raceline`** (`nav_msgs/Path`) — el contrato estándar de ROS/Nav2, pensado para que lo consuma un **controlador** (no lo escucha nadie todavía en este tutorial).
- **`/raceline_markers`** (`visualization_msgs/MarkerArray`) — solo para que **RViz** lo dibuje (línea coloreada por velocidad).

Es un nodo puramente **publisher** — no se suscribe a nada. Quien "escucha" hoy es RViz (con un display `MarkerArray` apuntando a `/raceline_markers`); el día que armes un controlador, ese será otro nodo que se suscribe a `/raceline` — sin tocar este archivo para nada, quedan conectados solo por el nombre del tópico.

## 3. El launch file

`global_planner/launch/raceline_view.launch.py` — no arranca nada "desde cero", **combina** `bridge_with_map.launch.py` (el bridge + RViz + el mapa, ya armado en `Tutorial_3_SLAM.md` / `controllers/launch/`) con el nodo de arriba:

```python
#!/usr/bin/env python3
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
        default_value=os.path.expanduser('~/autodrive/f1tenth_ws/maps/<tu_mapa>.yaml'),
        description='Ruta absoluta al .yaml del mapa guardado por slam_toolbox'
    )
    csv_path_arg = DeclareLaunchArgument(
        'csv_path',
        default_value=os.path.join(gp_share, 'racelines', '<tu_raceline>.csv'),
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
        parameters=[{'csv_path': LaunchConfiguration('csv_path'), 'frame_id': 'map'}],
        output='screen',
    )

    return LaunchDescription([map_arg, csv_path_arg, bridge_with_map, raceline_node])
```

`IncludeLaunchDescription` mete otro launch file adentro de este sin copiar su código — reusa `bridge_with_map.launch.py` tal cual, con su mismo `TimerAction` de 5s que evita la carrera de QoS del `Map` display (ver `Tutorial_3_SLAM.md`).

## 4. Traer el CSV y compilar

```bash
cp <ruta a tu CSV generado por tu proyecto de planificación> \
   ~/autodrive/f1tenth_ws/src/global_planner/racelines/<tu_raceline>.csv

cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select global_planner
```

**Importante:** `--symlink-install` symlinkea los `.py`, pero los `data_files` como los CSV de `racelines/` se **copian** a `build/` en cada compilación — si cambiás el CSV (una nueva versión de tu raceline), tenés que volver a correr `colcon build --packages-select global_planner` para que `install/` sirva el archivo nuevo. No alcanza con pisar el de `src/`.

## 5. Verlo en RViz

Con el simulador abierto, antena conectada, modo Autonomous:

```bash
source install/setup.bash
ros2 launch global_planner raceline_view.launch.py \
  map:=$HOME/autodrive/f1tenth_ws/maps/<tu_mapa>.yaml \
  csv_path:=install/global_planner/share/global_planner/racelines/<tu_raceline>.csv
```

Deberías ver, todo junto y alineado: el mapa, el auto en su posición real (TF en vivo), y la raceline (línea coloreada) encima del mapa.

### Verificación sin RViz (por si algo no se ve)
```bash
ros2 topic echo /raceline --once        # nav_msgs/Path, no vacío, frame_id: map
ros2 topic list | grep raceline         # /raceline y /raceline_markers deben aparecer
```

## 6. Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| La raceline se ve corrida/rotada respecto al mapa | El CSV no se calculó con el mismo `resolution`/`origin` del `.yaml` del mapa que estás cargando | Regenerar el CSV apuntando tu planificador al `.yaml` correcto — no hay transformación que lo arregle acá |
| `/raceline` y `/raceline_markers` no aparecen en `ros2 topic list` | El nodo no arrancó — revisar la terminal por el `RuntimeError` de `csv_path` vacío, o que la ruta no exista | Confirmar el parámetro `csv_path` que le pasa el launch, y que el archivo exista en `install/.../racelines/` (paso 4) |
| El display `Map` (no la raceline) queda en `Warn` | Carrera de QoS ya conocida, ver `Tutorial_3_SLAM.md` | Sacar y volver a agregar el display `Map` en RViz |
| Cambié el CSV pero en RViz sigue la ruta vieja | Te olvidaste de recompilar (paso 4) o `raceline_publisher` sigue corriendo con el proceso viejo | `colcon build --packages-select global_planner` de nuevo, y relanzar |
| Nunca corriste `slam_toolbox` en esta sesión pero igual querés probar esto | No hace falta — este tutorial solo necesita el mapa **ya guardado** (`.pgm`/`.yaml`) y el simulador conectado (para la TF del auto), no `slam_toolbox` corriendo | — |

## Cierre

Con esto, la raceline de tu proyecto de planificación global queda **visible en RViz y disponible como tópico ROS 2** (`/raceline`), lista para que un controlador (Pure Pursuit, RPP, MPC — lo que hayas elegido para seguirla) se suscriba y maneje. Ese controlador es el siguiente eslabón, y es un nodo nuevo, independiente de todo lo de acá.

## Referencias
- `Tutorial_3_SLAM.md` — cómo se genera el mapa que tu planificador necesita como entrada.
- `SLAM_Comandos_Rapidos.md` / `Planificacion_Global_Comandos_Rapidos.md` — chuletas de comandos.
