*This project has been created as part of the 42 curriculum by <your_login>.*

# Fly-in

A drone routing simulator. Given a network of zones and connections, it
moves a fleet of drones from a start zone to an end zone in the fewest
possible simulation turns, respecting zone types, zone capacities and
connection capacities.

## Description

The program reads a map file, validates it, builds a graph, plans a
conflict-free schedule for every drone, executes that schedule in a
simulation engine that checks every rule, and prints one line per turn:

```
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

Rules implemented:

- **Zone types:** `normal` (1 turn), `priority` (1 turn, preferred when
  paths tie), `restricted` (2 turns) and `blocked` (never entered).
- **Capacities:** `max_drones` per zone and `max_link_capacity` per
  connection. The start and end zones have no limit.
- **Simultaneous moves:** every turn is decided from the state at its
  beginning, and a space vacated in a turn can be used in that same turn.
- **Restricted zones:** a drone enters the connection in one turn and
  must arrive in the next one. It cannot wait on the connection, and the
  connection is freed in the turn the drone arrives.
- **Delivered drones:** drones that reach the end zone are no longer
  tracked.

## Instructions

Requirements: Python 3.10 or newer. The program itself only uses the
standard library. `flake8` and `mypy` are used for quality checks.

```
make install     # creates .venv and installs flake8 and mypy
make run         # runs the default map (maps/easy/01_linear_path.txt)
make run MAP=maps/hard/01_maze_nightmare.txt
make debug       # runs the program under pdb
make lint        # flake8 and mypy (see the Makefile for the flags)
make lint-strict # flake8 and mypy --strict
make clean       # removes __pycache__ and tool caches
```

Direct usage:

```
python3 fly_in.py <map_file> [--visual]
```

- Without options, it prints only the turn lines (the format required by
  the subject). The result summary goes to `stderr`.
- `--visual` also prints the map header and, after every turn, the state
  of the zones (see Visual representation).

Errors (invalid map, unreadable file, map without a path to the end
zone) are reported on `stderr` as `Error: ...` with a non-zero exit code.
Parsing errors include the line number and the cause.

### Map format

```
nb_drones: 5
start_hub: start 0 0 [color=green]
hub: junction 1 0 [zone=restricted color=orange max_drones=2]
end_hub: goal 3 0 [color=red]
connection: start-junction [max_link_capacity=2]
connection: junction-goal
```

- The first non-comment line must be `nb_drones: <positive integer>`.
- Exactly one `start_hub` and one `end_hub`; zone names are unique and
  contain no dashes or spaces; coordinates are integers.
- Metadata is optional: `zone` (`normal`, `blocked`, `restricted`,
  `priority`), `color`, `max_drones`; connections accept
  `max_link_capacity`.
- A connection links two zones defined **before** it, appears only once
  (`a-b` and `b-a` are the same) and cannot link a zone to itself.
- Lines starting with `#` and empty lines are ignored.
- A map with no path from start to end is valid input, but the program
  reports it and stops.

## Project structure

```
.
├── Makefile
├── .gitignore
├── .flake8
├── README.md
├── fly_in.py          # entry point
├── models.py          # data classes
├── parser.py          # map file parsing and validation
├── graph.py           # graph structure and reachability
├── engine.py          # turn-by-turn simulation and rule checking
├── path_finding.py    # reservations and scheduling
├── visualizer.py      # colored terminal output
├── maps/              # easy, medium, hard and challenger maps

```

### Files, classes and functions

**`models.py`**
- `ZoneType` (enum): `NORMAL`, `BLOCKED`, `RESTRICTED`, `PRIORITY`.
- `Zone`: name, coordinates, type, color, `max_drones`, start/end flags.
  `capacity_limit` (no limit for start and end) and `entry_cost`
  (2 for restricted zones, 1 otherwise).
- `Connection`: two zones and `max_link_capacity`. `other_zone(zone)`
  returns the opposite end.
- `Drone`: id, current zone, current connection, transit destination,
  remaining transit turns and route.

**`parser.py`**
- `ParseError`: error carrying the line number and the reason.
- `MapData`: parsed result (drones, zones, connections, start, end).
- `read_map_lines`: reads the file with a context manager, skipping
  comments and empty lines but keeping the original line numbers.
- `parse_int`, `parse_positive`, `split_line`, `parse_metadata`: small
  helpers for numbers, `prefix: body` lines and `[key=value ...]`.
- `parse_zone`, `parse_connection`: build `Zone` and `Connection`
  objects with every check required by the format.
- `parse_map`: orchestrates everything and checks duplicates, the single
  start and end, and zone references.

**`graph.py`**
- `Graph`: adjacency list plus a lookup of connections by zone pair.
- `get_connections(zone)`, `get_connections_zones(a, b)`,
  `get_neighbors(zone)` (blocked zones excluded).
- `path_destination()`: breadth-first search that tells whether the end
  zone is reachable from the start zone.

**`engine.py`**
- `SimulationError`: raised for any invalid move.
- `Departure`: a drone leaving a zone through a connection.
- `Simulation`: holds the state of every drone. `step(moves)` validates a
  whole turn (connections, blocked zones, zone and link capacity,
  drones in transit) before changing anything, applies it, and returns
  the movements of the turn already formatted. `is_finished()` tells when
  every drone is delivered.

**`path_finding.py`**
- `Reservations`: a calendar of how many drones use each zone at each
  instant and each connection at each turn.
- `Step`: one step of a route (arrival instant, zone, connection used).
- `Scheduler`: `find_route` searches the best route for one drone given
  the reservations; `plan` plans all drones one after another and returns
  the moves of every turn.

**`visualizer.py`**
- `Visualizer`: colors each movement with the color of its destination
  zone and prints the optional per-turn state (`--visual`).

**`fly_in.py`**
- `Application`: command line handling, error reporting and the main
  flow (parse, check path, plan, simulate, display).

## Algorithm

The scheduler plans in **space and time**. A state is a pair
`(zone, instant)`, and waiting is just another move, from
`(zone, t)` to `(zone, t + 1)`. Drones are planned one at a time. Each
drone runs a Dijkstra search over those states, taking the reservations
of the previous drones into account, and then writes its own use of
zones and connections into the calendar.

Details:

- A move to a normal or priority zone needs a free connection slot in
  the departure turn and a free place in the destination one turn later.
- A move to a restricted zone needs a free connection slot in the
  departure turn and a free place in the destination **two** turns later
  (the drone cannot wait on the connection).
- Among routes with the same arrival time, the search prefers the one
  that enters more `priority` zones.
- Blocked zones are never entered.
- The search is limited by a time horizon, so it always terminates.

The result is a schedule in which no rule can be broken. The engine then
executes it and checks every rule again independently.

**Complexity.** For one drone the search visits at most
`Z * T` states (`Z` zones, `T` the time horizon, bounded by
`4 * (Z + D)`), and each state looks at its connections, so it costs
about `O(Z * T * deg * log(Z * T))`. For `D` drones the total is `D`
times that. Memory is `O(Z * T)` for the search plus the reservation
calendar, which grows with the length of the routes of all drones.

**Limits.** Planning drones one at a time is a heuristic: it reaches the
optimum on every provided map, but it is not proven optimal for every
possible map.

## Visual representation

Colored terminal output (no graphical interface):

- Each movement is colored with the color of its destination zone.
  Colors are used only when the output goes to a terminal, so redirected
  output stays plain text.
- A drone crossing a connection towards a restricted zone is shown dimmed.
- With `--visual`, each turn is followed by a state line: drones waiting
  at the start, occupied zones (with their drones), drones in flight and
  how many drones are already delivered.

## Performance

Turns obtained on the provided maps (all equal to the optimum):

| Map | Drones | Turns |
|-----|--------|-------|
| easy / linear path | 2 | 4 |
| easy / simple fork | 4 | 4 |
| easy / basic capacity | 4 | 4 |
| medium / dead end trap | 5 | 8 |
| medium / circular loop | 6 | 10 |
| medium / priority puzzle | 5 | 6 |
| hard / maze nightmare | 8 | 13 |
| hard / capacity hell | 12 | 16 |
| hard / ultimate challenge | 15 | 26 |
| challenger / the impossible dream | 25 | 43 |

```
python3 -m unittest discover
```

## Resources

- Python documentation: `argparse`, `heapq`, `dataclasses`, `enum`.
- PEP 8 and PEP 257 (style and docstrings), flake8 and mypy documentation.
- E. W. Dijkstra, *A note on two problems in connexion with graphs*
  (1959).
- D. Silver, *Cooperative Pathfinding* (2005), for the idea of planning
  agents one at a time with a reservation table in space and time.

### AI usage

Describe here, honestly, how AI was used. Example: 
AI was used to discuss the architecture, explain concepts, propose the algorithm and review code and tests. The code was
typed, run and checked by the author, who is able to explain every part
of it.