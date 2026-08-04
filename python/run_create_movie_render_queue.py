"""Select generated LevelSequences, build BEDLAM MRQ batches, then exit UE."""

import os
import time
import traceback

import unreal


GENERATOR = os.path.abspath(os.environ["BEDLAM_MRQ_GENERATOR_SCRIPT"])
SEQUENCE_ROOT = os.environ.get("BEDLAM_MRQ_SEQUENCE_ROOT", "/Game/Bedlam/LevelSequences")
OUTPUT_DIR = os.path.abspath(os.environ["BEDLAM_MRQ_OUTPUT_DIR"])
PRESET = os.environ.get("BEDLAM_MRQ_PRESET", "1-1-1_EXR_PNG_DepthMask")
RESOLUTION = os.environ.get("BEDLAM_MRQ_RESOLUTION", "1280x720")
BATCHES = int(os.environ.get("BEDLAM_MRQ_BATCHES", "1"))
START_DELAY = float(os.environ.get("BEDLAM_MRQ_START_DELAY", "5"))
START_TIMEOUT = float(os.environ.get("BEDLAM_MRQ_START_TIMEOUT", "180"))
EXPECTED_MAP = os.environ.get("BEDLAM_MRQ_EXPECTED_MAP", "").split(".", 1)[0]

started_at = time.monotonic()
state = {"handle": None, "started": False}


def quit_editor():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "QUIT_EDITOR")


def generation_readiness():
    """Return whether the requested map and its LevelSequences are fully discoverable."""
    try:
        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
        if asset_registry.is_loading_assets():
            return False, "asset registry is still loading"

        world = unreal.get_editor_subsystem(
            unreal.UnrealEditorSubsystem
        ).get_editor_world()
        if world is None:
            return False, "editor world is unavailable"

        levels = unreal.EditorLevelUtils.get_levels(world)
        if not levels:
            return False, "editor world has no loaded levels"
        current_map = str(
            unreal.SystemLibrary.get_path_name(
                unreal.SystemLibrary.get_outer_object(levels[0])
            )
        ).split(".", 1)[0]
        if EXPECTED_MAP and current_map != EXPECTED_MAP:
            return False, f"current map is {current_map}, expected {EXPECTED_MAP}"

        assets = list(
            unreal.EditorAssetLibrary.list_assets(
                SEQUENCE_ROOT, recursive=False, include_folder=False
            )
        )
        sequence_assets = sorted(
            path
            for path in assets
            if unreal.EditorAssetLibrary.find_asset_data(path).get_class()
            == unreal.LevelSequence.static_class()
        )
        if not sequence_assets:
            return False, f"no LevelSequences found under {SEQUENCE_ROOT}"
        return True, sequence_assets
    except Exception as exc:
        return False, f"readiness check failed: {exc}"


def tick(_delta_seconds):
    if state["started"]:
        return
    elapsed = time.monotonic() - started_at
    if elapsed < START_DELAY:
        return

    ready, readiness_result = generation_readiness()
    if not ready:
        if elapsed < START_TIMEOUT:
            return
        state["started"] = True
        unreal.unregister_slate_post_tick_callback(state["handle"])
        state["handle"] = None
        message = (
            f"Timed out after {elapsed:.1f}s waiting for MRQ generation readiness: "
            f"{readiness_result}"
        )
        unreal.log_error(f"[linux-mrq-wrapper] {message}")
        quit_editor()
        return

    state["started"] = True
    unreal.unregister_slate_post_tick_callback(state["handle"])
    state["handle"] = None

    try:
        sequence_assets = readiness_result

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        namespace = {"__name__": "bedlam_mrq_generator", "__file__": GENERATOR}
        with open(GENERATOR, encoding="utf-8") as script_file:
            exec(compile(script_file.read(), GENERATOR, "exec"), namespace)

        preset_parts = PRESET.split("_")
        sampling = preset_parts[0].split("-")
        if len(sampling) != 3:
            raise RuntimeError(f"Invalid BEDLAM MRQ preset: {PRESET}")
        frame_step, spatial_samples, temporal_samples = map(int, sampling)
        width, height = map(int, RESOLUTION.lower().split("x", 1))
        generate_image = "EXR" in preset_parts or "PNG" in preset_parts
        generate_depth = (
            "DepthMask" in preset_parts or "DepthMaskNormals" in preset_parts
        )
        jobs_per_sequence = int(generate_image) + int(generate_depth)
        if jobs_per_sequence == 0:
            raise RuntimeError(
                f"Preset requests no supported render passes: {PRESET}"
            )

        subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
        pipeline_queue = subsystem.get_queue()
        for job in list(pipeline_queue.get_jobs()):
            pipeline_queue.delete_job(job)

        namespace["output_dir"] = OUTPUT_DIR
        for sequence_path in sequence_assets:
            asset_data = unreal.EditorAssetLibrary.find_asset_data(sequence_path)
            if "EXR" in preset_parts:
                namespace["add_render_job_exr_image"](
                    pipeline_queue,
                    asset_data,
                    frame_step,
                    (width, height),
                    spatial_samples,
                    temporal_samples,
                )
            if "PNG" in preset_parts and "EXR" not in preset_parts:
                namespace["add_render_job"](
                    pipeline_queue,
                    asset_data,
                    frame_step,
                    (width, height),
                    spatial_samples,
                    temporal_samples,
                )
            if "DepthMaskNormals" in preset_parts:
                namespace["add_render_job_exr_depthmask"](
                    pipeline_queue, asset_data, frame_step, (width, height), "World"
                )
            elif "DepthMask" in preset_parts:
                namespace["add_render_job_exr_depthmask"](
                    pipeline_queue, asset_data, frame_step, (width, height), None
                )

        if BATCHES != 1:
            raise RuntimeError("The Linux wrapper currently requires BEDLAM_MRQ_BATCHES=1")
        namespace["save_movie_render_queue"](
            pipeline_queue,
            0,
            namespace["movie_render_queue_root"],
            namespace["movie_render_queue_template"],
        )
        expected_jobs = len(sequence_assets) * jobs_per_sequence
        if len(pipeline_queue.get_jobs()) != expected_jobs:
            raise RuntimeError(
                f"Expected {expected_jobs} MRQ jobs, found {len(pipeline_queue.get_jobs())}"
            )

        unreal.log(
            f"[linux-mrq-wrapper] generated batches from {len(sequence_assets)} sequences "
            f"preset={PRESET} resolution={RESOLUTION} jobs={expected_jobs}"
        )
    except BaseException as exc:
        unreal.log_error(f"[linux-mrq-wrapper] failed: {exc}\n{traceback.format_exc()}")
    finally:
        quit_editor()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal._linux_mrq_generation_handle = state["handle"]
unreal.log(
    f"[linux-mrq-wrapper] waiting for map={EXPECTED_MAP or '<any>'}, "
    f"asset registry, and LevelSequences; minimum_delay={START_DELAY:.1f}s "
    f"timeout={START_TIMEOUT:.1f}s"
)
