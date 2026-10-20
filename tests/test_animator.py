import os
import tempfile
import unittest
from unittest.mock import patch

from animator import Animator
from engine import Simulation
from graph import Graph
from parser import parse_map
from visualizer import Visualizer


class AnimatorTestCase(unittest.TestCase):
    text = (
        "nb_drones: 2\n"
        "start_hub: s 0 0\n"
        "end_hub: g 2 1\n"
        "hub: a 1 0 [zone=priority color=red max_drones=2]\n"
        "hub: r 1 1 [zone=restricted]\n"
        "connection: s-a [max_link_capacity=2]\n"
        "connection: a-g\n"
        "connection: s-r\n"
        "connection: r-g\n"
    )

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "map.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write(self.text)
        data = parse_map(path)
        self.graph = Graph(data)
        self.simulation = Simulation(self.graph, data.nb_drones)

    def animator(self, color: bool = False, delay: float = 0) -> Animator:
        visualizer = Visualizer(self.graph, color, False)
        return Animator(self.graph, visualizer, delay)

    def move(self, *names: str) -> list[str]:
        zones = self.graph.zones
        return self.simulation.step(
            {number: zones[name] for number, name in enumerate(names, 1)}
        )


class TestDrawing(AnimatorTestCase):
    def test_positions_are_scaled_and_start_at_zero(self) -> None:
        animator = self.animator()
        self.assertEqual(animator.position(self.graph.zones["s"]), (0, 0))
        self.assertEqual(animator.position(self.graph.zones["g"]), (6, 2))

    def test_line_characters_follow_the_direction(self) -> None:
        animator = self.animator()
        zones = self.graph.zones
        horizontal = animator.line_cells(zones["s"], zones["a"])
        self.assertEqual(horizontal, [(1, 0, "-"), (2, 0, "-")])
        vertical = animator.line_cells(zones["a"], zones["r"])
        self.assertEqual(vertical, [(3, 1, "|")])
        diagonal = animator.line_cells(zones["s"], zones["r"])
        self.assertEqual({char for _, _, char in diagonal}, {"\\"})

    def test_map_without_drones(self) -> None:
        rows = self.animator().draw_map(self.simulation)
        self.assertEqual(rows[0].rstrip(), "S--*")
        self.assertEqual(rows[2][3], "~")
        self.assertEqual(rows[2][-1], "E")

    def test_zone_with_drone_shows_the_count(self) -> None:
        self.move("a", "a")
        rows = self.animator().draw_map(self.simulation)
        self.assertEqual(rows[0][3], "2")

    def test_color_only_when_enabled(self) -> None:
        self.move("a")
        plain = self.animator().frame(self.simulation, ["D1-a"])
        colored = self.animator(color=True).frame(self.simulation, ["D1-a"])
        self.assertNotIn("\033[3", plain)
        self.assertIn("\033[38;5;196m", colored)

    def test_connection_with_flying_drone_is_highlighted(self) -> None:
        self.move("r")
        rows = self.animator(color=True).draw_map(self.simulation)
        self.assertIn("\033[38;5;226m", "".join(rows))


class TestShow(AnimatorTestCase):
    def test_frame_has_turn_state_and_legend(self) -> None:
        moves = self.move("a", "a")
        lines = self.animator().frame(self.simulation, moves).split("\n")
        self.assertTrue(lines[0].startswith("Turn 1: D1-a D2-a"))
        self.assertIn("S start", lines[-2])
        self.assertIn("delivered: 0/2", lines[-1])

    def test_show_redraws_in_place_and_waits(self) -> None:
        animator = self.animator(delay=0.25)
        with patch("sys.stdout") as stdout, patch("time.sleep") as sleep:
            animator.show(self.simulation, [])
        written = stdout.write.call_args[0][0]
        self.assertTrue(written.startswith("\033[H"))
        self.assertTrue(written.endswith("\033[J"))
        sleep.assert_called_once_with(0.25)

    def test_negative_delay_does_not_sleep_backwards(self) -> None:
        animator = self.animator(delay=-1)
        with patch("sys.stdout"), patch("time.sleep") as sleep:
            animator.show(self.simulation, [])
        sleep.assert_called_once_with(0.0)


if __name__ == "__main__":
    unittest.main()