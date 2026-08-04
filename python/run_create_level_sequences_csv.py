"""Run BEDLAM create_level_sequences_csv.py with Linux paths, then exit UE."""

import csv
import json
import os
import sys
import time
import traceback

import unreal


CSV_PATH = os.path.abspath(os.environ["BEDLAM_LEVEL_SEQUENCE_CSV_PATH"])
OUTPUT_DIR = os.path.abspath(
    os.environ.get("BEDLAM_LEVEL_SEQUENCE_STATUS_DIR", os.path.dirname(CSV_PATH))
)
GENERATOR_SCRIPT = os.path.abspath(os.environ["BEDLAM_LEVEL_SEQUENCE_SCRIPT"])
CAMERA_MOVEMENT_TYPE = os.environ.get("BEDLAM_LEVEL_SEQUENCE_CAMERA_TYPE", "Default")
SEQUENCE_ROOT = os.environ.get("BEDLAM_LEVEL_SEQUENCE_ROOT", "/Game/Bedlam/LevelSequences")
STATUS_PATH = os.path.join(OUTPUT_DIR, "linux_level_sequence_status.json")
START_DELAY_SECONDS = float(os.environ.get("BEDLAM_LEVEL_SEQUENCE_START_DELAY", "15"))
START_TIMEOUT_SECONDS = float(os.environ.get("BEDLAM_LEVEL_SEQUENCE_START_TIMEOUT", "120"))


def write_status(status, **values):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    payload = {
        "status": status,
        "csv_path": CSV_PATH,
        "generator_script": GENERATOR_SCRIPT,
        "sequence_root": SEQUENCE_ROOT,
    }
    payload.update(values)
    with open(STATUS_PATH, "w", encoding="utf-8") as out_file:
        json.dump(payload, out_file, indent=2)


def source_sequence_names():
    names = []
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as in_file:
        for row in csv.DictReader(in_file):
            if row.get("Type") != "Group":
                continue
            config = {}
            for item in row.get("Comment", "").split(";"):
                if "=" in item:
                    key, value = item.split("=", 1)
                    config[key.strip()] = value.strip()
            if config.get("sequence_name"):
                names.append(config["sequence_name"])
    return names


def request_exit():
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    except Exception:
        world = None
    unreal.SystemLibrary.execute_console_command(world, "QUIT_EDITOR")


def required_map_actors_ready():
    try:
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    except Exception:
        return False, []
    labels = set()
    has_camera = False
    for actor in actors:
        try:
            labels.add(str(actor.get_actor_label()))
            if actor.static_class() == unreal.CineCameraActor.static_class():
                has_camera = True
        except Exception:
            continue
    return has_camera and "BE_CameraTarget" in labels, sorted(labels)


def run_generator():
    if not os.path.isfile(CSV_PATH):
        raise RuntimeError(f"CSV does not exist: {CSV_PATH}")
    if not os.path.isfile(GENERATOR_SCRIPT):
        raise RuntimeError(f"Generator does not exist: {GENERATOR_SCRIPT}")

    expected_names = source_sequence_names()
    write_status("running", expected_sequences=expected_names)
    namespace = {
        "__name__": "__main__",
        "__file__": GENERATOR_SCRIPT,
    }
    previous_argv = list(sys.argv)
    try:
        sys.argv = [GENERATOR_SCRIPT, CSV_PATH, CAMERA_MOVEMENT_TYPE]
        with open(GENERATOR_SCRIPT, encoding="utf-8") as script_file:
            try:
                exec(compile(script_file.read(), GENERATOR_SCRIPT, "exec"), namespace)
            except SystemExit as exc:
                # BEDLAM's command-line generator uses sys.exit(0) to report
                # normal completion. Preserve genuine non-zero failures, but
                # continue with the asset validation below on success.
                if exc.code not in (None, 0):
                    raise
                unreal.log(
                    "[linux-level-sequence-wrapper] "
                    "BEDLAM generator exited successfully with code 0"
                )
    finally:
        sys.argv = previous_argv

    generated_paths = list(
        unreal.EditorAssetLibrary.list_assets(SEQUENCE_ROOT, recursive=False, include_folder=False)
    )
    generated_names = sorted(
        str(path).rsplit("/", 1)[-1].split(".", 1)[0] for path in generated_paths
    )
    missing = sorted(set(expected_names) - set(generated_names))
    success = not missing and len(expected_names) == len(generated_names)
    write_status(
        "complete" if success else "failed",
        expected_sequences=expected_names,
        generated_sequences=generated_names,
        missing_sequences=missing,
    )
    unreal.log(
        f"[linux-level-sequence-wrapper] finished success={success} "
        f"generated={len(generated_names)} expected={len(expected_names)}"
    )


started_at = time.monotonic()
state = {"handle": None, "started": False}
write_status("waiting_for_map", start_delay_seconds=START_DELAY_SECONDS)


def start_when_ready(_delta_seconds):
    if state["started"]:
        return
    elapsed = time.monotonic() - started_at
    ready, labels = required_map_actors_ready()
    if elapsed < START_DELAY_SECONDS or not ready:
        if elapsed < START_TIMEOUT_SECONDS:
            return
        message = (
            f"Timed out waiting for CineCameraActor and BE_CameraTarget after {elapsed:.1f}s; "
            f"labels={labels[:30]}"
        )
        unreal.log_error(f"[linux-level-sequence-wrapper] {message}")
        write_status("failed", message=message)
        unreal.unregister_slate_post_tick_callback(state["handle"])
        state["handle"] = None
        request_exit()
        return

    state["started"] = True
    unreal.unregister_slate_post_tick_callback(state["handle"])
    state["handle"] = None
    unreal.log(
        f"[linux-level-sequence-wrapper] map ready after {elapsed:.1f}s; starting generator"
    )
    try:
        run_generator()
    except BaseException as exc:
        unreal.log_error(
            f"[linux-level-sequence-wrapper] failed: {exc}\n{traceback.format_exc()}"
        )
        write_status("failed", message=str(exc))
    finally:
        request_exit()


state["handle"] = unreal.register_slate_post_tick_callback(start_when_ready)
unreal._linux_level_sequence_start_handle = state["handle"]
unreal.log(
    f"[linux-level-sequence-wrapper] waiting for map actors; delay={START_DELAY_SECONDS:.1f}s"
)
