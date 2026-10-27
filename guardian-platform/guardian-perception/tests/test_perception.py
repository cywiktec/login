import math
import unittest

from guardian_perception import camera, lidar, person_detection, yolo
from guardian_perception.event_detection import EventDetector
from guardian_perception.object_tracker import ObjectTracker
from guardian_perception.yolo import make_detection as D


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


class CameraTests(unittest.TestCase):
    def test_validation(self):
        for args in ((0, 10, 1), (10, 10, float("nan")), (10, True, 1), (2, 2, 1, b"x")):
            with self.assertRaises(camera.FrameError):
                camera.make_frame(*args)
        with self.assertRaises(camera.FrameError):
            camera.make_frame(2, 2, 1, encoding="yuv")
        camera.make_frame(2, 2, 1, b"\0" * 12)

    def test_freshness_and_ordering(self):
        clock = Clock()
        src = camera.CameraSource(max_age=0.5, clock=clock)
        self.assertIsNone(src.latest())
        self.assertTrue(src.push(camera.make_frame(2, 2, 1.0)))
        self.assertFalse(src.push(camera.make_frame(2, 2, 1.0)))
        self.assertIsNotNone(src.latest())
        clock.t = 1.0
        self.assertIsNone(src.latest())
        with self.assertRaises(camera.FrameError):
            src.push("frame")


class LidarTests(unittest.TestCase):
    def scan(self, ranges):
        return lidar.make_scan(-0.5, 0.1, ranges, 0.1, 10.0, 0.0)

    def test_validation(self):
        with self.assertRaises(lidar.ScanError):
            self.scan([])
        with self.assertRaises(lidar.ScanError):
            lidar.make_scan(0, 0, [1], 0.1, 10, 0)
        with self.assertRaises(lidar.ScanError):
            lidar.make_scan(0, 0.1, [1], 5, 1, 0)

    def test_invalid_readings_dropped(self):
        s = self.scan([1, float("nan"), float("inf"), 0.01, 20, 2])
        self.assertEqual(len(lidar.valid_points(s)), 2)
        self.assertAlmostEqual(lidar.invalid_fraction(s), 4 / 6)

    def test_min_distance_unknown_is_none_not_clear(self):
        s = self.scan([3, 2, 5, float("nan"), float("nan"), float("nan")])
        self.assertEqual(lidar.min_distance(s, -0.5, -0.3), 2)
        self.assertIsNone(lidar.min_distance(s, -0.2, -0.0))   # mostly unusable
        self.assertIsNone(lidar.min_distance(s, 5, 6))          # empty sector

    def test_clusters(self):
        ranges = [2.0] * 4 + [float("nan")] + [5.0] * 4 + [float("nan"), 3.0]
        s = lidar.make_scan(0.0, 0.02, ranges, 0.1, 10, 0)
        found = lidar.clusters(s, gap=0.3, min_points=3)
        self.assertEqual(len(found), 2)
        self.assertEqual(sorted(c["points"] for c in found), [4, 4])


class YoloTests(unittest.TestCase):
    def test_detection_validation(self):
        for args in (("", .9, 0, 0, 1, 1), ("a", 1.5, 0, 0, 1, 1), ("a", .9, 1, 0, 0, 1),
                     ("a", float("nan"), 0, 0, 1, 1), ("a", True, 0, 0, 1, 1)):
            with self.assertRaises(yolo.DetectionError):
                D(*args)

    def test_iou(self):
        a, b = D("a", .9, 0, 0, 10, 10), D("a", .9, 5, 0, 15, 10)
        self.assertAlmostEqual(yolo.iou(a, b), 1 / 3)
        self.assertEqual(yolo.iou(a, D("a", .9, 20, 20, 30, 30)), 0.0)

    def test_nms_per_label(self):
        dets = [D("person", .9, 0, 0, 10, 10), D("person", .8, 1, 1, 10, 10), D("dog", .7, 0, 0, 10, 10)]
        kept = yolo.nms(dets, 0.5)
        self.assertEqual([(d.label, d.confidence) for d in kept], [("person", .9), ("dog", .7)])

    def test_postprocess_drops_bad_rows(self):
        raw = [(0, .9, 0, 0, 5, 5), (7, .9, 0, 0, 5, 5), (0, .2, 0, 0, 5, 5), (0, .9), ("x", .9, 0, 0, 5, 5),
               (0, float("nan"), 0, 0, 5, 5)]
        dets, dropped = yolo.postprocess(raw, ["person"], min_confidence=0.5)
        self.assertEqual(len(dets), 1)
        self.assertEqual(dropped, 4)


class TrackerTests(unittest.TestCase):
    def test_stable_ids_and_confirmation(self):
        tr = ObjectTracker(min_hits=2, max_missed=1)
        self.assertEqual(tr.update([D("person", .9, 0, 0, 10, 20)], 0), [])
        confirmed = tr.update([D("person", .9, 1, 0, 11, 20)], 1)
        self.assertEqual([t.id for t in confirmed], [1])
        confirmed = tr.update([D("person", .9, 2, 0, 12, 20)], 2)
        self.assertEqual(confirmed[0].id, 1)
        self.assertEqual(confirmed[0].hits, 3)

    def test_label_mismatch_and_expiry(self):
        tr = ObjectTracker(max_missed=1)
        tr.update([D("person", .9, 0, 0, 10, 10)], 0)
        tr.update([D("dog", .9, 0, 0, 10, 10)], 1)
        self.assertEqual({t.label for t in tr.all_tracks()}, {"person", "dog"})
        tr.update([], 2)
        tr.update([], 3)
        self.assertEqual(tr.all_tracks(), [])

    def test_two_objects_not_swapped(self):
        tr = ObjectTracker()
        tr.update([D("p", .9, 0, 0, 10, 10), D("p", .9, 100, 0, 110, 10)], 0)
        tr.update([D("p", .9, 101, 0, 111, 10), D("p", .9, 1, 0, 11, 10)], 1)
        by_id = {t.id: t.det.x1 for t in tr.all_tracks()}
        self.assertEqual(by_id, {1: 1, 2: 101})


class PersonTests(unittest.TestCase):
    def test_filters(self):
        dets = [D("person", .9, 0, 0, 10, 50), D("person", .4, 0, 0, 10, 80), D("dog", .9, 0, 0, 10, 90)]
        self.assertEqual(person_detection.count(dets), 1)
        self.assertEqual(person_detection.nearest_by_box_height(dets).y2, 50)
        self.assertIsNone(person_detection.nearest_by_box_height([]))
        self.assertTrue(person_detection.in_zone(dets[0], (0, 0, 20, 60)))
        self.assertFalse(person_detection.in_zone(dets[0], (50, 0, 60, 60)))


class EventTests(unittest.TestCase):
    def tracks(self, tr, *boxes):
        return tr.update([D("person", .9, *b) for b in boxes], len(self.log))

    def setUp(self):
        self.log = []
        self.det = EventDetector(zone=(0, 0, 100, 100))
        self.tr = ObjectTracker(min_hits=1)

    def test_person_in_zone_fires_once(self):
        t = self.tracks(self.tr, (10, 10, 20, 60))
        self.assertEqual([e["event"] for e in self.det.update(0, t)], ["person_in_zone"])
        self.assertEqual(self.det.update(1, self.tracks(self.tr, (10, 10, 20, 60))), [])
        self.det.update(2, self.tr.update([], 2))   # leaves -> re-arms
        t = self.tracks(self.tr, (10, 10, 20, 60))
        self.assertEqual([e["event"] for e in self.det.update(3, t)], ["person_in_zone"])

    def test_motion(self):
        self.det.update(0, self.tracks(self.tr, (10, 10, 20, 60)))
        ev = self.det.update(1, self.tracks(self.tr, (15, 10, 25, 60)))
        self.assertIn("motion", [e["event"] for e in ev])

    def test_still_person_no_motion(self):
        self.det.update(0, self.tracks(self.tr, (10, 10, 20, 60)))
        ev = self.det.update(1, self.tracks(self.tr, (10, 10, 20, 60)))
        self.assertNotIn("motion", [e["event"] for e in ev])

    def test_obstacle_close_and_unknown_keeps_state(self):
        self.assertEqual(self.det.update(0, [], 0.5)[0]["event"], "obstacle_close")
        self.assertEqual(self.det.update(1, [], None), [])       # lidar lost: still active
        self.assertEqual(self.det.update(2, [], float("nan")), [])
        self.assertEqual(self.det.update(3, [], 0.5), [])        # no repeat
        self.det.update(4, [], 3.0)
        self.assertEqual(self.det.update(5, [], 0.5)[0]["event"], "obstacle_close")

    def test_camera_loss_does_not_clear(self):
        t = self.tracks(self.tr, (10, 10, 20, 60))
        self.det.update(0, t)
        self.det.update(1, None)                                  # camera unavailable
        self.assertEqual(self.det.update(2, t), [])


if __name__ == "__main__":
    unittest.main()
