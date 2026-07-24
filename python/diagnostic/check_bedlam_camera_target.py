"""Read-only check of the persistent BEDLAM camera look-at reference."""

import unreal


actors = unreal.get_editor_subsystem(
    unreal.EditorActorSubsystem
).get_all_level_actors()
camera = next(
    (a for a in actors if a.get_actor_label() == "BE_CineCameraActor_Blueprint"),
    None,
)
target = next(
    (a for a in actors if a.get_actor_label() == "BE_CameraTarget"),
    None,
)

if camera is None or target is None:
    raise RuntimeError("camera={} target={}".format(camera, target))

settings = camera.get_editor_property("lookat_tracking_settings")
tracked = settings.get_editor_property("actor_to_track")
offset = settings.get_editor_property("relative_offset")
unreal.log_warning(
    "[CAMERA_TARGET_CHECK] camera={} enabled={} tracked={} expected={} "
    "matches={} camera_path={} target_path={} target_location={} "
    "map_offset=({}, {}, {})".format(
        camera.get_actor_label(),
        settings.get_editor_property("enable_look_at_tracking"),
        tracked.get_actor_label() if tracked else None,
        target.get_actor_label(),
        tracked == target,
        camera.get_path_name(),
        target.get_path_name(),
        target.get_actor_location(),
        offset.x,
        offset.y,
        offset.z,
    )
)
