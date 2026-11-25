"""Pure-Python tests of the actual camera helper; no Unreal/GPU work launched."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

SOURCE = Path(__file__).resolve().parents[2] / 'Syn4d_renderer/unreal/render/Core/Python/tools/camera_sampling/common.py'
spec = importlib.util.spec_from_file_location('camera_duration_test_common', SOURCE)
common = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'unreal': MagicMock()}):
    spec.loader.exec_module(common)


def candidate(mode='orbit'):
    start = dict(frame_index=-1, hfov=70,
                 camera_local=dict(x=-300, y=0, z=0),
                 cameraroot=dict(x=0, y=0, z=90, yaw=20, pitch=-20, roll=0))
    end = copy.deepcopy(start)
    end['frame_index'] = 383
    end['camera_local']['x'] = -500
    end['cameraroot']['yaw'] = 120
    end['cameraroot']['pitch'] = -40
    return dict(camera_motion_mode=mode, keyframes=[start, end],
                shake=dict(scale=10, frequency=2), look_at=dict(target='body_0', interpolation=5))


class CameraScalingTests(unittest.TestCase):
    def test_default_and_reference_are_exact_noops(self):
        value = candidate()
        self.assertIs(common.scale_candidate_motion_duration(value, 383), value)
        self.assertIs(common.scale_candidate_motion_duration(value, 192, {'motion_reference_frames': 192}), value)

    def test_short_orbit_preserves_start_and_nonmotion_settings(self):
        value = candidate()
        original = copy.deepcopy(value)
        result = common.scale_candidate_motion_duration(value, 97, {'motion_reference_frames': 193})
        self.assertEqual(value, original)
        self.assertEqual(result['keyframes'][0], original['keyframes'][0])
        self.assertEqual(result['keyframes'][1]['frame_index'], 383)
        self.assertEqual(result['keyframes'][1]['camera_local']['x'], -400)
        self.assertEqual(result['keyframes'][1]['cameraroot']['yaw'], 70)
        self.assertEqual(result['keyframes'][1]['cameraroot']['pitch'], -30)
        self.assertEqual(result['shake'], original['shake'])
        self.assertEqual(result['look_at'], original['look_at'])

    def test_dolly_scales_displacement_not_absolute_distance(self):
        value = candidate('dolly_x')
        result = common.scale_candidate_motion_duration(value, 97, {'motion_reference_frames': 193})
        self.assertEqual(result['keyframes'][1]['camera_local']['x'], -400)
        self.assertEqual(result['keyframes'][1]['cameraroot'], value['keyframes'][1]['cameraroot'])

    def test_long_motion_respects_existing_camera_bounds(self):
        result = common.scale_candidate_motion_duration(candidate(), 1920, {'motion_reference_frames': 192})
        end = result['keyframes'][1]
        self.assertLess(abs(end['cameraroot']['yaw'] - 20), 180)
        self.assertEqual(end['cameraroot']['pitch'], common.DEFAULT_PHI_MIN_DEG)
        self.assertEqual(-end['camera_local']['x'], common.DEFAULT_DISTANCE_MAX_CM)

    def test_static_unchanged(self):
        value = candidate('static')
        self.assertIs(common.scale_candidate_motion_duration(value, 383, {'motion_reference_frames': 192}), value)


if __name__ == '__main__':
    unittest.main()
