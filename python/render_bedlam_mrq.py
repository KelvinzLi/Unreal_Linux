"""
Render the saved BEDLAM MRQ queue with MoviePipelinePIEExecutor while logging
the runtime camera state from the same Unreal process that produces the images.

Run this with the full Unreal Editor (not -game and not -nullrhi), for example:

    UnrealEditor PROJECT MAP \
      -ExecutePythonScript=/absolute/path/render_bedlam_mrq.py \
      -RenderOffscreen -vulkan -unattended -NoSplash \
      -stdout -FullStdOutLogOutput

Environment variables:
    BEDLAM_RUNTIME_PROBE_DIR
        CSV/log output directory.
    BEDLAM_RUNTIME_RENDER_DIR
        Transient MRQ image output directory. The saved queue is not modified.
    BEDLAM_RUNTIME_START_DELAY
        Seconds to wait for Editor initialization before starting MRQ.

The Slate post-tick callback observes the PIE game world after each engine
tick. MRQ normally advances temporal samples on separate engine ticks, but UE
5.3 does not expose every Movie Pipeline temporal-sample field to Python.
Consequently, tick_in_output_frame is an observed tick ordinal, not a promised
MRQ temporal-sample index. The CSV also records all MoviePipelineLibrary timing
values exposed by the installed engine.
"""

import csv
import datetime
import os
import traceback

import unreal


QUEUE_ASSET = "/Game/Bedlam/MovieRenderQueue/MRQ_Batch_00"
CAMERA_LABEL = "BE_CineCameraActor_Blueprint"
TARGET_LABEL = "BE_CameraTarget"
ROOT_LABEL = "BE_CameraRoot"
OPERATOR_LABEL = "BE_CameraOperator"

PROBE_DIR = os.environ.get(
    "BEDLAM_RUNTIME_PROBE_DIR",
    "/work/kelvin/unreal_logs/bedlam_camera_runtime",
)
RENDER_DIR = os.environ.get(
    "BEDLAM_RUNTIME_RENDER_DIR",
    "/work/kelvin/bedlam2/images/kaggle_eval/sim/"
    "outpost_ue53_runtime_probe",
)
START_DELAY_SECONDS = float(
    os.environ.get("BEDLAM_RUNTIME_START_DELAY", "15")
)
FORCE_LOOKAT = os.environ.get(
    "BEDLAM_RUNTIME_FORCE_LOOKAT", "0"
).lower() in ("1", "true", "yes", "on")
TICK_GROUP_FIX = os.environ.get(
    "BEDLAM_RUNTIME_TICK_GROUP_FIX", "0"
).lower() in ("1", "true", "yes", "on")
TICK_PREREQUISITE_FIX = os.environ.get(
    "BEDLAM_RUNTIME_TICK_PREREQUISITE_FIX", "0"
).lower() in ("1", "true", "yes", "on")
RESTORE_UNBAKED = os.environ.get(
    "BEDLAM_RUNTIME_RESTORE_UNBAKED", "0"
).lower() in ("1", "true", "yes", "on")
SEQUENCE_OVERRIDE = os.environ.get(
    "BEDLAM_RUNTIME_SEQUENCE_OVERRIDE", ""
)
CUSTOM_START_FRAME = os.environ.get("BEDLAM_RUNTIME_START_FRAME", "")
CUSTOM_END_FRAME = os.environ.get("BEDLAM_RUNTIME_END_FRAME", "")
JOB_LIMIT = int(os.environ.get("BEDLAM_RUNTIME_JOB_LIMIT", "0"))
PRESERVE_BEDLAM_LAYOUT = os.environ.get(
    "BEDLAM_RUNTIME_PRESERVE_BEDLAM_LAYOUT", "0"
).lower() in ("1", "true", "yes", "on")
IMAGE_SPATIAL_SAMPLES = int(os.environ.get(
    "BEDLAM_RUNTIME_IMAGE_SPATIAL_SAMPLES", "0"
))
IMAGE_TEMPORAL_SAMPLES = int(os.environ.get(
    "BEDLAM_RUNTIME_IMAGE_TEMPORAL_SAMPLES", "0"
))
WRITE_DONE_MARKERS = os.environ.get(
    "BEDLAM_RUNTIME_WRITE_DONE_MARKERS", "0"
).lower() in ("1", "true", "yes", "on")

RUN_ID = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_PATH = os.path.join(PROBE_DIR, f"runtime_camera_{RUN_ID}.csv")


FIELDNAMES = [
    "sample_index",
    "engine_frame",
    "world_time_seconds",
    "real_time_seconds",
    "delta_seconds",
    "pipeline_state",
    "job_name",
    "shot_name",
    "output_frame_index",
    "total_output_frame_count",
    "tick_in_output_frame",
    "master_frame_number",
    "master_timecode",
    "shot_frame_number",
    "shot_timecode",
    "camera_name",
    "force_lookat",
    "tick_group_fix",
    "tick_prerequisite_fix",
    "pre_force_pitch",
    "pre_force_yaw",
    "pre_force_roll",
    "forced_pitch",
    "forced_yaw",
    "forced_roll",
    "force_succeeded",
    "camera_x",
    "camera_y",
    "camera_z",
    "camera_pitch",
    "camera_yaw",
    "camera_roll",
    "camera_quat_x",
    "camera_quat_y",
    "camera_quat_z",
    "camera_quat_w",
    "component_x",
    "component_y",
    "component_z",
    "component_pitch",
    "component_yaw",
    "component_roll",
    "component_quat_x",
    "component_quat_y",
    "component_quat_z",
    "component_quat_w",
    "target_x",
    "target_y",
    "target_z",
    "target_parent",
    "target_socket",
    "lookat_enabled",
    "actor_to_track",
    "root_x",
    "root_y",
    "root_z",
    "root_pitch",
    "root_yaw",
    "root_roll",
    "operator_x",
    "operator_y",
    "operator_z",
    "operator_pitch",
    "operator_yaw",
    "operator_roll",
    "follow_enabled",
    "player_camera_manager",
    "view_target",
    "pov_x",
    "pov_y",
    "pov_z",
    "pov_pitch",
    "pov_yaw",
    "pov_roll",
    "camera_vs_component_rotation_deg",
    "component_vs_pov_rotation_deg",
    "error",
]


_executor = None
_tick_handle = None
_started = False
_start_real_time = None
_csv_file = None
_writer = None
_sample_index = 0
_last_output_key = None
_tick_in_output_frame = -1
_reported_runtime_api = False
_cached_world = None
_cached_actors = {}
_configured_camera = None
_configured_controller = None
_expected_jobs_by_sequence = {}
_finished_jobs_by_sequence = {}


def safe_call(obj, name, *args):
    if obj is None:
        return None
    try:
        return getattr(obj, name)(*args)
    except Exception:
        return None


def safe_property(obj, *names):
    if obj is None:
        return None
    for name in names:
        try:
            return obj.get_editor_property(name)
        except Exception:
            pass
    return None


def object_name(obj):
    if obj is None:
        return ""
    for function_name in ("get_actor_label", "get_name", "get_path_name"):
        value = safe_call(obj, function_name)
        if value is not None:
            return str(value)
    return str(obj)


def value_text(value):
    if value is None:
        return ""
    for function_name in ("to_string", "export_text"):
        result = safe_call(value, function_name)
        if result is not None:
            return str(result)
    return str(value)


def get_sequence_base_name(job_name):
    if job_name.endswith("_exr_depth"):
        return job_name[:-10]
    if job_name.endswith("_exr"):
        return job_name[:-4]
    return job_name


def vec_values(value):
    if value is None:
        return ("", "", "")
    return (float(value.x), float(value.y), float(value.z))


def rot_values(value):
    if value is None:
        return ("", "", "")
    return (float(value.pitch), float(value.yaw), float(value.roll))


def quat_values(rotation):
    if rotation is None:
        return ("", "", "", "")
    quat = safe_call(rotation, "quaternion")
    if quat is None:
        return ("", "", "", "")
    return (
        float(quat.x),
        float(quat.y),
        float(quat.z),
        float(quat.w),
    )


def angle_difference(a, b):
    delta = float(a) - float(b)
    return abs((delta + 180.0) % 360.0 - 180.0)


def rotation_difference(a, b):
    if a is None or b is None:
        return ""
    return max(
        angle_difference(a.pitch, b.pitch),
        angle_difference(a.yaw, b.yaw),
        angle_difference(a.roll, b.roll),
    )


def component_location(component):
    for name in ("get_world_location", "get_component_location"):
        value = safe_call(component, name)
        if value is not None:
            return value
    return None


def component_rotation(component):
    for name in ("get_world_rotation", "get_component_rotation"):
        value = safe_call(component, name)
        if value is not None:
            return value
    return None


def get_camera_component(camera):
    component = safe_call(camera, "get_cine_camera_component")
    if component is not None:
        return component
    return safe_call(
        camera,
        "get_component_by_class",
        unreal.CineCameraComponent,
    )


def force_camera_lookat(camera, target):
    """Persist the target-facing rotation instead of relying on GetCameraView."""
    if not FORCE_LOOKAT or camera is None or target is None:
        return None, None

    camera_location = safe_call(camera, "get_actor_location")
    target_location = safe_call(target, "get_actor_location")
    if camera_location is None or target_location is None:
        return None, False

    rotation = safe_call(
        unreal.MathLibrary,
        "find_look_at_rotation",
        camera_location,
        target_location,
    )
    if rotation is None:
        return None, False

    # Turn off the transient CineCameraActor GetCameraView modifier. Otherwise
    # the experiment would have two independent mechanisms driving rotation.
    settings = safe_property(camera, "lookat_tracking_settings")
    if settings is not None:
        try:
            settings.set_editor_property("enable_look_at_tracking", False)
            camera.set_editor_property("lookat_tracking_settings", settings)
        except Exception:
            pass

    succeeded = safe_call(camera, "set_actor_rotation", rotation, False)
    return rotation, succeeded


def get_game_world():
    editor_subsystem = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    )
    return safe_call(editor_subsystem, "get_game_world")


def runtime_actors(world):
    if world is None:
        return []
    actors = safe_call(
        unreal.GameplayStatics,
        "get_all_actors_of_class",
        world,
        unreal.Actor,
    )
    return list(actors) if actors else []


def find_runtime_actor(actors, label):
    exact = []
    partial = []
    for actor in actors:
        actor_label = object_name(actor)
        actor_name = str(safe_call(actor, "get_name") or "")
        if actor_label == label or actor_name == label:
            exact.append(actor)
        elif label in actor_label or label in actor_name:
            partial.append(actor)
    candidates = exact or partial
    return candidates[0] if candidates else None


def get_runtime_probe_actors(world):
    global _cached_world
    global _cached_actors
    global _configured_camera
    global _configured_controller

    if world != _cached_world:
        actors = runtime_actors(world)
        _cached_world = world
        _cached_actors = {
            "camera": find_runtime_actor(actors, CAMERA_LABEL),
            "target": find_runtime_actor(actors, TARGET_LABEL),
            "root": find_runtime_actor(actors, ROOT_LABEL),
            "operator": find_runtime_actor(actors, OPERATOR_LABEL),
        }

    camera = _cached_actors.get("camera")
    if (
        TICK_GROUP_FIX
        and camera is not None
        and camera != _configured_camera
    ):
        # Sequencer restores the keyed base transform during its evaluation.
        # Run ACineCameraActor::Tick in the final world tick group so its native
        # look-at pass deterministically wins before MRQ obtains the view.
        camera.set_tick_group(
            unreal.TickingGroup.TG_POST_UPDATE_WORK
        )
        _configured_camera = camera
        unreal.log_warning(
            "[RUNTIME_PROBE] Camera tick group set to "
            "TG_POST_UPDATE_WORK"
        )

    if TICK_PREREQUISITE_FIX and camera is not None:
        controller = safe_call(
            unreal.GameplayStatics,
            "get_player_controller",
            world,
            0,
        )
        if controller is not None and controller != _configured_controller:
            # Match the confirmed-correct UE 5.4 render setup: the
            # PlayerController ticks first, then ACineCameraActor applies its
            # look-at tracking state.
            camera.add_tick_prerequisite_actor(controller)
            _configured_controller = controller
            unreal.log_warning(
                "[RUNTIME_PROBE] Added PlayerController -> camera "
                "tick prerequisite"
            )
    return _cached_actors


def get_active_pipeline():
    subsystem = unreal.get_editor_subsystem(
        unreal.MoviePipelineQueueSubsystem
    )
    executor = safe_call(subsystem, "get_active_executor")
    if executor is None:
        executor = _executor
    for name in (
        "get_active_movie_pipeline",
        "get_current_pipeline",
        "get_pipeline",
    ):
        pipeline = safe_call(executor, name)
        if pipeline is not None:
            return pipeline
    return safe_property(
        executor,
        "active_movie_pipeline",
        "current_pipeline",
    )


def pipeline_library_value(name, pipeline):
    if pipeline is None:
        return None
    return safe_call(unreal.MoviePipelineLibrary, name, pipeline)


def segment_metrics(pipeline):
    metrics = pipeline_library_value(
        "get_current_segment_state",
        pipeline,
    )
    output_index = safe_property(
        metrics,
        "output_frame_index",
    )
    total_count = safe_property(
        metrics,
        "total_output_frame_count",
    )
    return metrics, output_index, total_count


def active_job_name(pipeline):
    value = pipeline_library_value("get_job_name", pipeline)
    if value is not None:
        return str(value)
    job = safe_call(pipeline, "get_current_job")
    return str(safe_property(job, "job_name") or "")


def player_camera_values(world):
    controller = safe_call(
        unreal.GameplayStatics,
        "get_player_controller",
        world,
        0,
    )
    manager = safe_property(controller, "player_camera_manager")
    if manager is None:
        manager = safe_call(controller, "get_player_camera_manager")
    location = safe_call(manager, "get_camera_location")
    rotation = safe_call(manager, "get_camera_rotation")
    view_target = safe_call(manager, "get_view_target")
    return manager, view_target, location, rotation


def write_runtime_sample(delta_seconds):
    global _sample_index
    global _last_output_key
    global _tick_in_output_frame
    global _reported_runtime_api

    world = get_game_world()
    if world is None:
        return

    actors = get_runtime_probe_actors(world)
    camera = actors.get("camera")
    target = actors.get("target")
    root = actors.get("root")
    operator = actors.get("operator")

    # Do not write Editor ticks before the runtime level/camera exists.
    if camera is None:
        return

    pipeline = get_active_pipeline()
    metrics, output_index, total_count = segment_metrics(pipeline)
    job_name = active_job_name(pipeline)

    shot_name = pipeline_library_value(
        "get_current_shot_name",
        pipeline,
    )
    master_frame = pipeline_library_value(
        "get_master_frame_number",
        pipeline,
    )
    master_timecode = pipeline_library_value(
        "get_master_timecode",
        pipeline,
    )
    shot_frame = pipeline_library_value(
        "get_current_shot_frame_number",
        pipeline,
    )
    shot_timecode = pipeline_library_value(
        "get_current_shot_timecode",
        pipeline,
    )

    output_key = (job_name, value_text(shot_name), output_index)
    if output_key == _last_output_key:
        _tick_in_output_frame += 1
    else:
        _last_output_key = output_key
        _tick_in_output_frame = 0

    camera_component = get_camera_component(camera)
    camera_loc = safe_call(camera, "get_actor_location")
    pre_force_rot = safe_call(camera, "get_actor_rotation")
    forced_rot, force_succeeded = force_camera_lookat(camera, target)
    camera_rot = safe_call(camera, "get_actor_rotation")
    component_loc = component_location(camera_component)
    component_rot = component_rotation(camera_component)

    target_loc = safe_call(target, "get_actor_location")
    target_parent = safe_call(target, "get_attach_parent_actor")
    target_socket = safe_call(
        target,
        "get_attach_parent_socket_name",
    )

    root_loc = safe_call(root, "get_actor_location")
    root_rot = safe_call(root, "get_actor_rotation")
    operator_loc = safe_call(operator, "get_actor_location")
    operator_rot = safe_call(operator, "get_actor_rotation")

    settings = safe_property(
        camera,
        "lookat_tracking_settings",
    )
    lookat_enabled = safe_property(
        settings,
        "enable_look_at_tracking",
    )
    actor_to_track = safe_property(settings, "actor_to_track")
    follow_enabled = safe_property(
        operator,
        "enable_follow_camera",
        "EnableFollowCamera",
    )

    manager, view_target, pov_loc, pov_rot = player_camera_values(world)

    camera_xyz = vec_values(camera_loc)
    pre_force_rpy = rot_values(pre_force_rot)
    forced_rpy = rot_values(forced_rot)
    camera_rpy = rot_values(camera_rot)
    camera_quat = quat_values(camera_rot)
    component_xyz = vec_values(component_loc)
    component_rpy = rot_values(component_rot)
    component_quat = quat_values(component_rot)
    target_xyz = vec_values(target_loc)
    root_xyz = vec_values(root_loc)
    root_rpy = rot_values(root_rot)
    operator_xyz = vec_values(operator_loc)
    operator_rpy = rot_values(operator_rot)
    pov_xyz = vec_values(pov_loc)
    pov_rpy = rot_values(pov_rot)

    engine_frame = safe_call(
        unreal.SystemLibrary,
        "get_frame_count",
    )
    world_time = safe_call(
        unreal.GameplayStatics,
        "get_time_seconds",
        world,
    )
    real_time = safe_call(
        unreal.GameplayStatics,
        "get_real_time_seconds",
        world,
    )
    pipeline_state = safe_call(pipeline, "get_pipeline_state")

    row = {
        "sample_index": _sample_index,
        "engine_frame": engine_frame,
        "world_time_seconds": world_time,
        "real_time_seconds": real_time,
        "delta_seconds": delta_seconds,
        "pipeline_state": value_text(pipeline_state),
        "job_name": job_name,
        "shot_name": value_text(shot_name),
        "output_frame_index": output_index,
        "total_output_frame_count": total_count,
        "tick_in_output_frame": _tick_in_output_frame,
        "master_frame_number": value_text(master_frame),
        "master_timecode": value_text(master_timecode),
        "shot_frame_number": value_text(shot_frame),
        "shot_timecode": value_text(shot_timecode),
        "camera_name": object_name(camera),
        "force_lookat": FORCE_LOOKAT,
        "tick_group_fix": TICK_GROUP_FIX,
        "tick_prerequisite_fix": TICK_PREREQUISITE_FIX,
        "pre_force_pitch": pre_force_rpy[0],
        "pre_force_yaw": pre_force_rpy[1],
        "pre_force_roll": pre_force_rpy[2],
        "forced_pitch": forced_rpy[0],
        "forced_yaw": forced_rpy[1],
        "forced_roll": forced_rpy[2],
        "force_succeeded": force_succeeded,
        "camera_x": camera_xyz[0],
        "camera_y": camera_xyz[1],
        "camera_z": camera_xyz[2],
        "camera_pitch": camera_rpy[0],
        "camera_yaw": camera_rpy[1],
        "camera_roll": camera_rpy[2],
        "camera_quat_x": camera_quat[0],
        "camera_quat_y": camera_quat[1],
        "camera_quat_z": camera_quat[2],
        "camera_quat_w": camera_quat[3],
        "component_x": component_xyz[0],
        "component_y": component_xyz[1],
        "component_z": component_xyz[2],
        "component_pitch": component_rpy[0],
        "component_yaw": component_rpy[1],
        "component_roll": component_rpy[2],
        "component_quat_x": component_quat[0],
        "component_quat_y": component_quat[1],
        "component_quat_z": component_quat[2],
        "component_quat_w": component_quat[3],
        "target_x": target_xyz[0],
        "target_y": target_xyz[1],
        "target_z": target_xyz[2],
        "target_parent": object_name(target_parent),
        "target_socket": value_text(target_socket),
        "lookat_enabled": lookat_enabled,
        "actor_to_track": object_name(actor_to_track),
        "root_x": root_xyz[0],
        "root_y": root_xyz[1],
        "root_z": root_xyz[2],
        "root_pitch": root_rpy[0],
        "root_yaw": root_rpy[1],
        "root_roll": root_rpy[2],
        "operator_x": operator_xyz[0],
        "operator_y": operator_xyz[1],
        "operator_z": operator_xyz[2],
        "operator_pitch": operator_rpy[0],
        "operator_yaw": operator_rpy[1],
        "operator_roll": operator_rpy[2],
        "follow_enabled": follow_enabled,
        "player_camera_manager": object_name(manager),
        "view_target": object_name(view_target),
        "pov_x": pov_xyz[0],
        "pov_y": pov_xyz[1],
        "pov_z": pov_xyz[2],
        "pov_pitch": pov_rpy[0],
        "pov_yaw": pov_rpy[1],
        "pov_roll": pov_rpy[2],
        "camera_vs_component_rotation_deg": rotation_difference(
            camera_rot,
            component_rot,
        ),
        "component_vs_pov_rotation_deg": rotation_difference(
            component_rot,
            pov_rot,
        ),
        "error": "",
    }
    _writer.writerow(row)
    _sample_index += 1
    # Avoid a synchronous parallel-filesystem flush on every temporal tick;
    # still bound potential data loss if Unreal crashes.
    if _sample_index % 32 == 0:
        _csv_file.flush()

    if not _reported_runtime_api:
        _reported_runtime_api = True
        unreal.log_warning(
            "[RUNTIME_PROBE] First runtime row: "
            f"job={job_name}, output_frame={output_index}, "
            f"shot_frame={value_text(shot_frame)}, "
            f"camera={object_name(camera)}, "
            f"player_camera_manager={object_name(manager)}, "
            f"csv={CSV_PATH}"
        )


def unregister_tick():
    global _tick_handle
    if _tick_handle is not None:
        try:
            unreal.unregister_slate_post_tick_callback(_tick_handle)
        except Exception:
            pass
        _tick_handle = None


def close_csv():
    global _csv_file
    global _writer
    if _csv_file is not None:
        try:
            _csv_file.flush()
            _csv_file.close()
        except Exception:
            pass
    _csv_file = None
    _writer = None


def restore_unbaked_sequence_state():
    """Undo the Windows bake transiently; never save the modified asset."""
    if not RESTORE_UNBAKED:
        return

    sequence = unreal.load_asset(
        "/Game/Bedlam/LevelSequences/seq_000000_0"
    )
    if sequence is None:
        raise RuntimeError("Could not load sequence for transient restore")

    camera_binding = None
    for binding in sequence.get_bindings():
        if str(binding.get_display_name()) == CAMERA_LABEL:
            camera_binding = binding
            break
    if camera_binding is None:
        raise RuntimeError("Could not find camera binding for transient restore")

    transform_sections = []
    lookat_channel = None
    for track in camera_binding.get_tracks():
        class_name = track.get_class().get_name()
        sections = track.get_sections()
        if class_name == "MovieScene3DTransformTrack" and sections:
            transform_sections.append(sections[0])
        if str(track.get_display_name()) == "Enable Look at Tracking":
            if sections:
                channels = sections[0].get_all_channels()
                if channels:
                    lookat_channel = channels[0]

    if len(transform_sections) < 2 or lookat_channel is None:
        raise RuntimeError(
            "Expected original+baked transform sections and look-at channel"
        )

    # The first section is the original sparse/local track; the last is the
    # dense world-space bake created on Windows.
    transform_sections[0].set_is_active(True)
    for section in transform_sections[1:]:
        section.set_is_active(False)
    lookat_channel.set_default(True)

    unreal.log_warning(
        "[RUNTIME_PROBE] Restored original camera transform/look-at "
        "transiently; asset will not be saved"
    )


def quit_editor():
    unreal.log_flush()
    unreal.SystemLibrary.execute_console_command(None, "QUIT_EDITOR")


def write_sequence_done_marker(sequence_name):
    marker_dir = os.path.join(RENDER_DIR, "post_ready")
    os.makedirs(marker_dir, exist_ok=True)
    marker_path = os.path.join(marker_dir, f"{sequence_name}.done")
    expected_jobs = sorted(
        _expected_jobs_by_sequence.get(sequence_name, set())
    )
    with open(marker_path, "w", encoding="utf-8") as marker_file:
        marker_file.write("status=done\n")
        marker_file.write(f"sequence={sequence_name}\n")
        marker_file.write(f"jobs={','.join(expected_jobs)}\n")
    unreal.log_warning(
        f"[RUNTIME_PROBE] Wrote BEDLAM done marker: {marker_path}"
    )


def on_job_finished(job, success):
    job_name = str(safe_property(job, "job_name"))
    sequence_name = get_sequence_base_name(job_name)
    unreal.log_warning(
        "[RUNTIME_PROBE] Job finished: "
        f"name={job_name}, success={success}, "
        f"rows={_sample_index}"
    )
    if not success or not WRITE_DONE_MARKERS:
        return

    finished_jobs = _finished_jobs_by_sequence.setdefault(
        sequence_name, set()
    )
    finished_jobs.add(job_name)
    expected_jobs = _expected_jobs_by_sequence.get(sequence_name, set())
    if expected_jobs and expected_jobs.issubset(finished_jobs):
        write_sequence_done_marker(sequence_name)


def on_queue_finished(executor, success):
    global _executor
    unreal.log_warning(
        "[RUNTIME_PROBE] Queue finished: "
        f"success={success}, rows={_sample_index}, csv={CSV_PATH}, "
        f"render_dir={RENDER_DIR}"
    )
    _executor = None
    unregister_tick()
    close_csv()
    quit_editor()


def start_render():
    global _executor
    global _csv_file
    global _writer
    global _expected_jobs_by_sequence
    global _finished_jobs_by_sequence

    os.makedirs(PROBE_DIR, exist_ok=True)
    os.makedirs(RENDER_DIR, exist_ok=True)
    restore_unbaked_sequence_state()

    _csv_file = open(CSV_PATH, "w", newline="")
    _writer = csv.DictWriter(_csv_file, fieldnames=FIELDNAMES)
    _writer.writeheader()
    _csv_file.flush()

    saved_queue = unreal.load_asset(QUEUE_ASSET)
    if saved_queue is None:
        raise RuntimeError(f"Could not load queue: {QUEUE_ASSET}")

    subsystem = unreal.get_editor_subsystem(
        unreal.MoviePipelineQueueSubsystem
    )
    if subsystem is None:
        raise RuntimeError("MoviePipelineQueueSubsystem is unavailable")

    loaded = subsystem.load_queue(
        saved_queue,
        prompt_on_replacing_dirty_queue=False,
    )
    if not loaded:
        raise RuntimeError("Failed to load the saved MRQ queue")

    jobs = subsystem.get_queue().get_jobs()
    if not jobs:
        raise RuntimeError("The saved MRQ queue contains no jobs")

    if JOB_LIMIT > 0:
        queue = subsystem.get_queue()
        for job in list(jobs[JOB_LIMIT:]):
            queue.delete_job(job)
        jobs = queue.get_jobs()

    _expected_jobs_by_sequence = {}
    _finished_jobs_by_sequence = {}
    for index, job in enumerate(jobs):
        if SEQUENCE_OVERRIDE:
            job.set_editor_property(
                "sequence",
                unreal.SoftObjectPath(SEQUENCE_OVERRIDE),
            )
        config = job.get_configuration()
        antialiasing = config.find_or_add_setting_by_class(
            unreal.MoviePipelineAntiAliasingSetting
        )
        job_name = str(safe_property(job, "job_name"))
        sequence_name = get_sequence_base_name(job_name)
        _expected_jobs_by_sequence.setdefault(
            sequence_name, set()
        ).add(job_name)
        _finished_jobs_by_sequence.setdefault(sequence_name, set())
        if (
            IMAGE_SPATIAL_SAMPLES > 0
            and job_name.endswith("_exr")
            and not job_name.endswith("_exr_depth")
        ):
            antialiasing.set_editor_property(
                "spatial_sample_count", IMAGE_SPATIAL_SAMPLES
            )
        if (
            IMAGE_TEMPORAL_SAMPLES > 0
            and job_name.endswith("_exr")
            and not job_name.endswith("_exr_depth")
        ):
            antialiasing.set_editor_property(
                "temporal_sample_count", IMAGE_TEMPORAL_SAMPLES
            )
        output = config.find_or_add_setting_by_class(
            unreal.MoviePipelineOutputSetting
        )
        directory = unreal.DirectoryPath()
        if PRESERVE_BEDLAM_LAYOUT:
            pass_directory = (
                "exr_depth" if job_name.endswith("_exr_depth")
                else "exr_image" if job_name.endswith("_exr")
                else "png"
            )
            render_path = os.path.join(
                RENDER_DIR, pass_directory, sequence_name
            )
        else:
            render_path = RENDER_DIR
        directory.set_editor_property("path", render_path)
        output.set_editor_property("output_directory", directory)
        if CUSTOM_START_FRAME or CUSTOM_END_FRAME:
            output.set_editor_property("use_custom_playback_range", True)
            if CUSTOM_START_FRAME:
                output.set_editor_property(
                    "custom_start_frame", int(CUSTOM_START_FRAME)
                )
            if CUSTOM_END_FRAME:
                output.set_editor_property(
                    "custom_end_frame", int(CUSTOM_END_FRAME)
                )
        unreal.log_warning(
            "[RUNTIME_PROBE] Queue job "
            f"{index}: name={safe_property(job, 'job_name')}, "
            f"sequence={value_text(safe_property(job, 'sequence'))}, "
            f"spatial_samples={safe_property(antialiasing, 'spatial_sample_count')}, "
            f"temporal_samples={safe_property(antialiasing, 'temporal_sample_count')}, "
            f"output={render_path}"
        )

    unreal.log_warning(
        "[RUNTIME_PROBE] Starting MoviePipelinePIEExecutor"
    )
    _executor = subsystem.render_queue_with_executor(
        unreal.MoviePipelinePIEExecutor
    )
    if _executor is None:
        raise RuntimeError("Failed to create MoviePipelinePIEExecutor")

    _executor.on_executor_finished_delegate.add_callable_unique(
        on_queue_finished
    )
    _executor.on_individual_job_finished_delegate.add_callable_unique(
        on_job_finished
    )


def tick(delta_seconds):
    global _started
    try:
        if not _started:
            now = safe_call(
                unreal.SystemLibrary,
                "get_game_time_in_seconds",
                None,
            )
            # SystemLibrary time may be unavailable outside a world; use the
            # monotonic start value maintained by the Editor tick deltas.
            tick.elapsed = getattr(tick, "elapsed", 0.0) + delta_seconds
            if tick.elapsed < START_DELAY_SECONDS:
                return
            _started = True
            start_render()
            return

        write_runtime_sample(delta_seconds)
    except Exception:
        error = traceback.format_exc()
        unreal.log_error("[RUNTIME_PROBE] Tick failed:\n" + error)
        if _writer is not None:
            try:
                _writer.writerow({"error": error})
                _csv_file.flush()
            except Exception:
                pass
        unregister_tick()
        close_csv()
        quit_editor()


try:
    _tick_handle = unreal.register_slate_post_tick_callback(tick)
    unreal.log_warning(
        "[RUNTIME_PROBE] Loaded; "
        f"waiting {START_DELAY_SECONDS:.1f}s before PIE MRQ. "
        f"force_lookat={FORCE_LOOKAT}, "
        f"tick_group_fix={TICK_GROUP_FIX}, "
        f"tick_prerequisite_fix={TICK_PREREQUISITE_FIX}, "
        f"csv={CSV_PATH}, render_dir={RENDER_DIR}"
    )
except Exception:
    unreal.log_error(
        "[RUNTIME_PROBE] Startup failed:\n" + traceback.format_exc()
    )
    unregister_tick()
    close_csv()
    quit_editor()
    raise
