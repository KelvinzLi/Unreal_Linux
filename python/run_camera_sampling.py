"""Launch BEDLAM camera sampling after the editor map is ready, then exit."""

import json
import os
import time
import traceback

import unreal


SAMPLER = os.environ["BEDLAM_CAMERA_SAMPLING_SCRIPT"]
CSV_PATH = os.environ["BEDLAM_CAMERA_SAMPLING_CSV_PATH"]
OUTPUT_CSV = os.environ["BEDLAM_CAMERA_SAMPLING_OUTPUT_CSV"]
OUTPUT_JSON = os.environ["BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON"]
SEQUENCE_ROOT = os.environ.get("BEDLAM_CAMERA_SAMPLING_SEQUENCE_ROOT", "/Game/Bedlam/LevelSequences")
STATUS_PATH = os.path.abspath(os.environ["BEDLAM_CAMERA_SAMPLING_STATUS_PATH"])
EXPECTED_MAP = os.environ.get("BEDLAM_CAMERA_SAMPLING_EXPECTED_MAP", "").split(".", 1)[0]
START_DELAY = float(os.environ.get("BEDLAM_CAMERA_SAMPLING_START_DELAY", "15"))
START_TIMEOUT = float(os.environ.get("BEDLAM_CAMERA_SAMPLING_START_TIMEOUT", "180"))
TIMEOUT = float(os.environ.get("BEDLAM_CAMERA_SAMPLING_TIMEOUT", "7200"))
SEED_TEXT = os.environ.get("BEDLAM_CAMERA_SAMPLING_SEED", "").strip()
SEED = int(SEED_TEXT) if SEED_TEXT else None
PRESET = os.environ.get("BEDLAM_CAMERA_SAMPLING_PRESET", "random_pair").strip()

started_at = time.monotonic()
state = {"handle": None, "started": False, "sampler_namespace": None}


def write_status(status, **values):
    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
    payload = {
        "status": status,
        "csv_path": os.path.abspath(CSV_PATH),
        "output_csv_path": os.path.abspath(OUTPUT_CSV),
        "output_json_path": os.path.abspath(OUTPUT_JSON),
        "sequence_root": SEQUENCE_ROOT,
        "expected_map": EXPECTED_MAP,
        "preset": PRESET,
    }
    payload.update(values)
    temporary_path = STATUS_PATH + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2)
    os.replace(temporary_path, STATUS_PATH)


def quit_editor():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "QUIT_EDITOR")


def map_ready():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    labels = {str(actor.get_actor_label()) for actor in actors}
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    levels = unreal.EditorLevelUtils.get_levels(world) if world is not None else []
    current_map = ""
    if levels:
        current_map = str(
            unreal.SystemLibrary.get_path_name(
                unreal.SystemLibrary.get_outer_object(levels[0])
            )
        ).split(".", 1)[0]
    correct_map = not EXPECTED_MAP or current_map == EXPECTED_MAP
    ready = correct_map and "BE_CameraTarget" in labels
    return ready, current_map, sorted(labels)


def load_output():
    try:
        with open(OUTPUT_JSON, encoding="utf-8") as input_file:
            return json.load(input_file)
    except (OSError, ValueError):
        return None


def tick(_delta_seconds):
    elapsed = time.monotonic() - started_at
    try:
        if not state["started"]:
            ready, current_map, labels = map_ready()
            if elapsed < START_DELAY or not ready:
                if elapsed >= START_TIMEOUT:
                    raise RuntimeError(
                        "Timed out waiting for map={} and BE_CameraTarget; "
                        "current_map={} labels={}".format(
                            EXPECTED_MAP or "<any>", current_map, labels[:30]
                        )
                    )
                return

            write_status("running", current_map=current_map)
            namespace = {"__name__": "bedlam_camera_sampling", "__file__": SAMPLER}
            with open(SAMPLER, encoding="utf-8") as script_file:
                exec(compile(script_file.read(), SAMPLER, "exec"), namespace)
            state["sampler_namespace"] = namespace
            common_args = {
                "csv_path": CSV_PATH,
                "output_csv_path": OUTPUT_CSV,
                "output_json_path": OUTPUT_JSON,
                "sequence_root": SEQUENCE_ROOT,
                "seed": SEED,
            }
            if PRESET == "camera_placement_9":
                sampler_args = {
                    "max_camera_attempts": 4000,
                    "validation_samples": "all",
                    "camera_collision_radius_cm": 20.0,
                    "paired_initial_cameras": False,
                    "reuse_camera_pose_for_duplicate_modes": True,
                    "camera_motion_mode_list": [
                        "static_elevation_0",
                        "static_elevation_45",
                        "static_elevation_85",
                        "static_elevation_45",
                        "static_elevation_45",
                        "static_elevation_45",
                        "orbit_40-67_10-17_0-66",
                        "orbit_67-94_17-24_66-133",
                        "orbit_94-120_24-30_133-200",
                    ],
                    "camera_shake": "high",
                    "camera_shake_scale": [0.0, 0.0, 0.0, 5.0, 10.0, 15.0, 0.0, 0.0, 0.0],
                    "static_camera_shake_probability": 1.0,
                    "look_at_target": "cameraroot",
                    "hfov_range_deg": (60.0, 90.0),
                    "distance_range_cm": (400.0, 600.0),
                    "tick_delay_seconds": 2.0,
                }
            elif PRESET == "random_pair":
                sampler_args = {
                    "num_cameras": 2,
                    "max_camera_attempts": 1000,
                    "validation_samples": "all",
                    "camera_collision_radius_cm": 20.0,
                    "paired_initial_cameras": True,
                    "reuse_sequence_for_camera_pair": True,
                    "sequence_warmup_ticks": 1,
                    "camera_motion_mode": "random",
                    "camera_motion_family_weights": {"orbit": 60, "dolly": 30, "static": 10},
                    "camera_motion_attempt_block_size": 50,
                    "tick_delay_seconds": 2.0,
                }
            else:
                raise RuntimeError(f"Unknown BEDLAM camera sampling preset: {PRESET!r}")
            namespace["generate_validated_orbit_camera_animations_scheduled"](
                **common_args,
                **sampler_args,
            )
            state["started"] = True
            unreal.log("[linux-camera-wrapper] camera sampling started")
            return

        output = load_output()
        if not output:
            return
        info = output.get("info", {})
        pending = info.get("pending_sequences", [])
        completed = info.get("completed_sequences", [])
        errors = info.get("error_sequences", {})
        if not pending:
            if errors:
                raise RuntimeError(f"Camera sampling completed with errors: {errors}")
            if info.get("scheduler_failed"):
                raise RuntimeError("Camera sampling scheduler failed")
            if not completed:
                raise RuntimeError("Camera sampling produced no completed cameras")
            stop_sampler = state["sampler_namespace"].get(
                "stop_scheduled_validated_orbit_camera_generation"
            )
            if stop_sampler is not None:
                stop_sampler()
            write_status(
                "complete",
                completed_sequences=completed,
                completed_count=len(completed),
            )
            unreal.log(f"[linux-camera-wrapper] complete cameras={len(completed)}")
            unreal.unregister_slate_post_tick_callback(state["handle"])
            state["handle"] = None
            quit_editor()
        elif elapsed >= TIMEOUT:
            raise RuntimeError(f"Camera sampling timed out; completed={len(completed)} pending={len(pending)}")
    except BaseException as exc:
        unreal.log_error(f"[linux-camera-wrapper] failed: {exc}\n{traceback.format_exc()}")
        write_status("failed", message=str(exc))
        sampler_namespace = state.get("sampler_namespace")
        if sampler_namespace is not None:
            stop_sampler = sampler_namespace.get(
                "stop_scheduled_validated_orbit_camera_generation"
            )
            if stop_sampler is not None:
                try:
                    stop_sampler()
                except Exception:
                    pass
        if state["handle"] is not None:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            state["handle"] = None
        quit_editor()


write_status("waiting_for_map", start_delay_seconds=START_DELAY)
state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal._linux_camera_sampling_handle = state["handle"]
unreal.log("[linux-camera-wrapper] waiting for map readiness")
