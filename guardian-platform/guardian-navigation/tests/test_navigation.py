import math
import unittest

from guardian_navigation.geofence_provider import GeofenceProvider, point_in_polygon
from guardian_navigation.localization import Localizer, Pose
from guardian_navigation.maps import OccupancyGrid
from guardian_navigation.obstacle import ObstacleLevel, ObstacleMonitor, mark_obstacle
from guardian_navigation.planner import NoPathError, PathPlanner
from guardian_navigation.waypoint import WaypointTracker


class GridTests(unittest.TestCase):
    def test_conversion_and_bounds(self):
        grid = OccupancyGrid(10, 10, resolution=0.5, origin=(-1.0, -1.0))
        self.assertEqual(grid.world_to_cell(-1.0, -1.0), (0, 0))
        self.assertEqual(grid.world_to_cell(0.0, 0.0), (2, 2))
        self.assertEqual(grid.cell_to_world(2, 2), (0.25, 0.25))
        self.assertFalse(grid.is_free(-1, 0))
        self.assertFalse(grid.is_free(10, 0))
        with self.assertRaises(IndexError):
            grid.set_blocked(10, 10)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            OccupancyGrid(0, 5)
        with self.assertRaises(ValueError):
            OccupancyGrid(5, 5, resolution=0)


class PlannerTests(unittest.TestCase):
    def test_straight_and_diagonal(self):
        planner = PathPlanner(OccupancyGrid(5, 5))
        self.assertEqual(planner.plan_cells((0, 0), (4, 0)), [(i, 0) for i in range(5)])
        self.assertEqual(len(planner.plan_cells((0, 0), (4, 4))), 5)

    def test_routes_around_wall(self):
        grid = OccupancyGrid(5, 5)
        for y in range(4):
            grid.set_blocked(2, y)
        path = PathPlanner(grid).plan_cells((0, 0), (4, 0))
        self.assertTrue(all(grid.is_free(*c) for c in path))
        self.assertIn((2, 4), path)

    def test_no_corner_cutting(self):
        grid = OccupancyGrid(2, 2)
        grid.set_blocked(1, 0)
        grid.set_blocked(0, 1)
        with self.assertRaises(NoPathError):
            PathPlanner(grid).plan_cells((0, 0), (1, 1))

    def test_blocked_endpoints_and_unreachable(self):
        grid = OccupancyGrid(3, 1)
        grid.set_blocked(1, 0)
        planner = PathPlanner(grid)
        with self.assertRaises(NoPathError):
            planner.plan_cells((0, 0), (2, 0))
        with self.assertRaises(NoPathError):
            planner.plan_cells((1, 0), (0, 0))
        with self.assertRaises(NoPathError):
            planner.plan_cells((0, 0), (9, 9))

    def test_world_plan(self):
        path = PathPlanner(OccupancyGrid(3, 1, resolution=2.0)).plan((0.5, 0.5), (5.5, 0.5))
        self.assertEqual(path, [(1.0, 1.0), (3.0, 1.0), (5.0, 1.0)])


class WaypointTests(unittest.TestCase):
    def test_progress(self):
        tracker = WaypointTracker([(0, 0), (5, 0)], tolerance=0.5)
        self.assertEqual(tracker.update(0.1, 0), (5, 0))
        self.assertEqual(tracker.update(2, 0), (5, 0))
        self.assertIsNone(tracker.update(5, 0.2))
        self.assertTrue(tracker.done)

    def test_skips_several_reached(self):
        tracker = WaypointTracker([(0, 0), (0.1, 0), (5, 0)], tolerance=0.5)
        self.assertEqual(tracker.update(0, 0), (5, 0))
        self.assertEqual(tracker.remaining(), [(5, 0)])

    def test_reset_and_invalid(self):
        tracker = WaypointTracker([(0, 0)])
        tracker.update(0, 0)
        tracker.reset()
        self.assertFalse(tracker.done)
        with self.assertRaises(ValueError):
            WaypointTracker([], tolerance=0)


class ObstacleTests(unittest.TestCase):
    def test_levels(self):
        monitor = ObstacleMonitor(slow_distance=1.5, stop_distance=0.5)
        self.assertIs(monitor.classify([3.0, 2.0]), ObstacleLevel.CLEAR)
        self.assertIs(monitor.classify([3.0, 1.0]), ObstacleLevel.SLOW)
        self.assertIs(monitor.classify([3.0, 0.4]), ObstacleLevel.STOP)

    def test_invalid_readings(self):
        monitor = ObstacleMonitor()
        self.assertIs(monitor.classify([math.nan, math.inf, -1]), ObstacleLevel.STOP)
        self.assertIs(monitor.classify([]), ObstacleLevel.STOP)
        self.assertIs(monitor.classify([math.nan, 5.0]), ObstacleLevel.CLEAR)

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            ObstacleMonitor(slow_distance=0.5, stop_distance=1.0)

    def test_mark_obstacle(self):
        grid = OccupancyGrid(10, 10)
        self.assertEqual(mark_obstacle(grid, 5.5, 5.5), 1)
        self.assertFalse(grid.is_free(5, 5))
        self.assertGreater(mark_obstacle(grid, 2.5, 2.5, radius=1.0), 1)
        self.assertEqual(mark_obstacle(grid, 99, 99, radius=0.0), 0)


class LocalizationTests(unittest.TestCase):
    def test_straight_and_turn(self):
        loc = Localizer()
        loc.predict(1.0, 0.0, 2.0)
        self.assertAlmostEqual(loc.pose.x, 2.0)
        loc.predict(0.0, math.pi, 1.0)
        self.assertAlmostEqual(abs(loc.pose.theta), math.pi)

    def test_arc_returns_to_start(self):
        loc = Localizer()
        for _ in range(100):
            loc.predict(1.0, 2 * math.pi / 100, 1.0)
        self.assertAlmostEqual(loc.pose.x, 0.0, places=2)
        self.assertAlmostEqual(loc.pose.y, 0.0, places=2)

    def test_correct(self):
        loc = Localizer(Pose(0, 0, 0))
        loc.correct(2, 4, weight=0.5)
        self.assertEqual((loc.pose.x, loc.pose.y), (1.0, 2.0))
        loc.correct(10, 10, theta=1.0)
        self.assertEqual((loc.pose.x, loc.pose.y, loc.pose.theta), (10, 10, 1.0))
        with self.assertRaises(ValueError):
            loc.correct(0, 0, weight=0)
        with self.assertRaises(ValueError):
            loc.predict(1, 0, -1)


class GeofenceProviderTests(unittest.TestCase):
    SQUARE = [(0, 0), (4, 0), (4, 4), (0, 4)]

    def test_add_get_contains(self):
        provider = GeofenceProvider()
        provider.add("yard", self.SQUARE)
        self.assertEqual(provider.names(), ["yard"])
        self.assertTrue(provider.contains("yard", 2, 2))
        self.assertTrue(provider.contains("yard", 4, 2))
        self.assertFalse(provider.contains("yard", 5, 2))
        with self.assertRaises(KeyError):
            provider.get("nope")
        with self.assertRaises(ValueError):
            provider.add("bad", [(0, 0), (1, 1)])

    def test_load_json(self):
        provider = GeofenceProvider()
        provider.load('{"a": [[0, 0], [1, 0], [1, 1]]}')
        self.assertEqual(provider.names(), ["a"])
        with self.assertRaises(ValueError):
            provider.load("[1, 2]")

    def test_apply_to_grid_confines_planner(self):
        grid = OccupancyGrid(6, 6)
        provider = GeofenceProvider()
        provider.add("yard", [(0, 0), (3, 0), (3, 3), (0, 3)])
        self.assertEqual(provider.apply_to_grid(grid, "yard"), 36 - 9)
        self.assertTrue(grid.is_free(1, 1))
        with self.assertRaises(NoPathError):
            PathPlanner(grid).plan_cells((0, 0), (5, 5))

    def test_point_in_polygon_function(self):
        self.assertTrue(point_in_polygon(self.SQUARE, 1, 1))
        self.assertFalse(point_in_polygon(self.SQUARE, -1, 1))
