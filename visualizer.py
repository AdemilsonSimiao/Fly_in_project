import sys
from engine import Simulation
from graph import Graph
from parser import MapData


class Visualizer:
    palette = {
        "black": "38;5;244",
        "blue": "38;5;33",
        "brown": "38;5;130",
        "crimson": "38;5;161",
        "cyan": "38;5;51",
        "darkred": "38;5;124",
        "gold": "38;5;220",
        "green": "38;5;40",
        "lime": "38;5;118",
        "magenta": "38;5;201",
        "maroon": "38;5;88",
        "orange": "38;5;208",
        "purple": "38;5;93",
        "red": "38;5;196",
        "violet": "38;5;177",
        "yellow": "38;5;226",
    }

    def __init__(self, graph: Graph, color: bool, detailed: bool) -> None:
        self.graph = graph
        self.color = color
        self.detailed = detailed

    def paint(self, text: str, color_name: str | None) -> str:
        if not self.color or color_name is None:
            return text
        code = self.palette.get(color_name, "1")
        return f"\033[{code}m{text}\033[0m"

    def dim(self, text: str) -> str:
        if not self.color:
            return text
        return f"\033[2m{text}\033[0m"

    def paint_move(self, move: str) -> str:
        target = move.partition("-")[2]
        zone = self.graph.zones.get(target)
        if zone is None:
            return self.dim(move)
        return self.paint(move, zone.color)

    def show_header(self, data: MapData) -> None:
        if not self.detailed:
            return
        start = self.paint(data.start.name, data.start.color)
        end = self.paint(data.end.name, data.end.color)
        print(
            f"Map: {data.nb_drones} drones, {len(data.zones)} zones, "
            f"{len(data.connections)} connections"
        )
        print(f"Route: {start} -> {end}")

    def show_turn(self, simulation: Simulation, moves: list[str]) -> None:
        line = " ".join(self.paint_move(move) for move in moves)
        if not self.detailed:
            print(line)
            return
        print(f"Turn {simulation.turn}: {line}")
        print(f"    {self.describe_state(simulation)}")

    def describe_state(self, simulation: Simulation) -> str:
        occupied: dict[str, list[int]] = {}
        flying: list[str] = []
        waiting = 0
        delivered = 0
        for drone in simulation.drones.values():
            zone = drone.current_zone
            if zone is None:
                target = drone.transit_destination
                name = "?" if target is None else target.name
                flying.append(f"D{drone.drone_id}->{name}")
            elif zone is self.graph.end:
                delivered += 1
            elif zone is self.graph.start:
                waiting += 1
            else:
                occupied.setdefault(zone.name, []).append(drone.drone_id)
        in_zones = [
            self.paint(
                f"{name}[{' '.join(f'D{i}' for i in ids)}]",
                self.graph.zones[name].color,
            )
            for name, ids in occupied.items()
        ]
        return (
            f"waiting: {waiting} | "
            f"in zones: {' '.join(in_zones) or '-'} | "
            f"in flight: {' '.join(flying) or '-'} | "
            f"delivered: {delivered}/{len(simulation.drones)}"
        )

    def show_summary(self, nb_drones: int, turns: int) -> None:
        print(
            f"{nb_drones} drones delivered in {turns} turns",
            file=sys.stderr,
        )
