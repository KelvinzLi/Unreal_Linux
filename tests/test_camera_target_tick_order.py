"""CPU checks of production dependency wiring without importing Unreal."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class TargetTickOrderTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'python/render_bedlam_mrq.py'
        tree = ast.parse(path.read_text())
        names = {'ensure_target_tick_prerequisite', 'get_runtime_probe_actors'}
        tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        self.camera = Mock()
        self.component = Mock()
        self.parent = Mock()
        self.parent.get_component_by_class.return_value = self.component
        self.target = Mock()
        self.target.get_attach_parent_actor.return_value = self.parent
        self.actors = {'camera': self.camera, 'target': self.target}
        self.state = dict(
            unreal=SimpleNamespace(SkeletalMeshComponent=object, GameplayStatics=Mock(), log_warning=Mock()),
            _configured_target_dependencies=[], _cached_world=None, _cached_actors={},
            _configured_camera=None, _configured_controller=None,
            TICK_GROUP_FIX=False, TICK_PREREQUISITE_FIX=True,
            CAMERA_LABEL='camera', TARGET_LABEL='target', ROOT_LABEL='root', OPERATOR_LABEL='operator',
            runtime_actors=lambda world: self.actors,
            find_runtime_actor=lambda actors, label: actors.get(label),
            safe_call=lambda *args: None,
        )
        exec(compile(tree, str(path), 'exec'), self.state)
        self.probe = self.state['get_runtime_probe_actors']

    def test_adds_component_once_without_controller(self):
        self.probe('rgb')
        self.probe('rgb')
        self.camera.add_tick_prerequisite_component.assert_called_once_with(self.component)

    def test_new_world_gets_dependency_even_with_reused_names(self):
        self.probe('rgb')
        other = Mock()
        self.actors['camera'] = other
        self.probe('depth')
        other.add_tick_prerequisite_component.assert_called_once_with(self.component)
        self.assertEqual(self.state['_configured_target_dependencies'], [(other, self.component)])

    def test_static_target_unchanged(self):
        self.target.get_attach_parent_actor.return_value = None
        self.probe('rgb')
        self.camera.add_tick_prerequisite_component.assert_not_called()

    def test_retries_late_skeletal_component(self):
        self.parent.get_component_by_class.return_value = None
        self.probe('rgb')
        self.parent.get_component_by_class.return_value = self.component
        self.probe('rgb')
        self.camera.add_tick_prerequisite_component.assert_called_once_with(self.component)

    def test_disabled_flag_unchanged(self):
        self.state['TICK_PREREQUISITE_FIX'] = False
        self.probe('rgb')
        self.camera.add_tick_prerequisite_component.assert_not_called()

    def test_first_world_camera_spawns_late(self):
        self.actors['camera'] = None
        self.probe('first_rgb')
        self.actors['camera'] = self.camera
        self.probe('first_rgb')
        self.camera.add_tick_prerequisite_component.assert_called_once_with(self.component)

    def test_first_world_target_spawns_late(self):
        self.actors['target'] = None
        self.probe('first_rgb')
        self.actors['target'] = self.target
        self.probe('first_rgb')
        self.camera.add_tick_prerequisite_component.assert_called_once_with(self.component)

    def test_missing_target_unchanged(self):
        self.actors['target'] = None
        self.probe('rgb')
        self.camera.add_tick_prerequisite_component.assert_not_called()


if __name__ == '__main__':
    unittest.main()
