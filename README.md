# BEDLAM Linux rendering

This repository installs and runs the BEDLAM Unreal Engine 5.3.2 rendering
workflow on Linux. This README is the ordered setup and execution guide.
Implementation history, diagnostics, failure analysis, and rollback procedures
are in [LINUX_PIPELINE_RUNBOOK.md](LINUX_PIPELINE_RUNBOOK.md).

## 1. Requirements and storage layout

Use the official precompiled `Linux_Unreal_Engine_5.3.2.zip` from
[Unreal Engine for Linux](https://www.unrealengine.com/linux). Rendering must
run on a GPU node with a Vulkan-capable NVIDIA driver; a login node cannot run
the editor. The tested allocation used one GPU, 16 CPU cores, and 96 GB RAM.

Required command-line tools are:

```text
bash, unzip, jq, rsync, flock, ffmpeg, zstd, find, xargs
```

When capacity permits, keep the engine and projects on `/work` and write large,
reproducible render outputs to `/scratch`:

```text
/work/<user>/apps/Linux_Unreal_Engine_5.3.2
/work/<user>/apps/UnrealProjects/<project>
/scratch/<user>/datasets/<render_output>
```

These are recommended filesystem roles, not hard-coded paths. See
[runbook section 1](LINUX_PIPELINE_RUNBOOK.md#1-working-paths) for the tested
cluster layout and filesystem notes.

## 2. Install Unreal and Linux plugins

Extract the engine:

```bash
mkdir -p /work/$USER/apps
unzip Linux_Unreal_Engine_5.3.2.zip -d /work/$USER/apps
export UE_ROOT=/work/$USER/apps/Linux_Unreal_Engine_5.3.2
```

### Bridge

Download the separate official package
`Linux_Bridge_5.3.0_2023.0.8.zip`. Do not use its Windows build or the older
Linux 2023.0.3/2023.0.6 packages.

```bash
unzip -q Linux_Bridge_5.3.0_2023.0.8.zip \
  'Engine/Plugins/Bridge/*' -d "$UE_ROOT"

test -f "$UE_ROOT/Engine/Plugins/Bridge/Bridge.uplugin"
jq -r .BuildId \
  "$UE_ROOT/Engine/Plugins/Bridge/Binaries/Linux/UnrealEditor.modules"
```

The expected BuildId is `27405482`. Bridge is retained because this is the
tested project configuration. Background and dependency analysis are in
[runbook section 4](LINUX_PIPELINE_RUNBOOK.md#4-bedlam-camera-shake-plugin).

### BEDLAM camera-shake plugin

Copy the complete tested Linux plugin into the matching engine path:

```text
<UE_ROOT>/Engine/Plugins/BEDLAM/
├── BEDLAM.uplugin
├── Binaries/Linux/libUnrealEditor-BEDLAM.so
├── Content/CameraShake/
├── Resources/
└── Source/BEDLAM/
```

```bash
mkdir -p "$UE_ROOT/Engine/Plugins/BEDLAM"
cp -a "$BEDLAM_PLUGIN_SOURCE/." "$UE_ROOT/Engine/Plugins/BEDLAM/"
```

Do not substitute `Binaries/Win64` for `Binaries/Linux`. Enable `BEDLAM` in
each project that uses camera shake. Build history is in
[runbook section 4](LINUX_PIPELINE_RUNBOOK.md#4-bedlam-camera-shake-plugin).

### Modified MovieRenderPipeline

BEDLAM's modified engine plugin provides centre-temporal-sample camera metadata
and the corrected Linux EXR mask/depth channel names. Install the complete
tested UE 5.3.2 plugin at:

```text
<UE_ROOT>/Engine/Plugins/MovieScene/MovieRenderPipeline
```

For example, distribute and install the working directory as one archive:

```bash
# On the source installation
tar --zstd -cf MovieRenderPipeline_BEDLAM_Linux_UE5.3.2.tar.zst \
  -C "$UE_ROOT/Engine/Plugins/MovieScene" MovieRenderPipeline

# On the destination installation
tar --zstd -xf MovieRenderPipeline_BEDLAM_Linux_UE5.3.2.tar.zst \
  -C "$UE_ROOT/Engine/Plugins/MovieScene"
```

Expected Linux module hashes:

```text
65cc3ef4e7aae8c85f7f7e452e6628e8997bfc90cfd14642babff2ef5f23b4fa  libUnrealEditor-MovieRenderPipelineCore.so
f36b711de7389c1b215e35da4b8b72c457822c88b7e296e23368c647749657d4  libUnrealEditor-MovieRenderPipelineRenderPasses.so
```

Remove any project-level `Plugins/MovieRenderPipeline` copy because its module
names conflict with the engine copy. Source changes, rebuilding, and rollback
are in [runbook section 5](LINUX_PIPELINE_RUNBOOK.md#5-bedlam-movie-render-pipeline-metadata)
and [section 8](LINUX_PIPELINE_RUNBOOK.md#8-linux-multilayer-exr-channel-name-fix).

## 3. Upload BEDLAM and object content

Copy Unreal content from the working machine to the identical engine-relative
path on Linux. Preserve spelling and capitalization. For example:

```text
Source:      UE_5.3/Engine/Content/PS/Bedlam/Core/...
Linux: <UE_ROOT>/Engine/Content/PS/Bedlam/Core/...
```

The resulting layout must include:

```text
<UE_ROOT>/Engine/Content/PS/Bedlam/
├── Core/
├── Clothing/
├── HDRI/
├── Hair/
├── SMPLX_LH/
├── SMPLX_LH_animations/
└── Shoes/

<UE_ROOT>/Engine/Content/PS/obj/
```

`Core` includes the camera Blueprints, `BE_CameraTarget` content, updated
`BEDLAM2.uasset` editor widget, and related assets. `obj` includes GSO and
Objaverse meshes, materials, and textures. Copying is simplest; a symlink is
valid only when its target is stable and visible from every render node.

This same-path rule applies to Unreal content, not compiled Windows plugin
binaries. See [runbook section 3](LINUX_PIPELINE_RUNBOOK.md#3-bedlam-core-camera-assets).

## 4. Install BEDLAM Engine Python tools

Install the tracked renderer scripts under the runtime names expected by the
Linux wrappers:

```bash
export SYN4D_RENDERER_ROOT=/absolute/path/to/Syn4d_renderer
BEDLAM_CORE="$UE_ROOT/Engine/Content/PS/Bedlam/Core/Python"
mkdir -p "$BEDLAM_CORE"

install -m 0644 \
  "$SYN4D_RENDERER_ROOT/unreal/render/Core/Python/create_level_sequences_csv_nohair.py" \
  "$BEDLAM_CORE/create_level_sequences_csv.py"

install -m 0644 \
  "$SYN4D_RENDERER_ROOT/unreal/render/Core/Python/create_movie_render_queue.py" \
  "$BEDLAM_CORE/create_movie_render_queue.py"
```

The tested renderer branch is
`features/additional_global_motion_linux_render`. The optional nine-camera
ablation sampler comes from `features/camera_ablations`; ordinary rendering
does not require it. Renderer-specific changes are summarized in
[runbook sections 9–12](LINUX_PIPELINE_RUNBOOK.md#9-post-processing-changes).

## 5. Configure paths

Create the ignored machine-local configuration:

```bash
cd /absolute/path/to/unreal_linux
cp config/environment.example.sh config/local.sh
```

Edit every path needed by the intended workflow. General launchers load this
file automatically. An alternative configuration can be selected with:

```bash
export BEDLAM_CONFIG=/absolute/path/to/bedlam-linux-config.sh
```

Explicit command arguments take priority over configured defaults.
Dataset-specific scripts under `runs/` are examples, not portable launchers.

## 6. Create the post-processing environments

The setup script uses the renderer's committed `requirements.txt`. If an
existing `ORIGINAL_BEDLAM_ENV` is configured, it clones and repairs that
environment; otherwise it creates a clean Python 3.10 environment and installs
the same requirements. It never modifies the original and refuses to overwrite
an existing repaired environment:

```bash
# Set CONDA_ROOT, BEDLAM_PYTHON_ENV, OIIO_ENV, and SYN4D_RENDERER_ROOT in
# config/local.sh first. ORIGINAL_BEDLAM_ENV is optional.
scripts/setup_postprocessing_environments.sh
```

The tested repair installs NumPy 2.2.6, OpenEXR 3.4.4, and
opencv-python-headless 4.12.0.88. It also creates a separate Conda environment
containing `oiiotool` and `exrheader`. Keeping OpenImageIO CLI tools separate
prevents them from replacing the main environment's NumPy ABI.

Activate the repaired Python environment and expose only the tool binaries:

```bash
source "$CONDA_ROOT/etc/profile.d/conda.sh"
conda activate "$BEDLAM_PYTHON_ENV"
export PATH="$OIIO_ENV/bin:$PATH"
export OIIOTOOL="$OIIO_ENV/bin/oiiotool"
```

The original contamination, exact repair, and validation output are in
[runbook section 10](LINUX_PIPELINE_RUNBOOK.md#10-python-environment-contamination-and-safe-repair).

## 7. Verify the installation

```bash
hostname
nvidia-smi
scripts/verify_installation.sh
```

The verifier checks Unreal, Linux plugins, the modified MovieRenderPipeline,
BEDLAM content, object libraries, and renderer scripts. Run it inside a GPU
allocation before processing projects.

## 8. Prepare each project and map

For each project:

1. Use a UE 5.3 project with UE 5.3.2; never resave it in UE 5.4.
2. Enable the engine-level `BEDLAM` plugin.
3. Keep the tested Linux Bridge plugin enabled when declared by the project.
4. Remove a Windows/project-level `Plugins/MovieRenderPipeline` override.
5. Confirm the map contains `BE_CineCameraActor_Blueprint` and
   `BE_CameraTarget`.
6. Set the persistent camera's `Actor To Track` to `BE_CameraTarget` and save
   the map.

The batch repair script accepts semicolon-separated `/Game/...` map paths. Run
it through the editor, for example:

```bash
export BEDLAM_CAMERA_MAPS='/Game/Package/MapA;/Game/Package/MapB'
"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" \
  /absolute/path/to/Project.uproject \
  -RenderOffscreen -vulkan -unattended -NoSplash \
  "-ExecCmds=py $(pwd)/python/diagnostic/fix_bedlam_camera_targets_batch.py" \
  -stdout -FullStdOutLogOutput
```

The camera-shake plugin does not assign the look-at reference. Camera behavior
and Linux tick ordering are explained in
[runbook section 6](LINUX_PIPELINE_RUNBOOK.md#6-camera-configuration-and-linux-stabilization).

## 9. Create Level Sequences and MRQ

This basic workflow starts from an already prepared final `be_seq.csv`; it does
not perform camera sampling. Keep the matching `be_camera_animations.json`
beside the CSV. These paths have different meanings:

```text
PROJECT   = physical path to the .uproject file
MAP       = Unreal package path, such as /Game/Package/Map
MAP_FILE  = physical path to the corresponding Map.umap file
DATASET   = directory containing be_seq.csv and be_camera_animations.json
ASSETS    = external store for generated Level Sequence and MRQ .uasset files
```

Set them once:

```bash
export PROJECT=/work/$USER/apps/UnrealProjects/Project/Project.uproject
export MAP=/Game/Package/Map
export MAP_FILE=/work/$USER/apps/UnrealProjects/Project/Content/Package/Map.umap
export DATASET=/scratch/$USER/datasets/scene
export ASSETS="$DATASET/unreal_assets"

test -f "$DATASET/be_seq.csv"
test -f "$DATASET/be_camera_animations.json"
```

### 9.1 Create Level Sequences only

```bash
BEDLAM_LEVEL_SEQUENCE_CSV_PATH="$DATASET/be_seq.csv" \
BEDLAM_GENERATED_ASSET_STORE="$ASSETS" \
scripts/run_ue53_create_level_sequences.sh
```

This creates:

```text
$ASSETS/LevelSequences/*.uasset
$ASSETS/linux_level_sequence_status.json
```

The launcher links the external asset directory into the project at
`Content/Bedlam/LevelSequences`, making it available in Unreal as
`/Game/Bedlam/LevelSequences`. Do not run two workflows against the same
project directory concurrently because they can repoint this link.

### 9.2 Configure MRQ sampling and create MRQ only

The preset begins with three integers:

```text
frame-step - spatial-samples - temporal-samples
```

The tested basic preset is:

```text
1-1-1_EXR_PNG_DepthMask
│ │ │
│ │ └─ 1 temporal sample
│ └─── 1 spatial sample
└───── render every frame
```

For example, `1-8-1_EXR_PNG_DepthMask` renders every frame with eight spatial
samples and one temporal sample. Sampling is authored into MRQ here; do not set
runtime sampling overrides unless intentionally replacing these values.

Create MRQ after Level Sequence generation reports `status: complete`:

```bash
BEDLAM_MRQ_OUTPUT_DIR="$DATASET" \
BEDLAM_GENERATED_ASSET_STORE="$ASSETS" \
BEDLAM_MRQ_PRESET=1-1-1_EXR_PNG_DepthMask \
BEDLAM_MRQ_RESOLUTION=1280x720 \
BEDLAM_MRQ_LEGACY_MOTION_BLUR=false \
scripts/run_ue53_create_movie_render_queue.sh
```

This creates:

```text
$ASSETS/MovieRenderQueue/MRQ_Batch_00.uasset
$ASSETS/linux_mrq_generation_status.json
```

The queue is available in Unreal as
`/Game/Bedlam/MovieRenderQueue/MRQ_Batch_00`.

### 9.3 Recommended combined command

For normal use, create Level Sequences and MRQ in one Unreal session to avoid
a second editor startup:

```bash
scripts/run_ue53_csv_to_mrq_workflow.sh \
  --engine "$UE_ROOT" \
  --project "$PROJECT" \
  --map "$MAP" \
  --map-file "$MAP_FILE" \
  --csv "$DATASET/be_seq.csv" \
  --output "$DATASET" \
  --asset-store "$ASSETS" \
  --preset 1-1-1_EXR_PNG_DepthMask \
  --resolution 1280x720 \
  --legacy-motion-blur false
```

Both status manifests must report `"status": "complete"` before rendering.
Generated-asset storage and recovery details are in
[runbook section 18](LINUX_PIPELINE_RUNBOOK.md#18-generated-level-sequence-and-mrq-assets).
Camera sampling and simulation are optional advanced workflows documented only
in the runbook and are not required for this basic generation path.

## 10. Render

Run after generation finishes, inside a GPU allocation:

```bash
PROJECT=/absolute/path/to/Project.uproject \
MAP=/Game/Package/Map \
BEDLAM_RUNTIME_RENDER_DIR=/scratch/$USER/datasets/scene \
BEDLAM_RUNTIME_PROBE_DIR=/scratch/$USER/datasets/scene/unreal_logs/runtime_camera \
BEDLAM_RUNTIME_EXEC_CMDS='tick.AllowAsyncTickDispatch 0,tick.AllowConcurrentTickQueue 0' \
scripts/run_ue53_bedlam_render.sh
```

The default queue asset is:

```text
/Game/Bedlam/MovieRenderQueue/MRQ_Batch_00
```

Override it when necessary with `BEDLAM_RUNTIME_QUEUE_ASSET`. Spatial and
temporal sampling come from MRQ unless the corresponding runtime override is
set to a nonzero value. The launcher uses full-editor offscreen Vulkan and
adds the tested camera tick prerequisite.

Expected output is:

```text
exr_image/<sequence>/
exr_depth/<sequence>/
post_ready/<sequence>.done
```

Runtime behavior and diagnostic controls are in
[runbook section 7](LINUX_PIPELINE_RUNBOOK.md#7-production-render-command).

## 11. Post-process

Keep the repaired Python environment active and the OIIO tool directory on
`PATH`:

```bash
cd "$SYN4D_RENDERER_ROOT/tools/post_render_pipeline"
bash be_post_render_pipeline_watch.sh \
  /scratch/$USER/datasets/scene \
  landscape extract_layers extract_masks \
  --workers 2
```

Successful processing produces PNGs, MP4s, depth/mask layers, and camera CSVs,
then removes processed source EXRs according to the renderer workflow. Watch
mode continues polling and therefore does not print a global completion line.
Detailed output layout, locks, and recovery are in
[runbook sections 11 and 13](LINUX_PIPELINE_RUNBOOK.md#11-running-post-processing).

## 12. Final validation

Before sharing a dataset, verify:

- the render and post-processing commands exited successfully;
- every expected sequence has a processed completion marker;
- RGB PNG/MP4, depth, masks, and camera CSVs exist;
- camera metadata uses the expected centre temporal sample;
- no unresolved plugin, map, actor-binding, or EXR-channel errors occur in the
  Unreal logs.

Use the complete checklist in
[runbook section 14](LINUX_PIPELINE_RUNBOOK.md#14-validation-checklist). Known
harmless warnings are listed separately in
[runbook section 15](LINUX_PIPELINE_RUNBOOK.md#15-known-harmless-or-unrelated-messages).
