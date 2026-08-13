"""Assign BE_CameraTarget on every map listed in BEDLAM_CAMERA_MAPS.

BEDLAM_CAMERA_MAPS is a semicolon-separated list of /Game package paths.
The script loads, repairs, saves, and verifies each persistent level in one
editor process. It exits by raising if any map cannot be repaired.
"""

import os

import unreal


CAMERA_LABEL = "BE_CineCameraActor_Blueprint"
TARGET_LABEL = "BE_CameraTarget"
MAPS_ENV = "BEDLAM_CAMERA_MAPS"


def find_actor(actors, label):
    return next((actor for actor in actors if actor.get_actor_label() == label), None)


def repair_map(map_path):
    if not unreal.EditorLevelLibrary.load_level(map_path):
        raise RuntimeError("Failed to load map: {}".format(map_path))

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = actor_subsystem.get_all_level_actors()
    camera = find_actor(actors, CAMERA_LABEL)
    target = find_actor(actors, TARGET_LABEL)
    if camera is None or target is None:
        raise RuntimeError(
            "Missing BEDLAM actors in {}: camera={} target={}".format(
                map_path, camera, target
            )
        )

    settings = camera.get_editor_property("lookat_tracking_settings")
    before = settings.get_editor_property("actor_to_track")
    changed = before != target
    if changed:
        settings.set_editor_property("actor_to_track", target)
        camera.set_editor_property("lookat_tracking_settings", settings)
        if not unreal.EditorLevelLibrary.save_current_level():
            raise RuntimeError("Failed to save map: {}".format(map_path))

    after = camera.get_editor_property(
        "lookat_tracking_settings"
    ).get_editor_property("actor_to_track")
    if after != target:
        raise RuntimeError("Actor To Track verification failed: {}".format(map_path))

    unreal.log_warning(
        "[CAMERA_TARGET_BATCH] map={} changed={} before={} after={} verified=True".format(
            map_path,
            changed,
            before.get_actor_label() if before else None,
            after.get_actor_label(),
        )
    )


map_paths = [value.strip() for value in os.environ.get(MAPS_ENV, "").split(";")]
map_paths = [value for value in map_paths if value]
if not map_paths:
    raise RuntimeError("{} is empty".format(MAPS_ENV))

for package_path in map_paths:
    repair_map(package_path)

unreal.log_warning("[CAMERA_TARGET_BATCH_DONE] maps={}".format(len(map_paths)))
