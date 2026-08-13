"""Chain the existing LevelSequence and MRQ wrappers in one UE editor session."""

import json
import os
import traceback

import unreal


LEVEL_WRAPPER = os.path.abspath(os.environ["BEDLAM_COMBINED_LEVEL_WRAPPER"])
MRQ_WRAPPER = os.path.abspath(os.environ["BEDLAM_COMBINED_MRQ_WRAPPER"])
LEVEL_STATUS = os.path.abspath(os.environ["BEDLAM_LEVEL_SEQUENCE_STATUS_PATH"])
MRQ_STATUS = os.path.abspath(os.environ["BEDLAM_MRQ_STATUS_PATH"])


def read_status(path):
    try:
        with open(path, encoding="utf-8") as status_file:
            return json.load(status_file)
    except (OSError, ValueError):
        return {}


def quit_editor():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "QUIT_EDITOR")


if not os.path.isfile(LEVEL_WRAPPER):
    raise RuntimeError(f"LevelSequence wrapper does not exist: {LEVEL_WRAPPER}")
if not os.path.isfile(MRQ_WRAPPER):
    raise RuntimeError(f"MRQ wrapper does not exist: {MRQ_WRAPPER}")

level_namespace = {
    "__name__": "bedlam_combined_level_sequence_wrapper",
    "__file__": LEVEL_WRAPPER,
}
with open(LEVEL_WRAPPER, encoding="utf-8") as script_file:
    exec(compile(script_file.read(), LEVEL_WRAPPER, "exec"), level_namespace)

original_level_exit = level_namespace["request_exit"]
chain_state = {"mrq_started": False}


def start_mrq_or_exit():
    """Replace the LevelSequence wrapper's exit with an in-process MRQ handoff."""
    if chain_state["mrq_started"]:
        return
    level_status = read_status(LEVEL_STATUS)
    if level_status.get("status") != "complete":
        unreal.log_error(
            "[linux-combined-wrapper] LevelSequence generation did not complete; "
            "MRQ generation will not start"
        )
        original_level_exit()
        return

    chain_state["mrq_started"] = True
    unreal.log(
        "[linux-combined-wrapper] LevelSequences complete; starting MRQ wrapper "
        "without restarting Unreal"
    )
    try:
        mrq_namespace = {
            "__name__": "bedlam_combined_mrq_wrapper",
            "__file__": MRQ_WRAPPER,
        }
        with open(MRQ_WRAPPER, encoding="utf-8") as script_file:
            exec(compile(script_file.read(), MRQ_WRAPPER, "exec"), mrq_namespace)
    except BaseException as exc:
        unreal.log_error(
            f"[linux-combined-wrapper] Could not start MRQ generation: {exc}\n"
            f"{traceback.format_exc()}"
        )
        os.makedirs(os.path.dirname(MRQ_STATUS), exist_ok=True)
        with open(MRQ_STATUS, "w", encoding="utf-8") as status_file:
            json.dump({"status": "failed", "message": str(exc)}, status_file, indent=2)
        quit_editor()


# The LevelSequence wrapper resolves this global when its asynchronous work
# finishes. Replacing it here keeps the editor alive for the MRQ stage.
level_namespace["request_exit"] = start_mrq_or_exit
unreal._linux_combined_level_namespace = level_namespace
unreal.log("[linux-combined-wrapper] LevelSequence stage registered")
