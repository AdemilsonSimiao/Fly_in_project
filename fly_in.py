import argparse
import sys
from animator import Animator
from engine import Simulation
from errors import ParseError, SimulationError, WindowError
from graph import Graph
from models import Zone
from parser import MapData, parse_map
from path_finding import Scheduler
from timeline import Timeline
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
        parser.add_argument(
            "--animate",
            action="store_true",
            help="animate the map in the terminal, one frame per turn",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.5,
            help="seconds between animation frames (default: 0.5)",
        )
        parser.add_argument(
            "--gui",
            action="store_true",
            help="open a window that plays the simulation",
        )
        return parser

    def run(self, argv: list[str]) -> int:
        arguments = self.build_parser().parse_args(argv)
        try:
            return self.simulate(arguments)
        except (ParseError, SimulationError, WindowError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1

    def simulate(self, arguments: argparse.Namespace) -> int:
        data = parse_map(arguments.map_file)
        graph = Graph(data)
        if not graph.path_destination():
            print(
                "Error: there is no path from the start zone "
                "to the end zone",
                file=sys.stderr,
            )
            return 1
        schedule = Scheduler(graph).plan(data.nb_drones)
        visualizer = Visualizer(graph, sys.stdout.isatty(), arguments.visual)
        if arguments.gui:
            return self.show_window(graph, data, schedule, visualizer)
        if arguments.animate:
            delay: float = arguments.delay
            return self.animate(graph, data, schedule, visualizer, delay)
        return self.print_turns(graph, data, schedule, visualizer)

    def print_turns(
        self,
        graph: Graph,
        data: MapData,
        schedule: list[dict[int, Zone]],
        visualizer: Visualizer,
    ) -> int:
        simulation = Simulation(graph, data.nb_drones)
        visualizer.show_header(data)
        for moves in schedule:
            visualizer.show_turn(simulation, simulation.step(moves))
        visualizer.show_summary(data.nb_drones, simulation.turn)
        return 0

    def animate(
        self,
        graph: Graph,
        data: MapData,
        schedule: list[dict[int, Zone]],
        visualizer: Visualizer,
        delay: float,
    ) -> int:
        if not sys.stdout.isatty():
            print("Error: --animate needs a terminal", file=sys.stderr)
            return 1
        simulation = Simulation(graph, data.nb_drones)
        animator = Animator(graph, visualizer, delay)
        animator.start()
        animator.show(simulation, [])
        for moves in schedule:
            animator.show(simulation, simulation.step(moves))
        visualizer.show_summary(data.nb_drones, simulation.turn)
        return 0

    def show_window(
        self,
        graph: Graph,
        data: MapData,
        schedule: list[dict[int, Zone]],
        visualizer: Visualizer,
    ) -> int:
        try:
            from window import Window
        except ImportError:
            print("Error: tkinter is not available", file=sys.stderr)
            return 1
        timeline = Timeline(graph, data.nb_drones, schedule)
        window = Window(graph, timeline)
        for moves in timeline.moves[1:]:
            print(" ".join(moves))
        visualizer.show_summary(data.nb_drones, timeline.last)
        window.run()
        return 0


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv[1:]))
