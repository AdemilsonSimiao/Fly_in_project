import sys
import time

from engine import Simulation
from graph import Graph
from models import Connection, Zone, ZoneType
from visualizer import Visualizer


class Animator:
    symbols = {
        ZoneType.NORMAL: "o",
        ZoneType.PRIORITY: "*",
        ZoneType.RESTRICTED: "~",
        ZoneType.BLOCKED: "X",
    }
    legend = (
        "o normal  * priority  ~ restricted  X blocked  "
        "S start  E end  1-9 drones"
    )

    def __init__(
        self, graph: Graph, visualizer: Visualizer, delay: float
    ) -> None:
        self.graph = graph
        self.visualizer = visualizer
        self.delay = delay
        self.min_x = min(zone.x for zone in graph.zones.values())
        self.min_y = min(zone.y for zone in graph.zones.values())

    def position(self, zone: Zone) -> tuple[int, int]:
        return (zone.x - self.min_x) * 3, (zone.y - self.min_y) * 2

    def marker(self, zone: Zone, count: int) -> str:
        if zone.is_start:
            symbol = "S"
        elif zone.is_end:
            symbol = "E"
        elif count > 0:
            symbol = str(count) if count < 10 else "+"
        else:
            symbol = self.symbols[zone.zone_type]
        return self.visualizer.paint(symbol, zone.color)

    def line_cells(
        self, first: Zone, second: Zone
    ) -> list[tuple[int, int, str]]:
        column_a, row_a = self.position(first)
        column_b, row_b = self.position(second)
        delta_column = column_b - column_a
        delta_row = row_b - row_a
        if abs(delta_column) > 2 * abs(delta_row):
            char = "-"
        elif abs(delta_row) > 2 * abs(delta_column):
            char = "|"
        elif delta_column * delta_row > 0:
            char = "\\"
        else:
            char = "/"
        steps = max(abs(delta_column), abs(delta_row))
        return [
            (
                column_a + round(delta_column * step / steps),
                row_a + round(delta_row * step / steps),
                char,
            )
            for step in range(1, steps)
        ]

    def flying_connections(self, simulation: Simulation) -> list[Connection]:
        return [
            drone.current_connection
            for drone in simulation.drones.values()
            if drone.current_connection is not None
        ]

    def zone_counts(self, simulation: Simulation) -> dict[str, int]:
        counts: dict[str, int] = {}
        for drone in simulation.drones.values():
            if drone.current_zone is not None:
                name = drone.current_zone.name
                counts[name] = counts.get(name, 0) + 1
        return counts

    def draw_map(self, simulation: Simulation) -> list[str]:
        counts = self.zone_counts(simulation)
        flying = self.flying_connections(simulation)
        markers = {
            self.position(zone): self.marker(zone, counts.get(zone.name, 0))
            for zone in self.graph.zones.values()
        }
        cells: dict[tuple[int, int], str] = {}
        for connection in self.graph.connections:
            in_flight = any(connection is other for other in flying)
            for column, row, char in self.line_cells(
                connection.zone_a, connection.zone_b
            ):
                if (column, row) in markers:
                    continue
                if in_flight:
                    cells[(column, row)] = self.visualizer.paint(
                        char, "yellow"
                    )
                else:
                    cells.setdefault((column, row), self.visualizer.dim(char))
        cells.update(markers)
        width = max(column for column, _ in cells) + 1
        height = max(row for _, row in cells) + 1
        return [
            "".join(cells.get((column, row), " ") for column in range(width))
            for row in range(height)
        ]

    def frame(self, simulation: Simulation, moves: list[str]) -> str:
        moves_text = " ".join(
            self.visualizer.paint_move(move) for move in moves
        )
        lines = [f"Turn {simulation.turn}: {moves_text}".rstrip(), ""]
        lines += self.draw_map(simulation)
        lines += [
            "",
            self.visualizer.dim(self.legend),
            self.visualizer.describe_state(simulation),
        ]
        return "\n".join(line + "\033[K" for line in lines)

    def start(self) -> None:
        sys.stdout.write("\033[2J")

    def show(self, simulation: Simulation, moves: list[str]) -> None:
        sys.stdout.write("\033[H" + self.frame(simulation, moves) + "\n\033[J")
        sys.stdout.flush()
        time.sleep(max(0.0, self.delay))
