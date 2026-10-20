import unittest

from errors import WindowError
from graph import Graph
from parser import parse_map
from path_finding import Scheduler
from timeline import Timeline
from window import Window


class TestWindow(unittest.TestCase):
    def setUp(self) -> None:
        data = parse_map("maps/medium/03_priority_puzzle.txt")
        graph = Graph(data)
        schedule = Scheduler(graph).plan(data.nb_drones)
        self.timeline = Timeline(graph, data.nb_drones, schedule)
        try:
            self.window = Window(graph, self.timeline)
        except WindowError:
            self.skipTest("no display available")
        self.addCleanup(self.window.root.destroy)

    def items(self) -> int:
        return len(self.window.canvas.find_all())

    def test_draws_zones_and_connections(self) -> None:
        self.assertGreater(self.items(), len(self.window.graph.zones))
        self.assertEqual(len(self.window.points), len(self.window.graph.zones))

    def test_next_starts_the_next_turn(self) -> None:
        self.window.advance()
        self.assertEqual((self.window.turn, self.window.progress), (1, 0.0))
        self.window.advance()
        self.assertEqual((self.window.turn, self.window.progress), (1, 1.0))

    def test_back_and_restart(self) -> None:
        self.window.advance()
        self.window.advance()
        self.window.back()
        self.assertEqual(self.window.turn, 0)
        self.window.advance()
        self.window.restart()
        self.assertEqual((self.window.turn, self.window.progress), (0, 1.0))
        self.window.back()
        self.assertEqual(self.window.turn, 0)

    def test_playing_reaches_the_last_turn(self) -> None:
        self.window.playing = True
        for _ in range(100000):
            self.window.tick()
            if not self.window.playing and self.window.progress >= 1.0:
                break
        self.assertEqual(self.window.turn, self.timeline.last)
        self.assertIn("delivered 5/5", self.window.status.cget("text"))

    def test_drones_are_drawn_while_moving(self) -> None:
        resting = self.items()
        self.window.turn = 2
        self.window.progress = 0.5
        self.window.draw()
        self.assertGreater(self.items(), resting)

    def test_hover_describes_a_zone(self) -> None:
        zone = self.window.graph.zones["fast_path"]
        self.assertIn("fast_path", self.window.describe(zone))
        self.assertIn("0 drones", self.window.describe(self.window.graph.end))

    def test_unknown_color_falls_back(self) -> None:
        self.assertEqual(
            self.window.color_of("notacolor"), self.window.default_fill
        )
        self.assertEqual(self.window.color_of("red"), "red")


if __name__ == "__main__":
    unittest.main()