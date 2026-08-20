# Laboratories

Guías paso a paso para trabajar con el F1TENTH en AutoDRIVE, pensadas para leerse en orden si es tu primera vez. Cada tema tiene **dos documentos**: un **Tutorial** (explica el *por qué* de cada paso, con teoría y troubleshooting) y una chuleta de **Comandos Rápidos** (solo los comandos, en orden, sin explicación — para cuando ya entendiste el tema y solo querés ejecutar).

## Antes de empezar

Si es la primera vez que tocás este workspace, el `README.md` de la raíz del repo explica cómo instalar/compilar todo desde cero. Estos documentos asumen que ya tenés `~/autodrive/f1tenth_ws` compilado y el simulador funcionando (bridge conectado, `teleop_keyboard` moviendo el auto).

## 0. Teoría y Conceptos

📄 [`00_Teoria_y_Conceptos.md`](00_Teoria_y_Conceptos.md)

Antes de tocar código, conviene entender dos ideas de ROS 2 que van a aparecer todo el tiempo:

- **Tópicos** (`topic`): cómo se comunican los nodos entre sí (quién publica, quién se suscribe), aplicado a los tópicos reales de este F1TENTH (`/autodrive/f1tenth_1/lidar`, `/throttle_command`, etc.).
- **TF (`tf2`)**: cómo sabe ROS dónde está cada cosa (el auto, el LiDAR, el mapa) unas respecto de otras, y por qué la cadena `map → f1tenth_1 → lidar` es la base de todo lo que viene después (SLAM, planificación, control).

Si ya conocés ROS 2, podés saltarte este documento y volver cuando algo no te cierre.

## 3. SLAM — Construir el mapa

📄 [`Tutorial_3_SLAM.md`](Tutorial_3_SLAM.md) · 📄 [`SLAM_Comandos_Rapidos.md`](SLAM_Comandos_Rapidos.md)

**Qué resuelve:** el auto no tiene un mapa del circuito de entrada — hay que construirlo manejando por la pista mientras `slam_toolbox` arma un mapa 2D en tiempo real (occupancy grid), combinando el LiDAR con la posición del auto para ir "dibujando" las paredes.

**Qué te lleva de la mano el tutorial:** instalar y configurar `slam_toolbox` para este simulador en particular (algunos parámetros son distintos a los de un tutorial genérico de ROS, porque AutoDRIVE tiene sus propias particularidades — no publica `/clock`, no existe el tópico `/scan`, etc., todo explicado ahí), manejar el circuito completo (a mano o con el controlador `gap_node`, que lo hace solo), guardar el resultado en dos formatos (`.pgm`/`.yaml` para navegación, el pose-graph nativo de `slam_toolbox` por si querés retomar el mapeo después), y volver a cargar ese mapa guardado en RViz en cualquier momento sin tener que mapear de nuevo.

**Con qué te vas:** un mapa `.pgm`/`.yaml` del circuito, guardado en `maps/`, que es el insumo que necesita todo lo que sigue.

## 4. Planificación Global — Traer una raceline a AutoDRIVE

📄 [`Tutorial_4_Planificacion_Global.md`](Tutorial_4_Planificacion_Global.md) · 📄 [`Planificacion_Global_Comandos_Rapidos.md`](Planificacion_Global_Comandos_Rapidos.md)

**Qué resuelve:** ya tenés el mapa (paso anterior). El siguiente problema es decidir **por dónde debería andar el auto** — una trayectoria (raceline) que recorra el circuito, calculada de antemano sobre ese mapa. Ese cálculo (qué algoritmo de planificación usar, cómo suavizar la ruta resultante) **no es parte de este tutorial** — es tu propio trabajo, en un proyecto aparte, con el algoritmo que te hayan asignado o que elijas (Dijkstra, A*, RRT, con suavizado Cubic-Spline, B-Spline, Fem-pos, lo que sea). Este tutorial arranca **después** de eso: una vez que tenés esa ruta calculada y guardada como una lista de waypoints (un archivo CSV), te explica cómo traerla a AutoDRIVE para verla en RViz, alineada con el mapa y el auto, y disponible como un tópico de ROS 2 para que un controlador la pueda seguir más adelante.

**Qué te lleva de la mano el tutorial:** qué formato tiene que tener ese CSV para que todo funcione sin cambios, cómo armar el paquete de ROS 2 que lo lee y lo publica (con el código completo, listo para copiar), y cómo verificar que quedó bien alineado con el mapa.

**Con qué te vas:** la raceline visible en RViz y publicada en el tópico `/raceline`, lista para conectarle un controlador (Pure Pursuit, RPP, MPC, el que corresponda) en un próximo paso — que ya no es parte de este tutorial tampoco.

## Cómo se relacionan estas guías entre sí

```text
Tutorial 3 (SLAM)                Tutorial 4 (Planificación Global)
┌─────────────────────┐          ┌──────────────────────────────────┐
│ manejar el circuito  │  mapa    │ tu algoritmo de planificación     │
│ con slam_toolbox     │ ───────▶ │ (proyecto aparte, no está acá)    │
│                      │ .pgm/.yaml│ ───────▶ raceline (CSV) ───────▶ │
└─────────────────────┘          │ traer el CSV a AutoDRIVE (RViz +  │
                                  │ tópico /raceline)                 │
                                  └──────────────────────────────────┘
                                                    │
                                                    ▼
                                     (siguiente paso, no cubierto acá:
                                      un controlador que siga /raceline)
```

Cada tutorial produce lo que el siguiente necesita como entrada — pero cada uno es un paquete de ROS 2 independiente, así que podés detenerte en cualquier punto de la cadena y ya tenés algo funcional y verificable en RViz.
