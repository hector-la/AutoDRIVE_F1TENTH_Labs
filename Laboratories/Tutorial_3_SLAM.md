# Tutorial 3: SLAM (Mapeo 2D) del F1TENTH en AutoDRIVE

Adaptado de [Tutorial 3 de nabihandres/AUTODRIVE](https://github.com/nabihandres/AUTODRIVE/blob/main/Tutorial%203%3A%20Simultaneous%20Localization%20and%20Maping.md) a la estructura real de este workspace (`~/autodrive/f1tenth_ws`).

## Prerrequisitos

- `~/autodrive/f1tenth_ws` compilado y validado (simulador + bridge + teleop funcionando). Si no, seguir primero [AutoDRIVE_DevKit_Starter](https://github.com/hector-la/AutoDRIVE_DevKit_Starter).

Bloque de preparación de terminal que se repetirá varias veces:

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate
source /opt/ros/humble/setup.bash
source install/setup.bash
```

---

## 1. Instalar SLAM Toolbox

`slam_toolbox` es un paquete de sistema (vía `apt`), no va en el venv:

```bash
sudo apt update
sudo apt install ros-humble-slam-toolbox
```

Verificar instalación:

```bash
source /opt/ros/humble/setup.bash
ros2 pkg prefix slam_toolbox
ls $(ros2 pkg prefix slam_toolbox)/share/slam_toolbox/launch
```

### Modo usado en este tutorial

**Online asíncrono** (`online_async_launch.py`) — procesa el LiDAR en tiempo real mientras manejas el F1TENTH en el simulador, priorizando no acumular retraso sobre preservar cada scan. Es el modo recomendado para este caso de uso.

> Aunque sea asíncrono, conviene manejar despacio durante el mapeo — a alta velocidad se reduce el traslape entre scans y el mapa sale con paredes duplicadas/deformadas ("ghosting").

---

## 2. Configurar SLAM Toolbox

### 2.1 Crear carpeta de configuración

```bash
mkdir -p ~/autodrive/f1tenth_ws/src/config
```

### 2.2 Copiar la configuración estándar

```bash
source /opt/ros/humble/setup.bash
SLAM_SHARE=$(ros2 pkg prefix slam_toolbox)/share/slam_toolbox

cp "$SLAM_SHARE/config/mapper_params_online_async.yaml" \
   ~/autodrive/f1tenth_ws/src/config/mapper_params_online_async.yaml
```

### 2.3 Verificar el tópico real del LiDAR

Este paso necesita el simulador y el bridge ya corriendo — si todavía no los has levantado, adelanta las Terminales 1 y 2 de la sección 3 (más abajo) y vuelve aquí.

El tutorial original advierte que AutoDRIVE puede mostrar un tópico `/scan` sin publicador real. En este setup específico, comprobé por código que **`/scan` ni siquiera aparece** en la lista de tópicos — pero igual vale la pena que lo verifiques tú mismo:

```bash
ros2 topic list | grep -i scan
```

No debería aparecer nada. El tópico real es:

```bash
ros2 topic type /autodrive/f1tenth_1/lidar
```

Resultado esperado:

```text
sensor_msgs/msg/LaserScan
```

Inspecciona un mensaje (con el simulador conectado y en modo Autonomous):

```bash
ros2 topic echo /autodrive/f1tenth_1/lidar --once
```

Debe incluir:

```yaml
header:
  frame_id: lidar
```

Puedes también revisar el publicador con:

```bash
ros2 topic info /autodrive/f1tenth_1/lidar -v
```

Debe mostrar `Publisher count: 1`, con el nodo `autodrive_incoming_bridge`.

### 2.4 Verificar el árbol TF

Con el simulador y el bridge corriendo, genera el árbol TF:

```bash
ros2 run tf2_tools view_frames
```

(Si `tf2_tools` no está instalado: `sudo apt install ros-humble-tf2-tools`. Genera un archivo `frames.pdf` en el directorio actual.)

Los frames relevantes son:

- `map`: referencia global fija, publicada por AutoDRIVE.
- `f1tenth_1`: frame base (móvil) del vehículo.
- `lidar`: frame del sensor LiDAR.

No existe `base_footprint` en este árbol, y no hace falta — `slam_toolbox` puede usar cualquier frame base válido conectado por TF a la referencia odométrica y al LiDAR. Aquí usamos `f1tenth_1` como base frame (confirmado también por código: `broadcast_transform("f1tenth_1", "map", ...)` y `broadcast_transform("lidar", "f1tenth_1", ...)`).

### 2.5 Editar los parámetros ROS del archivo

```bash
nano ~/autodrive/f1tenth_ws/src/config/mapper_params_online_async.yaml
```

Configurar la sección `ros__parameters` así:

```yaml
slam_toolbox:
  ros__parameters:

    # ROS Parameters
    odom_frame: map
    map_frame: slam_map
    base_frame: f1tenth_1
    scan_topic: /autodrive/f1tenth_1/lidar
    use_map_saver: true
    mode: mapping # localization
```

| Parámetro | Por qué este valor |
|---|---|
| `odom_frame: map` | AutoDRIVE ya publica `map → f1tenth_1` directamente; ese `map` hace de referencia odométrica. |
| `map_frame: slam_map` | Nombre distinto al `map` de AutoDRIVE, para no chocar. Cadena TF resultante: `slam_map → map → f1tenth_1 → lidar`. |
| `base_frame: f1tenth_1` | En el TF tree de AutoDRIVE, sensores/ruedas/encoders cuelgan de `f1tenth_1` — cumple el rol de `base_link`. |
| `scan_topic: /autodrive/f1tenth_1/lidar` | Único tópico real de LiDAR en este setup (ver nota sobre `/scan` arriba). |
| `use_map_saver: true` | Habilita guardar el mapa como `.pgm` + `.yaml` compatibles con `map_server`. |
| `mode: mapping` | Construye y actualiza el mapa continuamente (vs. `localization`, que usa un mapa ya guardado). |

Guardar en `nano`: `Ctrl+O`, `Enter`, `Ctrl+X`.

---

## 3. Levantar todo en el orden correcto

El orden importa porque el LiDAR y el TF deben empezar a llegar antes de arrancar SLAM.

### Terminal 1 — Simulador

```bash
cd ~/autodrive/f1tenth_ws/simulator
./"AutoDRIVE Simulator.x86_64"
```

En el simulador: click en el ícono de antena hasta que diga **Connected**, verificar modo **Autonomous**.

> Si tu laptop tiene GPU NVIDIA con gráficos híbridos (Optimus/PRIME) y notás que el simulador va lento o corre por la integrada, puede hacer falta forzar la GPU dedicada (por ejemplo con `prime-run` o un wrapper equivalente con `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia`) — no es parte del setup estándar, depende de tu hardware.

### Terminal 2 — Bridge

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch autodrive_f1tenth simulator_bringup_rviz.launch.py
```

En el simulador: conectar la antena, verificar modo Autonomous. Este comando ya abre RViz — no hace falta lanzarlo de nuevo más adelante, lo vamos a configurar más abajo una vez que `slam_toolbox` esté publicando `/map`.

**Antes de seguir**, en el panel de Displays de RViz (izquierda): destildá o borrá el display **Camera** (sobre `front_camera`) si está activo. Esa sola suscripción hace que `autodrive_incoming_bridge` decodifique cada frame de cámara — el paso más caro de su callback — y se sature tanto que se cae de `ros2 node list` sin avisar, arrastrando LiDAR/TF con él.

### Esperar 3-5 segundos

Deja que el bridge empiece a publicar `/tf`, `/tf_static` y `/autodrive/f1tenth_1/lidar` antes de continuar.

> No reinicies Unity mientras `slam_toolbox` esté corriendo — puede generar warnings `TF_OLD_DATA`.

### Terminal 3 — SLAM Toolbox

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate
source /opt/ros/humble/setup.bash
source install/setup.bash

CFG=$(realpath ./src/config/mapper_params_online_async.yaml)

ros2 launch slam_toolbox online_async_launch.py \
  slam_params_file:=$CFG \
  use_sim_time:=true
```

**Nota:** `use_sim_time:=true` es obligatorio acá, aunque el bridge de AutoDRIVE no publique `/clock` — con `false`, `slam_toolbox` descarta todos los scans de LiDAR con el error `"the timestamp on the message is earlier than all the data in the transform cache"`. Antes de lanzar, confirma que no quede un `slam_toolbox` viejo corriendo de una sesión anterior (`ps aux | grep slam_toolbox`) — dos instancias vivas a la vez compiten por publicar `/map` y parece que "el mapa se congeló".

`slam_toolbox` tiene que estar arriba y sano **antes** de manejar — si arrancás a moverte antes, los primeros metros del circuito quedan sin mapear. Confirmá que levantó bien (`ros2 node list | grep slam`) antes de pasar a la Terminal 4.

### Terminal 4 — Manejar

Elegí una de las dos opciones:

**Opción A — Manejar vos mismo:**

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 run autodrive_f1tenth teleop_keyboard
```

Teleop por teclado que trae AutoDRIVE. Si ya lo usaste siguiendo el starter kit, es el mismo comando.

**Opción B — Mapear sin manos con `gap_node` (recomendado para este lab):**

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 run controllers gap_node
```

`gap_node` viene incluido en este repo (`src/controllers/controllers/gap_node.py`) — lo copiaste a tu workspace en el paso "Cómo usar este repo" del `README.md`. Implementa **Follow The Gap (FTG)**, un algoritmo de navegación reactiva: en cada scan del LiDAR busca el hueco libre más grande frente al auto y se dirige a su centro, sin necesitar un mapa ni un humano manejando. Ya viene tuneado para este circuito, con velocidad baja a propósito (mapear rápido genera drift y deforma el mapa). Para pararlo, Ctrl+C o `kill <pid>` (sin `-9`) — frena el auto de forma segura antes de matar el proceso, no queda girando/acelerando solo.

Usamos `gap_node` para armar este lab precisamente por esto: te deja mapear el circuito completo sin necesitar dos personas (una manejando, otra mirando la terminal) ni estar pendiente del teclado — arrancás el nodo y te concentrás en observar el mapa formarse en RViz.

### Configurar RViz

En la misma ventana de RViz que abrió la Terminal 2 (no hace falta abrir otra): configurá `Fixed Frame` = `slam_map`, agregá un display `Map` suscrito al tópico `/map`, y (opcional) `LaserScan` sobre `/autodrive/f1tenth_1/lidar` para ver el LiDAR en vivo mientras mapeas.

Con el auto manejando (Terminal 4), observá el mapa formarse en RViz.

**Da 2-3 vueltas completas antes de guardar, no cortes apenas cierra la primera.** Vas a notar que al completar la primera vuelta, justo donde el auto vuelve cerca del punto de partida, el mapa "salta" o se ve desfasado entre el inicio y el final — eso es normal, no un error. Es el **loop closure**: mientras das la vuelta, `slam_toolbox` va encadenando cada scan nuevo contra el anterior (scan matching local), y ese emparejamiento tiene un pequeño error cada vez que se va acumulando (drift). Cuando el auto vuelve a pasar cerca de una zona ya mapeada, `slam_toolbox` la reconoce y corre una optimización global de todo el grafo de poses que "engancha" el final con el inicio — ese salto que ves es esa corrección funcionando, no rompiéndose. Necesita juntar varios scans en la zona de cierre antes de confiar en el match, así que **no pares justo ahí** — un par de vueltas extra le dan más para afinar el cierre y el desfase final queda mucho menor.

---

## 4. Guardar el mapa

Guarda dos cosas distintas, con roles distintos — vale la pena guardar ambas:

| Qué | Formato | Para qué sirve |
|---|---|---|
| Mapa estático | `.pgm` (imagen) + `.yaml` (metadata) | Formato estándar de ROS/Nav2. Sirve para **localización** sobre un mapa ya terminado (por ejemplo con AMCL), o simplemente para visualizarlo después. Es una foto final, no se puede "continuar mapeando" a partir de él. |
| Pose-graph | `.data` + `.posegraph` | Formato nativo de `slam_toolbox` — el grafo completo de poses y scans que usó para construir el mapa. Sirve para **retomar el mapeo** más adelante sin perder todo el trabajo de scan matching ya hecho. |

**No mates `slam_toolbox` para guardar** — tiene que seguir corriendo y publicando `/map`. Podés parar el nodo que estaba manejando (Terminal 4, `teleop_keyboard` o `gap_node`) sin problema.

### 4.1 Crear carpeta de mapas

```bash
mkdir -p ~/autodrive/f1tenth_ws/maps
```

### 4.2 Guardar el mapa estático (`.pgm` + `.yaml`)

Abre un quinto terminal:

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 run nav2_map_server map_saver_cli -f maps/F1tenth_Map
```

Este comando se suscribe al tópico `/map` (el que publica `slam_toolbox` en vivo) y guarda lo que reciba. Espera a ver:

```text
[INFO] [map_saver]: Map saved successfully
```

Vas a ver también un par de `WARN` sobre "Free/Occupied threshold unspecified" e "Image format unspecified" — son solo avisos de que usó los valores por defecto de ROS (que están bien para este caso), no errores.

Deben generarse:

```text
maps/F1tenth_Map.pgm
maps/F1tenth_Map.yaml
```

### 4.3 Guardar el pose-graph nativo

Mismo terminal:

```bash
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
  "{filename: '$HOME/autodrive/f1tenth_ws/maps/F1tenth_Map_posegraph'}"
```

⚠️ Este servicio necesita **ruta absoluta** — a diferencia de `map_saver_cli`, que arriba aceptó una ruta relativa (`maps/...`), acá hace falta la ruta completa. `$HOME` la arma sola con tu usuario (no hace falta escribir `/home/tu_usuario/...` a mano). La respuesta esperada:

```text
response:
slam_toolbox.srv.SerializePoseGraph_Response(result=0)
```

`result=0` significa éxito (no es un código de error).

Verificar que los cuatro archivos existan:

```bash
ls -lh ~/autodrive/f1tenth_ws/maps
```

---

## 5. Volver a cargar el mapa guardado en RViz

Esto sirve para revisar un mapa ya guardado sin tener que mapear de nuevo — por ejemplo, para mostrárselo a alguien o confirmar que quedó bien. **No hace falta `slam_toolbox` corriendo para esto**, solo el archivo `.pgm`/`.yaml` ya guardado.

### 5.1 Levantar el nodo `map_server`

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 run nav2_map_server map_server --ros-args -p yaml_filename:=$(pwd)/maps/F1tenth_Map.yaml
```

`map_server` es un **lifecycle node**: un tipo de nodo de ROS 2 que arranca en un estado "sin configurar" y no hace nada hasta que alguien lo lleva explícitamente por sus estados (`configure` → `activate`). Esto es deliberado en Nav2 — evita que un nodo empiece a publicar datos a medio inicializar. Vas a ver que el comando de arriba se queda esperando, sin publicar nada todavía — es normal.

### 5.2 Activarlo

En otro terminal (mismo `source` de siempre):

```bash
ros2 lifecycle set /map_server configure
ros2 lifecycle set /map_server activate
```

Recién después de `activate`, el nodo lee el `.pgm`/`.yaml` y empieza a publicar `/map`.

### 5.3 Agregar el display en RViz

Si RViz ya está abierto: panel izquierdo, botón **Add** → pestaña "By display type" → `Map` → OK. En sus propiedades, **Topic** = `/map`. Y en **Global Options → Fixed Frame**, poné `map` (el frame con el que `map_server` publica por defecto).

**Nota si no aparece nada:** `map_server` publica `/map` con QoS `TRANSIENT_LOCAL` — un mensaje "latcheado" que se manda una sola vez al activar, y queda en caché para quien se suscriba después. Si tu display de RViz ya estaba agregado *antes* de correr `activate` en el paso 5.2, a veces su suscripción queda con QoS `VOLATILE`, que en DDS **no recibe ese histórico cacheado** — solo mensajes publicados a partir de que se suscribió. Se ve como si el mapa nunca cargara. Arreglo rápido, sin tocar nada de RViz — forzar una publicación nueva con RViz ya suscrito:

```bash
ros2 lifecycle set /map_server deactivate
ros2 lifecycle set /map_server activate
```

### 5.4 Apagarlo al terminar

`Ctrl+C` en el terminal del paso 5.1. **No lo dejes corriendo de fondo** — un `map_server` (o cualquier nodo de localización de Nav2) huérfano de una sesión vieja puede competir por publicar `/map` con un `slam_toolbox` de una sesión de mapeo futura y hacer que el mapa se vea desfasado, aunque el mapeo en sí esté sano. Antes de arrancar una sesión de mapeo nueva, conviene chequear `ps aux | grep -E "map_server|lifecycle_manager"` y confirmar que no quedó nada de una vez anterior.

---

## 6. Ver el mapa automáticamente cada vez que abrís RViz (opcional)

La sección 5 sirve para revisar el mapa una vez, a mano. Si en cambio querés tenerlo **de fondo mientras manejás o probás cosas** (sin mapear de nuevo), conviene armar un launch file propio que levante bridge + RViz + el mapa ya activado, todo en un solo comando — en vez de escribir 5 comandos en 3 terminales cada vez.

⚠️ **No uses esto al mismo tiempo que `slam_toolbox` mapeando** — dos nodos publicando `/map` a la vez compiten entre sí y el mapa termina viéndose desfasado, aunque cada uno por separado esté sano. Es para manejar/probar viendo el mapa ya hecho, no para mapear de nuevo.

### 6.1 Crear la carpeta de launch files

```bash
mkdir -p ~/autodrive/f1tenth_ws/src/controllers/launch
```

### 6.2 Crear el launch file

```bash
nano ~/autodrive/f1tenth_ws/src/controllers/launch/bridge_with_map.launch.py
```

```python
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
```

`autostart: True` en el `lifecycle_manager` reemplaza los `ros2 lifecycle set ... configure/activate` manuales de la sección 5 — los dispara solo. El `TimerAction` de 5 segundos es la parte importante: sin él, todo arranca al mismo tiempo y hay una carrera — a veces RViz no llega a suscribirse antes de que `map_server` publique su único mensaje, y el mapa nunca aparece (avisa "No map received" en el display, sin ningún error de código de por medio). Retrasando `map_server`, RViz siempre gana esa carrera.

### 6.3 Registrar el launch file en `setup.py`

```bash
nano ~/autodrive/f1tenth_ws/src/controllers/setup.py
```

Agregar `import os` y `from glob import glob` arriba, y una línea nueva en `data_files`:

```python
import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'controllers'

setup(
    ...
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),   # ← nueva
    ],
    ...
)
```

### 6.4 Compilar

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### 6.5 Correrlo

Con el simulador ya abierto y conectado (Terminal 1, como siempre):

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash && source install/setup.bash
ros2 launch controllers bridge_with_map.launch.py map:=$(pwd)/maps/F1tenth_Map.yaml
```

Un solo comando levanta bridge + RViz + el mapa (con el delay de 5 segundos, así que no te alarmes si tarda un toque en aparecer).

### 6.6 Agregar el display una vez y guardarlo para no repetirlo

En RViz: `Add` → `Map` → Topic `/map` (el `Fixed Frame` va a ser `map`, el mismo que usa AutoDRIVE — el mapa queda alineado con el auto en vivo). Después, `File → Save Config As...` sobre el mismo archivo que usa el launch (`~/autodrive/f1tenth_ws/src/autodrive_ros2/autodrive_f1tenth/rviz/simulator.rviz`), para que la próxima vez ya abra con el display puesto.

**De acá en adelante, para abrir RViz con el mapa ya cargado de fondo, usá este comando** (Terminal 2, en vez de `simulator_bringup_rviz.launch.py`):

```bash
ros2 launch controllers bridge_with_map.launch.py map:=$(pwd)/maps/F1tenth_Map.yaml
```

Para una sesión de **mapeo nuevo** (con `slam_toolbox`), seguí usando `simulator_bringup_rviz.launch.py` como en la sección 3 — no mezcles los dos.

---

## Resumen del orden de arranque

```text
1. Simulador AutoDRIVE (~/autodrive/f1tenth_ws/simulator)
2. Bridge ROS 2 con RViz incluido (Camera display OFF)
3. Esperar 3-5 segundos
4. SLAM Toolbox con use_sim_time:=true — confirmar que levantó antes de seguir
5. Manejar: teleop_keyboard o gap_node (recomendado, mapea sin manos)
6. Configurar RViz (Fixed Frame=slam_map, display Map) y observar, 2-3 vueltas completas
7. Guardar el mapa (mapa .pgm/.yaml + pose-graph)
8. (Opcional) Volver a cargarlo en RViz con map_server
9. (Opcional, una sola vez) Armar bridge_with_map.launch.py — de ahí en más, para abrir RViz con el mapa ya cargado de fondo (sin mapear de nuevo), el comando es:
   ros2 launch controllers bridge_with_map.launch.py map:=<ruta al .yaml>
```

Versión solo-comandos, sin explicación, para consulta rápida: `Laboratories/SLAM_Comandos_Rapidos.md`.

## Troubleshooting: `slam_map` no aparece en Fixed Frame

Checklist en orden, de más simple a más específico:

| # | Comando | Qué confirma |
|---|---|---|
| 1 | `ros2 node list \| grep slam` y `ps aux \| grep slam_toolbox` | `slam_toolbox` está corriendo de verdad. Revisar **ambos** — un nodo puede seguir apareciendo en `ros2 node list` por un rato aunque el proceso ya haya muerto, y al revés, `kill` a veces no mata el proceso a la primera (revisar con `ps`). |
| 2 | `ros2 topic hz /autodrive/f1tenth_1/lidar` | El LiDAR llega a una tasa razonable (varios Hz). Si sale muy bajo (ej. ~0.5 Hz) o no sale nada, `slam_toolbox` no va a poder procesarlo a tiempo — no tiene caso seguir revisando los pasos de abajo hasta resolver esto. |
| 3 | `ros2 topic echo /rosout` (dejar corriendo unos segundos) | Si ves repetido `Message Filter dropping message... earlier than all the data in the transform cache`, es la señal exacta de que el TF llega demasiado tarde — el mapa nunca se va a formar aunque todo lo demás esté bien. |
| 4 | `ros2 run tf2_ros tf2_echo map slam_map` | Si `slam_toolbox` está calculando el mapa, esto imprime la transformación constantemente. Si se queda esperando ("waiting for transform"), no está publicando nada. |
| 5 | `ros2 topic hz /map` | Confirma que el tópico del mapa en sí se está actualizando. |
| 6 | En RViz, abrir el dropdown de **Fixed Frame** | Solo lista frames que RViz ya vio pasar por TF al menos una vez — si `slam_map` no aparece ahí, es porque nunca llegó, no que RViz lo esté ocultando. |

**Tip:** si el paso 3 muestra el error de "timestamp earlier than transform cache" de forma **persistente y sin excepción** (no ocasional), sospechá primero de `use_sim_time:=false` antes que de la velocidad del simulador — un simulador lento genera drops *intermitentes*, no un descarte total y permanente.

## Referencias

- [Tutorial original (nabihandres/AUTODRIVE)](https://github.com/nabihandres/AUTODRIVE/blob/main/Tutorial%203%3A%20Simultaneous%20Localization%20and%20Maping.md)
- [Documentación SLAM Toolbox (ROS 2 Humble)](https://docs.ros.org/en/humble/p/slam_toolbox/)
- [Repositorio oficial SLAM Toolbox](https://github.com/SteveMacenski/slam_toolbox)
