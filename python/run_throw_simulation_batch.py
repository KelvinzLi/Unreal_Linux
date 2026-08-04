"""Launch the existing Syn4D throw simulation batch inside Unreal Editor.

Configuration is supplied through BEDLAM_SIM_* environment variables by the
Linux launcher. The simulation implementation remains in Syn4d_renderer.
"""

import json
import os
import traceback

import unreal


def env(name, default=None):
    value = os.environ.get(name)
    return default if value in (None, "") else value


def env_int(name, default):
    return int(env(name, default))


def env_float(name, default):
    return float(env(name, default))


def env_bool(name, default=False):
    value = str(env(name, "1" if default else "0")).strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"Invalid Boolean value for {name}: {value}")


CSV_PATH = os.path.abspath(env("BEDLAM_SIM_CSV_PATH"))
OUTPUT_DIR = os.path.abspath(env("BEDLAM_SIM_OUTPUT_DIR"))
THROW_BATCH_SCRIPT = os.path.abspath(env("BEDLAM_SIM_BATCH_SCRIPT"))
STATUS_PATH = os.path.join(OUTPUT_DIR, "linux_simulation_status.json")


def write_status(status, message=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    payload = {
        "status": status,
        "csv_path": CSV_PATH,
        "output_dir": OUTPUT_DIR,
        "batch_script": THROW_BATCH_SCRIPT,
    }
    if message:
        payload["message"] = str(message)
    with open(STATUS_PATH, "w", encoding="utf-8") as status_file:
        json.dump(payload, status_file, indent=2)


def request_editor_exit():
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    except Exception:
        world = None
    unreal.SystemLibrary.execute_console_command(world, "QUIT_EDITOR")


def load_batch_namespace():
    namespace = {
        "__name__": "sim_throw_csv_objects_batch",
        "__file__": THROW_BATCH_SCRIPT,
    }
    with open(THROW_BATCH_SCRIPT, encoding="utf-8") as script_file:
        exec(compile(script_file.read(), THROW_BATCH_SCRIPT, "exec"), namespace)
    return namespace


def start():
    for required_path in (CSV_PATH, THROW_BATCH_SCRIPT):
        if not os.path.isfile(required_path):
            raise RuntimeError(f"Required file does not exist: {required_path}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    write_status("running")
    batch = load_batch_namespace()
    batch["run_batch"](
        csv_path=CSV_PATH,
        output_dir=OUTPUT_DIR,
        num_throw_objects=env_int("BEDLAM_SIM_NUM_THROW_OBJECTS", 20),
        scale_multiplier=env_float("BEDLAM_SIM_SCALE_MULTIPLIER", 0.5),
        physics_substepping=env_bool("BEDLAM_SIM_PHYSICS_SUBSTEPPING", True),
        physics_substep_fps=env_float("BEDLAM_SIM_PHYSICS_SUBSTEP_FPS", 480.0),
        physics_max_substeps=env_int("BEDLAM_SIM_PHYSICS_MAX_SUBSTEPS", 32),
        max_resimulation_attempts=env_int("BEDLAM_SIM_MAX_RESIMULATION_ATTEMPTS", 8),
        seed=env_int("BEDLAM_SIM_SEED", 12345),
        limit=(
            None
            if env("BEDLAM_SIM_LIMIT") in (None, "0")
            else env_int("BEDLAM_SIM_LIMIT", 1)
        ),
        continue_on_error=env_bool("BEDLAM_SIM_CONTINUE_ON_ERROR", False),
    )

    state = {"seen_running": False, "handle": None}

    def monitor(_delta_seconds):
        handle = getattr(unreal, "_csv_throw_batch_handle", None)
        if handle is not None:
            state["seen_running"] = True
            return
        if not state["seen_running"]:
            return

        diagnostics = os.path.join(OUTPUT_DIR, "_batch_tmp", "batch_diagnostics.json")
        final_csv = os.path.join(OUTPUT_DIR, "be_seq_sim.csv")
        success = os.path.isfile(final_csv) and os.path.isfile(diagnostics)
        write_status(
            "complete" if success else "failed",
            None if success else "Batch ended without final CSV and diagnostics",
        )
        if state["handle"] is not None:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            state["handle"] = None
        unreal.log(f"[linux-sim-wrapper] finished success={success} output={OUTPUT_DIR}")
        request_editor_exit()

    state["handle"] = unreal.register_slate_post_tick_callback(monitor)
    unreal._linux_simulation_monitor_handle = state["handle"]
    unreal.log(f"[linux-sim-wrapper] started csv={CSV_PATH} output={OUTPUT_DIR}")


try:
    start()
except Exception as exc:
    unreal.log_error(f"[linux-sim-wrapper] startup failed: {exc}\n{traceback.format_exc()}")
    write_status("failed", exc)
    request_editor_exit()
