# Teoría y Conceptos — AutoDRIVE F1TENTH

Documento vivo: acá se va agregando teoría de ROS 2 / navegación autónoma a medida que la vamos necesitando, explicada en el contexto real de este proyecto (no genérico). Pensado para que cualquiera del equipo (o quien llegue después) pueda entender el *por qué*, no solo copiar comandos.

---

## 1. ¿Qué es un tópico (`topic`) en ROS 2?

Un tópico es un canal de comunicación con nombre por donde los nodos se pasan mensajes, sin conocerse entre sí directamente:

- Un nodo **publica** (`Publisher`) mensajes de un tipo específico en un tópico.
- Otro(s) nodo(s) se **suscriben** (`Subscriber`) a ese mismo tópico para recibirlos.
- La comunicación es asíncrona y de muchos-a-muchos: puede haber varios publicadores y varios suscriptores en el mismo tópico.

En este proyecto, el nodo `autodrive_incoming_bridge` (parte del devkit) recibe datos del simulador Unity por WebSocket y los **publica** como tópicos ROS. El nodo `autodrive_outgoing_bridge` hace lo inverso: se **suscribe** a los tópicos de comando (`*_command`) y se los reenvía al simulador.

## 2. Tópicos del F1TENTH — confirmados en vivo (`/autodrive/f1tenth_1/...`)

> Estos son los tópicos reales de **este** setup, verificados con `ros2 topic list`/`ros2 topic info` mientras el simulador y el bridge corrían. Son específicos del vehículo `f1tenth_1` (un solo auto). Si en algún momento se prueba un escenario con dos vehículos, deberían aparecer los mismos duplicados como `f1tenth_2`, pero eso no se ha probado todavía. El paquete `autodrive_nigel` (otro robot de AutoDRIVE) también compila en este workspace pero no lo usamos — sus tópicos serían distintos.

| Tópico | Tipo | Qué es, en corto |
|---|---|---|
| `/autodrive/f1tenth_1/throttle_command` | `Float32` | Lo que **tú envías** al simulador para acelerar/frenar. Rango `[-1, 1]`: negativo reversa, positivo adelante. |
| `/autodrive/f1tenth_1/steering_command` | `Float32` | Lo que **tú envías** para girar el volante. Rango `[-1, 1]`: no son radianes, es una fracción del giro máximo. |
| `/autodrive/f1tenth_1/throttle` | `Float32` | El acelerador que el simulador dice que **realmente** está aplicando en ese instante (puede diferir del comando por física/límites). |
| `/autodrive/f1tenth_1/steering` | `Float32` | El ángulo de dirección real actual, mismo criterio que `throttle` vs `throttle_command`. |
| `/autodrive/f1tenth_1/left_encoder` / `right_encoder` | `JointState` | Lectura de los encoders de las ruedas (velocidad angular/posición) — de aquí se puede derivar velocidad real del auto y odometría. |
| `/autodrive/f1tenth_1/ips` | `Point` | *Indoor Positioning System* — la posición (x, y, z) del auto "de verdad", como si fuera un GPS interior perfecto del simulador. Útil como referencia/ground truth, no algo que tendrías en un auto real. |
| `/autodrive/f1tenth_1/imu` | `Imu` | Acelerómetro + giroscopio: aceleración lineal y velocidad angular del chasis. |
| `/autodrive/f1tenth_1/lidar` | `LaserScan` | El escaneo láser 2D — un arreglo de distancias a distintos ángulos alrededor del auto. Es el sensor principal para evitar obstáculos, SLAM, Follow-the-Gap, etc. |
| `/autodrive/f1tenth_1/front_camera` | `Image` | Imagen RGB de la cámara frontal. |

**Comandos vs. feedback:** los que terminan en `_command` son de **entrada** (tú decides el valor y lo publicas); los que no, son de **salida/telemetría** (el simulador te informa el estado real). Es el mismo patrón en `throttle`/`throttle_command` y `steering`/`steering_command`.

---

## 3. ¿Qué es TF (`tf2`) y por qué importa?

Un robot tiene varias partes — el chasis, el LiDAR, la cámara, cada rueda — y cada una "ve" el mundo desde su propio punto de referencia. TF (*transform*) es el sistema de ROS 2 que mantiene, en todo momento, **dónde está cada parte respecto a las demás**, para poder convertir mediciones de un punto de vista a otro.

Conceptos clave:

- **Frame (marco de referencia):** un sistema de coordenadas con nombre (ej. `lidar`, `f1tenth_1`, `map`). Cada mensaje de sensor viene "anclado" a un frame (`header.frame_id`) — un punto del LiDAR está expresado en coordenadas *relativas al sensor*, no del mundo.
- **Transform:** la traslación + rotación que convierte coordenadas de un frame a otro. Ej.: "el LiDAR está 27.3 cm adelante y 9.6 cm arriba del centro del auto, sin rotación" es el transform `f1tenth_1 → lidar`.
- **Árbol TF:** todos los frames de un robot forman un árbol (no un grafo cualquiera): cada frame tiene **un solo padre**, pero puede tener varios hijos. ROS puede componer la cadena de transforms entre dos frames cualesquiera del árbol para pasar de uno a otro, aunque no estén directamente conectados.

### La cadena en este proyecto: `map → f1tenth_1 → lidar`

Concretamente, en `autodrive_incoming_bridge.py` (el nodo que arma el árbol TF acá), cada frame se define así:

```
map                                        # raíz: el mundo, fijo, no se mueve
 └── f1tenth_1                             # el auto — SU transform respecto a "map" cambia en cada mensaje (se mueve)
      ├── lidar          [+0.273, 0, +0.096]   # fijo respecto al auto — el sensor no se mueve solo
      ├── imu             [+0.08, 0, +0.055]
      ├── ips              [+0.08, 0, +0.055]
      ├── front_camera    [-0.015, 0, +0.15]
      ├── left_encoder / right_encoder
      └── front_left_wheel / front_right_wheel / rear_left_wheel / rear_right_wheel
```

- **`map`** es la raíz del árbol: el marco de referencia global y fijo del mundo del simulador. No tiene padre.
- **`f1tenth_1`** es el frame del chasis del auto. Su posición/orientación respecto a `map` **cambia constantemente** — es literalmente "dónde está el auto en el mundo ahora mismo". Definido en el eje trasero del vehículo.
- **`lidar`**, `imu`, `ips`, `front_camera`, los encoders y las 4 ruedas cuelgan de `f1tenth_1` con un offset **fijo** (están atornillados al chasis, no se mueven entre sí) — solo las ruedas tienen además una rotación que cambia con el volante/el giro de la llanta.

**¿Para qué sirve esto en la práctica?** Un punto del LiDAR llega en coordenadas relativas al sensor (frame `lidar`). Si quieres saber en qué punto exacto del *mundo* (`map`) está un obstáculo — para construir un mapa, evitar una pared, planear una ruta — necesitas componer la cadena `lidar → f1tenth_1 → map`. Eso es exactamente lo que hace posible el SLAM (`Tutorial_3_SLAM.md`): sin un árbol TF consistente, `slam_toolbox` no podría ubicar cada escaneo del LiDAR en el mapa global que está construyendo.

---

## 4. Glosario rápido

| Término | Significado breve |
|---|---|
| **Nodo** | Un proceso ROS 2 independiente (ej. `autodrive_incoming_bridge`, `teleop_keyboard`). |
| **Mensaje** | La estructura de datos que viaja por un tópico (ej. `LaserScan`, `Float32`). |
| **`frame_id`** | El nombre del frame TF al que está anclado un mensaje — dice "desde dónde" se midió. |
| **Quaternion** | Forma de representar una rotación 3D con 4 números (x, y, z, w), evita las ambigüedades de los ángulos de Euler. Aparece en las orientaciones de los transforms TF. |
| **`LaserScan`** | Tipo de mensaje del LiDAR 2D: un arreglo `ranges[]` (distancias) más `angle_min`, `angle_max`, `angle_increment` para saber a qué ángulo corresponde cada distancia. |
| **`use_sim_time`** | Le dice a un nodo si debe usar el reloj `/clock` de una simulación en vez de la hora real del sistema. El bridge de este proyecto **nunca** publica `/clock` — eso no cambia. Pero `slam_toolbox` sí necesita `use_sim_time:=true` para funcionar aquí (confirmado 19/08/2026): con `false` descarta todos los scans de LiDAR por siempre, aunque no haya ningún `/clock` real detrás. El motivo exacto no está del todo claro (parece ser cómo `slam_toolbox` maneja internamente sus timeouts, no que reciba tiempo de simulación de verdad), pero el resultado es reproducible. Ver `CLAUDE.md`, gotcha #6. |
| **Occupancy grid (mapa de ocupación)** | La representación de un mapa como una grilla de celdas, cada una marcada libre/ocupada/desconocida — lo que produce SLAM al final. |

---

_(Se irá ampliando con cada laboratorio nuevo.)_
