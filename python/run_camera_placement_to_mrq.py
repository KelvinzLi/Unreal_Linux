"""Build validation sequences, sample cameras, then build final sequences and MRQ.

All stages run in one Unreal Editor session.  The existing Linux wrappers remain
the source of truth for each individual stage; this module only coordinates their
asynchronous completion callbacks and validates each hand-off.
"""

import csv
import json
import os
import shutil
import time
import traceback

import unreal


LEVEL_WRAPPER = os.path.abspath(os.environ["BEDLAM_WORKFLOW_LEVEL_WRAPPER"])
CAMERA_WRAPPER = os.path.abspath(os.environ["BEDLAM_WORKFLOW_CAMERA_WRAPPER"])
MRQ_WRAPPER = os.path.abspath(os.environ["BEDLAM_WORKFLOW_MRQ_WRAPPER"])
BASE_CSV = os.path.abspath(os.environ["BEDLAM_WORKFLOW_BASE_CSV"])
EXPANDED_CSV = os.path.abspath(os.environ["BEDLAM_CAMERA_SAMPLING_OUTPUT_CSV"])
FINAL_CSV = os.path.abspath(os.environ["BEDLAM_WORKFLOW_FINAL_CSV"])
CAMERA_JSON = os.path.abspath(os.environ["BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON"])
INITIAL_LEVEL_STATUS = os.path.abspath(
    os.environ["BEDLAM_WORKFLOW_INITIAL_LEVEL_STATUS"]
)
FINAL_LEVEL_STATUS = os.path.abspath(os.environ["BEDLAM_WORKFLOW_FINAL_LEVEL_STATUS"])
CAMERA_STATUS = os.path.abspath(os.environ["BEDLAM_CAMERA_SAMPLING_STATUS_PATH"])
MRQ_STATUS = os.path.abspath(os.environ["BEDLAM_MRQ_STATUS_PATH"])
WORKFLOW_STATUS = os.path.abspath(os.environ["BEDLAM_WORKFLOW_STATUS_PATH"])
EXPECTED_MAP = os.environ.get("BEDLAM_WORKFLOW_EXPECTED_MAP", "").split(".", 1)[0]
EXPECTED_BASE = int(os.environ["BEDLAM_WORKFLOW_EXPECTED_BASE_SEQUENCES"])
EXPECTED_FINAL = int(os.environ["BEDLAM_WORKFLOW_EXPECTED_FINAL_SEQUENCES"])
EXPECTED_JOBS = int(os.environ["BEDLAM_WORKFLOW_EXPECTED_MRQ_JOBS"])
START_TIMEOUT = float(os.environ.get("BEDLAM_WORKFLOW_START_TIMEOUT", "180"))
LEVEL_ROOT = "/Game/Bedlam/LevelSequences"
MRQ_ROOT = "/Game/Bedlam/MovieRenderQueue"

state = {"stage": "waiting_for_map", "handle": None, "started_at": time.monotonic()}
namespaces = {}


def atomic_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2)
    os.replace(temporary, path)


def write_workflow_status(status, **values):
    payload = {
        "status": status,
        "stage": state["stage"],
        "base_csv": BASE_CSV,
        "expanded_csv": EXPANDED_CSV,
        "final_csv": FINAL_CSV,
        "camera_json": CAMERA_JSON,
        "expected_base_sequences": EXPECTED_BASE,
        "expected_final_sequences": EXPECTED_FINAL,
        "expected_mrq_jobs": EXPECTED_JOBS,
    }
    payload.update(values)
    atomic_json(WORKFLOW_STATUS, payload)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as input_file:
            return json.load(input_file)
    except (OSError, ValueError):
        return {}


def group_names(path):
    with open(path, newline="", encoding="utf-8-sig") as input_file:
        names = []
        for row in csv.DictReader(input_file):
            if row.get("Type") != "Group":
                continue
            config = {}
            for item in row.get("Comment", "").split(";"):
                if "=" in item:
                    key, value = item.split("=", 1)
                    config[key.strip()] = value.strip()
            name = config.get("sequence_name")
            if not name:
                raise RuntimeError(f"Group row has no sequence_name in {path}")
            names.append(name)
    if len(names) != len(set(names)):
        raise RuntimeError(f"Duplicate sequence names in {path}")
    return names


def quit_editor():
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    except Exception:
        world = None
    unreal.SystemLibrary.execute_console_command(world, "QUIT_EDITOR")


def fail(stage, exc):
    state["stage"] = stage
    message = str(exc)
    unreal.log_error(
        f"[linux-camera-to-mrq] failed stage={stage}: {message}\n{traceback.format_exc()}"
    )
    write_workflow_status("failed", message=message)
    quit_editor()


def execute_wrapper(path, namespace_name):
    namespace = {"__name__": namespace_name, "__file__": path}
    with open(path, encoding="utf-8") as script_file:
        exec(compile(script_file.read(), path, "exec"), namespace)
    namespaces[namespace_name] = namespace
    setattr(unreal, "_linux_camera_to_mrq_" + namespace_name, namespace)
    return namespace


def asset_paths(root):
    return list(
        unreal.EditorAssetLibrary.list_assets(
            root, recursive=False, include_folder=False
        )
    )


def clear_generated_assets(root):
    paths = asset_paths(root)
    for path in paths:
        if not unreal.EditorAssetLibrary.delete_asset(path):
            raise RuntimeError(f"Could not delete generated asset: {path}")
    remaining = asset_paths(root)
    if remaining:
        raise RuntimeError(f"Generated assets remain under {root}: {remaining}")
    unreal.log(f"[linux-camera-to-mrq] cleared {len(paths)} assets under {root}")


def validate_level_status(path, expected_count):
    status = read_json(path)
    if status.get("status") != "complete":
        raise RuntimeError(f"Level Sequence stage is not complete: {path}: {status}")
    expected = list(status.get("expected_sequences") or [])
    missing = list(status.get("missing_sequences") or [])
    if len(expected) != expected_count or missing:
        raise RuntimeError(
            f"Invalid Level Sequence status: expected_count={len(expected)} "
            f"required={expected_count} missing={missing}"
        )
    return status


def start_initial_level_sequences():
    state["stage"] = "initial_level_sequences"
    write_workflow_status("running")
    os.environ["BEDLAM_LEVEL_SEQUENCE_CSV_PATH"] = BASE_CSV
    os.environ["BEDLAM_LEVEL_SEQUENCE_STATUS_PATH"] = INITIAL_LEVEL_STATUS
    os.environ["BEDLAM_LEVEL_SEQUENCE_START_DELAY"] = "0"
    namespace = execute_wrapper(LEVEL_WRAPPER, "initial_level_sequences")

    def completed():
        try:
            validate_level_status(INITIAL_LEVEL_STATUS, EXPECTED_BASE)
            start_camera_sampling()
        except BaseException as exc:
            fail("initial_level_sequences", exc)

    namespace["request_exit"] = completed


def start_camera_sampling():
    state["stage"] = "camera_sampling"
    write_workflow_status("running")
    namespace = execute_wrapper(CAMERA_WRAPPER, "camera_sampling")

    def completed():
        try:
            status = read_json(CAMERA_STATUS)
            if status.get("status") != "complete":
                raise RuntimeError(f"Camera sampling is not complete: {status}")
            names = group_names(EXPANDED_CSV)
            if len(names) != EXPECTED_FINAL:
                raise RuntimeError(
                    f"Expanded CSV contains {len(names)} sequences; "
                    f"expected {EXPECTED_FINAL}"
                )
            camera_output = read_json(CAMERA_JSON)
            info = camera_output.get("info", {})
            if info.get("pending_sequences") or info.get("error_sequences"):
                raise RuntimeError(
                    "Camera JSON is incomplete: pending={} errors={}".format(
                        info.get("pending_sequences"), info.get("error_sequences")
                    )
                )
            promote_csv_and_start_final_sequences()
        except BaseException as exc:
            fail("camera_sampling", exc)

    namespace["quit_editor"] = completed


def promote_csv_and_start_final_sequences():
    state["stage"] = "promote_multicamera_csv"
    write_workflow_status("running")
    try:
        sequence_library = getattr(unreal, "LevelSequenceEditorBlueprintLibrary", None)
        if sequence_library is not None:
            try:
                sequence_library.close_level_sequence()
            except Exception:
                pass
        clear_generated_assets(LEVEL_ROOT)

        os.makedirs(os.path.dirname(FINAL_CSV), exist_ok=True)
        temporary = FINAL_CSV + ".tmp"
        shutil.copy2(EXPANDED_CSV, temporary)
        os.replace(temporary, FINAL_CSV)
        if group_names(FINAL_CSV) != group_names(EXPANDED_CSV):
            raise RuntimeError("Promoted final CSV does not match expanded CSV")
        start_final_level_sequences()
    except BaseException as exc:
        fail("promote_multicamera_csv", exc)


def start_final_level_sequences():
    state["stage"] = "final_level_sequences"
    write_workflow_status("running")
    os.environ["BEDLAM_LEVEL_SEQUENCE_CSV_PATH"] = FINAL_CSV
    os.environ["BEDLAM_LEVEL_SEQUENCE_STATUS_PATH"] = FINAL_LEVEL_STATUS
    os.environ["BEDLAM_MRQ_LEVEL_SEQUENCE_STATUS"] = FINAL_LEVEL_STATUS
    namespace = execute_wrapper(LEVEL_WRAPPER, "final_level_sequences")

    def completed():
        try:
            validate_level_status(FINAL_LEVEL_STATUS, EXPECTED_FINAL)
            start_mrq()
        except BaseException as exc:
            fail("final_level_sequences", exc)

    namespace["request_exit"] = completed


def start_mrq():
    state["stage"] = "mrq"
    write_workflow_status("running")
    namespace = execute_wrapper(MRQ_WRAPPER, "mrq")

    def completed():
        try:
            status = read_json(MRQ_STATUS)
            if status.get("status") != "complete":
                raise RuntimeError(f"MRQ generation is not complete: {status}")
            if int(status.get("expected_jobs", -1)) != EXPECTED_JOBS:
                raise RuntimeError(
                    f"MRQ contains {status.get('expected_jobs')} jobs; "
                    f"expected {EXPECTED_JOBS}"
                )
            state["stage"] = "complete"
            write_workflow_status(
                "complete",
                final_sequences=EXPECTED_FINAL,
                mrq_jobs=EXPECTED_JOBS,
                mrq_asset=status.get("mrq_asset"),
            )
            unreal.log(
                f"[linux-camera-to-mrq] complete sequences={EXPECTED_FINAL} "
                f"jobs={EXPECTED_JOBS}"
            )
        except BaseException as exc:
            fail("mrq", exc)
            return
        quit_editor()

    namespace["quit_editor"] = completed


def initial_readiness():
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    if registry.is_loading_assets():
        return False, "asset registry is loading"
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is None:
        return False, "editor world is unavailable"
    levels = unreal.EditorLevelUtils.get_levels(world)
    if not levels:
        return False, "editor world has no levels"
    current_map = str(
        unreal.SystemLibrary.get_path_name(
            unreal.SystemLibrary.get_outer_object(levels[0])
        )
    ).split(".", 1)[0]
    if EXPECTED_MAP and current_map != EXPECTED_MAP:
        return False, f"current map={current_map}, expected={EXPECTED_MAP}"
    labels = {
        str(actor.get_actor_label())
        for actor in unreal.get_editor_subsystem(
            unreal.EditorActorSubsystem
        ).get_all_level_actors()
    }
    if "BE_CameraTarget" not in labels:
        return False, "BE_CameraTarget is unavailable"
    return True, current_map


def wait_for_map(_delta_seconds):
    if state["stage"] != "waiting_for_map":
        return
    elapsed = time.monotonic() - state["started_at"]
    try:
        ready, detail = initial_readiness()
        if not ready:
            if elapsed < START_TIMEOUT:
                return
            raise RuntimeError(f"Timed out waiting for map readiness: {detail}")
        unreal.unregister_slate_post_tick_callback(state["handle"])
        state["handle"] = None
        clear_generated_assets(LEVEL_ROOT)
        clear_generated_assets(MRQ_ROOT)
        start_initial_level_sequences()
    except BaseException as exc:
        if state["handle"] is not None:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            state["handle"] = None
        fail("waiting_for_map", exc)


if len(group_names(BASE_CSV)) != EXPECTED_BASE:
    raise RuntimeError(
        f"Base CSV sequence count changed before launch: {BASE_CSV}"
    )
write_workflow_status("waiting_for_map")
state["handle"] = unreal.register_slate_post_tick_callback(wait_for_map)
unreal._linux_camera_to_mrq_state = state
unreal.log("[linux-camera-to-mrq] waiting for map and asset registry")
