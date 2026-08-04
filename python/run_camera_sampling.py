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
START_DELAY = float(os.environ.get("BEDLAM_CAMERA_SAMPLING_START_DELAY", "15"))
TIMEOUT = float(os.environ.get("BEDLAM_CAMERA_SAMPLING_TIMEOUT", "7200"))
SEED_TEXT = os.environ.get("BEDLAM_CAMERA_SAMPLING_SEED", "").strip()
SEED = int(SEED_TEXT) if SEED_TEXT else None

started_at = time.monotonic()
state = {"handle": None, "started": False}


def quit_editor():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "QUIT_EDITOR")


def map_ready():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    labels = {str(actor.get_actor_label()) for actor in actors}
    return "BE_CameraTarget" in labels


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
            if elapsed < START_DELAY or not map_ready():
                if elapsed >= TIMEOUT:
                    raise RuntimeError("Timed out waiting for the map and BE_CameraTarget")
                return

            namespace = {"__name__": "bedlam_camera_sampling", "__file__": SAMPLER}
            with open(SAMPLER, encoding="utf-8") as script_file:
                exec(compile(script_file.read(), SAMPLER, "exec"), namespace)
            namespace["generate_validated_orbit_camera_animations_scheduled"](
                csv_path=CSV_PATH,
                output_csv_path=OUTPUT_CSV,
                output_json_path=OUTPUT_JSON,
                sequence_root=SEQUENCE_ROOT,
                num_cameras=2,
                seed=SEED,
                max_camera_attempts=1000,
                validation_samples="all",
                camera_collision_radius_cm=20.0,
                paired_initial_cameras=True,
                reuse_sequence_for_camera_pair=True,
                sequence_warmup_ticks=1,
                camera_motion_mode="random",
                camera_motion_family_weights={"orbit": 60, "dolly": 30, "static": 10},
                camera_motion_attempt_block_size=50,
                tick_delay_seconds=2.0,
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
            if len(completed) != 16:
                raise RuntimeError(f"Expected 16 completed cameras, found {len(completed)}")
            unreal.log(f"[linux-camera-wrapper] complete cameras={len(completed)}")
            unreal.unregister_slate_post_tick_callback(state["handle"])
            state["handle"] = None
            quit_editor()
        elif elapsed >= TIMEOUT:
            raise RuntimeError(f"Camera sampling timed out; completed={len(completed)} pending={len(pending)}")
    except BaseException as exc:
        unreal.log_error(f"[linux-camera-wrapper] failed: {exc}\n{traceback.format_exc()}")
        if state["handle"] is not None:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            state["handle"] = None
        quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal._linux_camera_sampling_handle = state["handle"]
unreal.log("[linux-camera-wrapper] waiting for map readiness")
