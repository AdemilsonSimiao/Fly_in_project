import argparse
import sys

from engine import Simulation, SimulationError
from graph import Graph
from parser import ParseError, parse_map
from path_finding import Scheduler
from visualizer import Visualizer


class Application:
    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="Route drones through a network of zones."
        )
        parser.add_argument("map_file", help="path to the map file")
        parser.add_argument(
            "--visual",
            action="store_true",
            help="show the zone states after every turn",
        )
        return parser

    def run(self, argv: list[str]) -> int:
        arguments = self.build_parser().parse_args(argv)
        path: str = arguments.map_file
        detailed: bool = arguments.visual
        try:
            return self.simulate(path, detailed)
        except (ParseError, SimulationError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1

    def simulate(self, path: str, detailed: bool) -> int:
        data = parse_map(path)
        graph = Graph(data)
        if not graph.path_destination():
            print(
                "Error: there is no path from the start zone "
                "to the end zone",
                file=sys.stderr,
            )
            return 1
        schedule = Scheduler(graph).plan(data.nb_drones)
        simulation = Simulation(graph, data.nb_drones)
        visualizer = Visualizer(graph, sys.stdout.isatty(), detailed)
        visualizer.show_header(data)
        for moves in schedule:
            visualizer.show_turn(simulation, simulation.step(moves))
        visualizer.show_summary(data.nb_drones, simulation.turn)
        return 0


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv[1:]))
