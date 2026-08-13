# BEDLAM Linux rendering

Linux-specific camera diagnostics and rendering helpers for BEDLAM MRQ jobs.

See [LINUX_PIPELINE_RUNBOOK.md](LINUX_PIPELINE_RUNBOOK.md) for the complete
reproducible setup, plugin builds, rendering command, EXR fix, post-processing
changes, rollback paths, and validation checklist.

The confirmed camera stabilization settings are:

```text
tick.AllowAsyncTickDispatch=0
tick.AllowConcurrentTickQueue=0
```

The persistent `BE_CineCameraActor_Blueprint` must track
`BE_CameraTarget`. In each MRQ PIE world, enforce this tick dependency:

```python
camera.add_tick_prerequisite_actor(controller)
```

This means the `PlayerController` ticks before the camera.

The runtime launcher preserves the production
`exr_image/{sequence_name}` and `exr_depth/{sequence_name}` output directories
and writes completion markers for full renders. Custom frame-range renders do
not write completion markers.

The Linux throw-simulation wrapper is `scripts/run_ue53_throw_simulation.sh`. It runs
the existing Syn4D simulation scripts unchanged inside a full offscreen UE 5.3
editor session. See the simulation section of `LINUX_PIPELINE_RUNBOOK.md`.

The nine-camera placement ablation has a dedicated launcher:

```bash
scripts/run_ue53_camera_placement_ablation.sh \
  PROJECT MAP MAP_FILE /absolute/path/to/be_seq_base.csv
```

It reproduces the six static and three orbit camera configuration used by the
Windows camera-placement workflow. The initial Level Sequences and completed
`linux_level_sequence_status.json` must already exist in
`<dataset>/unreal_assets/LevelSequences`.

For a general final CSV-to-MRQ workflow, use:

```bash
scripts/run_ue53_csv_to_mrq_workflow.sh \
  --engine /absolute/path/to/UnrealEngine \
  --project /absolute/path/to/Project.uproject \
  --map /Game/Package/Map \
  --map-file /absolute/path/to/Map.umap \
  --csv /absolute/path/to/be_seq.csv \
  --output /absolute/path/to/render/output \
  --asset-store /absolute/path/to/unreal_assets
```

The asset store defaults to `unreal_assets` beside the CSV. The workflow
generates Level Sequences and the MRQ in one editor session while retaining
separate status manifests for retry and validation.

For the complete base-CSV-to-camera-placement workflow, use:

```bash
scripts/run_ue53_camera_placement_to_mrq_workflow.sh \
  --project /absolute/path/to/Project.uproject \
  --map /Game/Package/Map \
  --map-file /absolute/path/to/Map.umap \
  --base-csv /absolute/path/to/be_seq_base.csv
```

This keeps Unreal open while it generates temporary validation Level
Sequences, samples the nine camera-placement modes, promotes the validated
multicamera CSV to `be_seq.csv`, replaces the temporary sequences with the
final sequences, and builds the MRQ. Defaults are 9 cameras,
`1-1-1_EXR_PNG_DepthMask`, 1280x720, an asset store beside the CSV, and render
output beside the CSV. Existing Level Sequence and MRQ assets are cleared only
from that dedicated generated-asset store after the expected map is ready.

The combined workflow records:

```text
unreal_assets/linux_initial_level_sequence_status.json
unreal_assets/linux_camera_sampling_status.json
unreal_assets/linux_level_sequence_status.json
unreal_assets/linux_mrq_generation_status.json
unreal_assets/linux_camera_to_mrq_workflow_status.json
```

The current eight-scene preparation is balanced across four GPU sessions:

```bash
runs/camera_placement/run_ue53_camera_placement_preparation_session.sh 1
runs/camera_placement/run_ue53_camera_placement_preparation_session.sh 2
runs/camera_placement/run_ue53_camera_placement_preparation_session.sh 3
runs/camera_placement/run_ue53_camera_placement_preparation_session.sh 4
```

The groups are Gothic; Antiquity/Outpost/Space; Spaceship/Street; and
Train/Warehouse. Gothic runs alone because camera validation is unusually slow
there. Train and Warehouse remain sequential because they share `BE_IBL_3`.

Dataset-specific launchers live outside the general scripts. The current
camera-placement render run uses:

```bash
runs/camera_placement/run_ue53_camera_placement_scene_render.sh gothic
```

It validates and selects the scene-specific generated assets before invoking
the general BEDLAM renderer.

The full eight-scene run is divided across four independent GPU sessions:

```bash
runs/camera_placement/run_ue53_camera_placement_session.sh 1
runs/camera_placement/run_ue53_camera_placement_session.sh 2
runs/camera_placement/run_ue53_camera_placement_session.sh 3
runs/camera_placement/run_ue53_camera_placement_session.sh 4
```

Each command renders two scenes sequentially. Train and Warehouse deliberately
share session 4 because both use the `BE_IBL_3` project.

After camera-placement preparation, the six currently ready scenes can be
rendered across three GPU sessions with:

```bash
runs/camera_placement/run_ue53_camera_placement_ready6_render_session.sh 1
runs/camera_placement/run_ue53_camera_placement_ready6_render_session.sh 2
runs/camera_placement/run_ue53_camera_placement_ready6_render_session.sh 3
```

The pairs are Antiquity/Outpost, Spaceship/Street, and Train/Warehouse.

For the final eight-scene run on five GPUs, use:

```bash
runs/camera_placement/run_ue53_camera_placement_5gpu_render_session.sh 1
runs/camera_placement/run_ue53_camera_placement_5gpu_render_session.sh 2
runs/camera_placement/run_ue53_camera_placement_5gpu_render_session.sh 3
runs/camera_placement/run_ue53_camera_placement_5gpu_render_session.sh 4
runs/camera_placement/run_ue53_camera_placement_5gpu_render_session.sh 5
```

The groups are Gothic; Antiquity/Space; Outpost/Spaceship; Street; and
Train/Warehouse. Shared-project scenes are sequential in one session, so no
generated-asset link is repointed while another process uses that project.

## UE 5.3 Bridge plugin

Use the official Linux Bridge build rather than copying a Windows plugin:

```text
Package: /work/kelvin/unreal_plugins/Linux_Bridge_5.3.0_2023.0.8.zip
Install: /scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2/Engine/Plugins/Bridge
Bridge version: 2023.0.8
EngineVersion: 5.3.0
BuildId: 27405482
```

The archive already has the engine-relative layout, so install it from the UE
root with:

```bash
UE53=/scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2
unzip -q \
  /work/kelvin/unreal_plugins/Linux_Bridge_5.3.0_2023.0.8.zip \
  'Engine/Plugins/Bridge/*' \
  -d "$UE53"
```

Verify that the plugin and engine BuildIds match:

```bash
jq -r .BuildId \
  "$UE53/Engine/Plugins/Bridge/Binaries/Linux/UnrealEditor.modules"
```

The expected value is `27405482`. Projects that declare `Bridge` may keep it
enabled. A successful editor smoke test must contain:

```text
LogPluginManager: Mounting Engine plugin Bridge
```

The installed plugin includes the `Bridge` and `MegascansPlugin` Linux
modules. It was tested with Vulkan alongside the engine-level BEDLAM and
MovieRenderPipeline plugins and shut down cleanly.

Bridge is independent of BEDLAM's modified MovieRenderPipeline. Remove each
uploaded project's Windows-only `Plugins/MovieRenderPipeline` override so
Linux loads the modified engine copy; do not disable Bridge as part of that
cleanup.
