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
SEQUENCE_ROOT = "/Game/Bedlam/LevelSequences"
STATUS_PATH = os.path.abspath(os.environ["BEDLAM_LEVEL_SEQUENCE_STATUS_PATH"])
START_DELAY_SECONDS = float(os.environ.get("BEDLAM_LEVEL_SEQUENCE_START_DELAY", "15"))
START_TIMEOUT_SECONDS = float(os.environ.get("BEDLAM_LEVEL_SEQUENCE_START_TIMEOUT", "120"))
EXPECTED_MAP = os.environ.get("BEDLAM_LEVEL_SEQUENCE_EXPECTED_MAP", "").split(".", 1)[0]
EXPORT_GEOMETRY_CACHE_OBJ = os.environ.get(
    "BEDLAM_LEVEL_SEQUENCE_EXPORT_GEOMETRY_CACHE_OBJ", "0"
).lower() in ("1", "true", "yes", "on")


def write_status(status, **values):
    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
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
    if not names:
        raise RuntimeError(f"CSV contains no Group sequence rows: {CSV_PATH}")
    duplicates = sorted(name for name in set(names) if names.count(name) > 1)
    if duplicates:
        raise RuntimeError(f"CSV contains duplicate sequence names: {duplicates}")
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
        return False, {"current_map": "", "labels": []}
    world = unreal.get_editor_subsystem(
        unreal.UnrealEditorSubsystem
    ).get_editor_world()
    levels = unreal.EditorLevelUtils.get_levels(world) if world is not None else []
    current_map = ""
    if levels:
        current_map = str(
            unreal.SystemLibrary.get_path_name(
                unreal.SystemLibrary.get_outer_object(levels[0])
            )
        ).split(".", 1)[0]

    labels = set()
    has_camera = False
    for actor in actors:
        try:
            labels.add(str(actor.get_actor_label()))
            if isinstance(actor, unreal.CineCameraActor):
                has_camera = True
        except Exception:
            continue
    correct_map = not EXPECTED_MAP or current_map == EXPECTED_MAP
    return (
        correct_map and has_camera and "BE_CameraTarget" in labels,
        {"current_map": current_map, "labels": sorted(labels)},
    )


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
            generator_source = script_file.read()
            export_setting = "EXPORT_GEOMETRY_CACHE_OBJ = True"
            if generator_source.count(export_setting) != 1:
                raise RuntimeError(
                    "Could not uniquely configure geometry-cache OBJ export in "
                    f"{GENERATOR_SCRIPT}"
                )
            generator_source = generator_source.replace(
                export_setting,
                f"EXPORT_GEOMETRY_CACHE_OBJ = {EXPORT_GEOMETRY_CACHE_OBJ!r}",
                1,
            )
            try:
                exec(compile(generator_source, GENERATOR_SCRIPT, "exec"), namespace)
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
        str(path).rsplit("/", 1)[-1].split(".", 1)[0]
        for path in generated_paths
        if unreal.EditorAssetLibrary.find_asset_data(path).get_class()
        == unreal.LevelSequence.static_class()
    )
    missing = sorted(set(expected_names) - set(generated_names))
    extra = sorted(set(generated_names) - set(expected_names))
    success = not missing
    write_status(
        "complete" if success else "failed",
        expected_sequences=expected_names,
        generated_sequences=generated_names,
        missing_sequences=missing,
        extra_sequences=extra,
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
    ready, readiness = required_map_actors_ready()
    if elapsed < START_DELAY_SECONDS or not ready:
        if elapsed < START_TIMEOUT_SECONDS:
            return
        message = (
            f"Timed out waiting for CineCameraActor and BE_CameraTarget after {elapsed:.1f}s; "
            f"current_map={readiness['current_map']}; "
            f"labels={readiness['labels'][:30]}"
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
    f"[linux-level-sequence-wrapper] waiting for map={EXPECTED_MAP or '<any>'} "
    f"and required actors; delay={START_DELAY_SECONDS:.1f}s"
)
