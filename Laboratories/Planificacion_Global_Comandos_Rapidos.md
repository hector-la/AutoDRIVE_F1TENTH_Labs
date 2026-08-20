# Planificación Global (raceline) — Comandos Rápidos

Chuleta operativa: solo comandos, en orden, sin explicación larga. Para el detalle de *por qué* cada pieza es así, ver `Tutorial_4_Planificacion_Global.md`.

Bloque de preparación que se repite en cada terminal:
```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate
source /opt/ros/humble/setup.bash
source install/setup.bash
```

---

## Parte 0 — Llevar el mapa a tu proyecto de planificación

```bash
cp ~/autodrive/f1tenth_ws/maps/<tu_mapa>.pgm ~/autodrive/f1tenth_ws/maps/<tu_mapa>.yaml \
   <carpeta de mapas de tu proyecto de planificación>
```
Ahí corrés tu algoritmo (Dijkstra/A*/RRT/...) + suavizado (Cubic-Spline/B-Spline/Fem-pos/...) — eso es tu propio código, fuera de este repo. Lo único que necesitás traer de vuelta cuando termine es el **CSV final** (`x,y,heading,kappa,v`, ver el contrato en `Tutorial_4_Planificacion_Global.md`); cualquier archivo intermedio que tu proyecto genere en el camino (PNGs, CSV crudo, etc.) se queda del otro lado, no hace falta traerlo.

---

## Parte 1 — Crear el paquete (una sola vez)

```bash
cd ~/autodrive/f1tenth_ws/src
mkdir -p global_planner/global_planner global_planner/launch global_planner/racelines global_planner/resource
touch global_planner/global_planner/__init__.py
touch global_planner/resource/global_planner
```
Copiar `package.xml`, `setup.py`, `setup.cfg`, `global_planner/raceline_publisher.py` y `launch/raceline_view.launch.py` del `Tutorial_4_Planificacion_Global.md` (secciones 1-3).

---

## Parte 2 — Traer un CSV nuevo (cada vez que cambia tu raceline)

```bash
cp <ruta a tu CSV> ~/autodrive/f1tenth_ws/src/global_planner/racelines/<nombre>.csv

cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select global_planner
```
**Recompilar es obligatorio** aunque uses `--symlink-install` — los CSV de `racelines/` se copian a `build/`, no se symlinkean.

Verificar que el archivo instalado es el nuevo:
```bash
diff ~/autodrive/f1tenth_ws/src/global_planner/racelines/<nombre>.csv \
     ~/autodrive/f1tenth_ws/install/global_planner/share/global_planner/racelines/<nombre>.csv
# sin salida = son iguales, ok
```

---

## Parte 3 — Verla en RViz (simulador ya abierto, antena conectada, modo Autonomous)

```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash && source install/setup.bash

ros2 launch global_planner raceline_view.launch.py \
  map:=$HOME/autodrive/f1tenth_ws/maps/<mapa>.yaml \
  csv_path:=install/global_planner/share/global_planner/racelines/<nombre>.csv
```
Si `map:=`/`csv_path:=` coinciden con los `default_value` del launch, se pueden omitir.

En RViz deberías ver: mapa + auto en su posición real + línea de la raceline, todo alineado.

---

## Parte 4 — Verificación sin abrir RViz

```bash
ros2 node list | grep raceline_publisher
ros2 topic list | grep raceline                 # /raceline y /raceline_markers
ros2 topic echo /raceline --once                 # nav_msgs/Path, frame_id: map, no vacío
```

---

## Parte 5 — Probar con dos mapas/racelines distintos (comparar)

```bash
# copiar con nombre distinto en vez de pisar el default
cp <csv_nuevo> ~/autodrive/f1tenth_ws/src/global_planner/racelines/<nombre_b>.csv
colcon build --symlink-install --packages-select global_planner

ros2 launch global_planner raceline_view.launch.py \
  map:=$HOME/autodrive/f1tenth_ws/maps/<mapa_b>.yaml \
  csv_path:=install/global_planner/share/global_planner/racelines/<nombre_b>.csv
```

---

## Apagar

`Ctrl+C` en la terminal del `ros2 launch` (mata bridge + RViz + `map_server` + `raceline_publisher` juntos). Verificar que no quedó nada colgado:
```bash
ps aux | grep -E "autodrive_incoming_bridge|rviz2|raceline_publisher|map_server" | grep -v grep
```
Si algo sigue vivo: `kill -9 <pid>` (ver gotcha #10 del `CLAUDE.md` — `eventlet`/`gevent` ignoran `kill` normal).

---

## Resumen

```text
Llevar el mapa:         cp .pgm/.yaml a tu proyecto de planificación → correr tu algoritmo + suavizado ahí
Crear paquete (1 vez):  mkdir + package.xml/setup.py/setup.cfg + raceline_publisher.py + launch
Traer CSV nuevo:        cp a racelines/ → colcon build --packages-select global_planner (SIEMPRE)
Ver en RViz:            ros2 launch global_planner raceline_view.launch.py map:=... csv_path:=...
Verificar sin RViz:     ros2 topic echo /raceline --once
```
