"""Assign the persistent BEDLAM CineCamera look-at target and save the map."""

import unreal


CAMERA_LABEL = "BE_CineCameraActor_Blueprint"
TARGET_LABEL = "BE_CameraTarget"


actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = actor_subsystem.get_all_level_actors()

camera = next(
    (actor for actor in actors if actor.get_actor_label() == CAMERA_LABEL),
    None,
)
target = next(
    (actor for actor in actors if actor.get_actor_label() == TARGET_LABEL),
    None,
)

if camera is None or target is None:
    raise RuntimeError(
        "Could not find camera/target: camera={}, target={}".format(
            camera,
            target,
        )
    )

settings = camera.get_editor_property("lookat_tracking_settings")
before = settings.get_editor_property("actor_to_track")
offset = settings.get_editor_property("relative_offset")
settings.set_editor_property("actor_to_track", target)
camera.set_editor_property("lookat_tracking_settings", settings)

after = camera.get_editor_property(
    "lookat_tracking_settings"
).get_editor_property("actor_to_track")
if after != target:
    raise RuntimeError("Actor To Track assignment did not persist in memory")

unreal.EditorLevelLibrary.save_current_level()
unreal.log_warning(
    "[CAMERA_TARGET_FIX] camera={} before={} after={} "
    "relative_offset=({}, {}, {}) saved=True".format(
        camera.get_actor_label(),
        before,
        after.get_actor_label(),
        offset.x,
        offset.y,
        offset.z,
    )
)
