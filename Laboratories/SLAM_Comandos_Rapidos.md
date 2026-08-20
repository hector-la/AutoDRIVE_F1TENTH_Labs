# SLAM — Comandos Rápidos (mapear, guardar, volver a cargar)

Chuleta operativa: solo comandos, en orden, sin explicación larga. Para el detalle de *por qué* cada parámetro/flag es así, ver `Tutorial_3_SLAM.md` y `CLAUDE.md`.

Bloque de preparación que se repite en cada terminal:
```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate
source /opt/ros/humble/setup.bash
source install/setup.bash
```

---

## Parte 1 — Mapear (4 terminales)

### Terminal 1 — Simulador
```bash
cd ~/autodrive/f1tenth_ws/simulator
./run_with_nvidia.sh
```
Click en el ícono de antena → **Connected**, verificar modo **Autonomous**.

### Terminal 2 — Bridge + RViz
```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash && source install/setup.bash
ros2 launch autodrive_f1tenth simulator_bringup_rviz.launch.py
```
**Antes de mapear**: en el panel de Displays de RViz, destildar/borrar el display **Camera** (`front_camera`) — si queda activo, satura el bridge y puede tirar abajo LiDAR/TF sin avisar (`CLAUDE.md` gotcha #9).

### Terminal 3 — SLAM Toolbox
```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash && source install/setup.bash
CFG=$(realpath ./src/config/mapper_params_online_async.yaml)
ros2 launch slam_toolbox online_async_launch.py slam_params_file:=$CFG use_sim_time:=true
```
- `use_sim_time:=true` es obligatorio aunque el bridge no publique `/clock` (gotcha #6) — con `false`, descarta todos los scans.
- Antes de lanzar: `ps aux | grep slam_toolbox` — no debe quedar una instancia vieja corriendo (gotcha #11, compiten por `/map`).

### Terminal 4 — Manejar (FTG autónomo)
```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash && source install/setup.bash
ros2 run controllers gap_node
```
- Velocidad lenta a propósito (mejor scan-matching). Parámetros ya tuneados para este circuito.
- Ctrl+C o `kill <pid>` (sin `-9`) frenan el auto de forma segura antes de matar el nodo.
- Dar **2-3 vueltas**, no cortar en la primera — el desfase que se ve al cerrar la vuelta es el loop closure de `slam_toolbox` corrigiendo drift acumulado; vueltas extra le dan más para afinar el cierre.

En RViz: `Fixed Frame` = `slam_map`, display `Map` sobre `/map` (opcional `LaserScan` sobre `/autodrive/f1tenth_1/lidar`).

---

## Parte 2 — Guardar el mapa

**No mates `slam_toolbox` todavía** — tiene que seguir publicando `/map`. Parar solo el `gap_node` (Terminal 4) está bien.

Terminal nuevo:
```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash && source install/setup.bash
mkdir -p maps
```

### 2.1 Mapa estático (`.pgm` + `.yaml`) — para localización futura
```bash
ros2 run nav2_map_server map_saver_cli -f maps/<nombre>
```
Esperar `Map saved successfully`. Los `WARN` de "Free/Occupied threshold unspecified" e "Image format unspecified" son solo avisos de que usó los valores por defecto — no son errores.

### 2.2 Pose-graph nativo — para retomar el mapeo después
```bash
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
  "{filename: '$HOME/autodrive/f1tenth_ws/maps/<nombre>_posegraph'}"
```
- **Ruta absoluta obligatoria** (a diferencia de `map_saver_cli`, que acepta relativa). `$HOME` la resuelve sola, no hace falta escribir `/home/tu_usuario/...` a mano.
- Respuesta `result=0` = éxito.
- Nombre único por sesión de mapeo — no reusar el de una vuelta anterior o lo pisa.

---

## Parte 3 — Cargar el mapa guardado de vuelta en RViz

No hace falta `slam_toolbox` corriendo para esto — solo el mapa ya guardado.

### 3.1 Levantar `map_server`
```bash
cd ~/autodrive/f1tenth_ws
source venv/bin/activate && source /opt/ros/humble/setup.bash && source install/setup.bash
ros2 run nav2_map_server map_server --ros-args -p yaml_filename:=$(pwd)/maps/<nombre>.yaml
```
Arranca inactivo (es un lifecycle node) — no publica nada todavía.

### 3.2 Activarlo (otro terminal)
```bash
ros2 lifecycle set /map_server configure
ros2 lifecycle set /map_server activate
```

### 3.3 Agregar el display en RViz
`Add` → `Map` → Topic = `/map` → `Fixed Frame` = `map`.

**Nota**: `map_server` publica con QoS `TRANSIENT_LOCAL` (latcheado, una sola vez al activar). Si el display de RViz ya estaba agregado *antes* de activar el nodo pero sigue sin mostrar nada, es porque su suscripción quedó en `VOLATILE` y se perdió ese único mensaje cacheado — no vuelve a llegar solo. Arreglo rápido, sin tocar RViz: forzar una publicación nueva con RViz ya suscrito:
```bash
ros2 lifecycle set /map_server deactivate
ros2 lifecycle set /map_server activate
```

### 3.4 Al terminar, apagarlo
`Ctrl+C` en la Terminal del paso 3.1. No dejarlo corriendo de fondo — un `map_server` huérfano de una sesión vieja es exactamente lo que puede pisar un `/map` futuro y hacer que un mapeo nuevo se vea desfasado.

---

## Resumen

```text
Mapear:   Simulador → Bridge+RViz (Camera OFF) → slam_toolbox (use_sim_time:=true) → gap_node → 2-3 vueltas
Guardar:  map_saver_cli (.pgm/.yaml) + serialize_map (posegraph, ruta absoluta)
Cargar:   map_server + lifecycle configure/activate → display Map en RViz (Fixed Frame=map) → apagar al terminar
```
