# BEDLAM2 Unreal Linux rendering and post-processing runbook

This document records the working BEDLAM2 pipeline on the Oxford Linux
cluster as of 25 July 2026. It covers the UE 5.3.2 installation, BEDLAM
plugins and engine content, deterministic camera evaluation, BEDLAM output
layout and metadata, the Linux EXR fix, and the Syn4D post-processing changes.

## 1. Working paths

```text
UE 5.3.2:
/scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2

Project:
/scratch/shared/beegfs/kelvin/apps/UnrealProjects/UE_5.3.2/SciFiModularOutpost

Project descriptor:
/scratch/shared/beegfs/kelvin/apps/UnrealProjects/UE_5.3.2/SciFiModularOutpost/SciFiModularOutpost.uproject

Map:
/Game/SciFiModularOutpost/Maps/ShowCase

MRQ queue:
/Game/Bedlam/MovieRenderQueue/MRQ_Batch_00.MRQ_Batch_00

Linux helper repository:
/athenahomes/kelvin/projects/Syn4D/unreal_linux

Post-processing repository:
/athenahomes/kelvin/projects/Syn4D/Syn4d_renderer

Repaired BEDLAM Python environment:
/users/kelvin/miniconda3/envs/bedlam2-repaired

Isolated OpenImageIO command-line environment:
/users/kelvin/miniconda3/envs/bedlam-oiio-tools
```

Do not open the fresh UE 5.3.2 project with UE 5.4. Assets saved by UE 5.4 may
not reopen correctly in UE 5.3.

Rendering must run inside a Slurm GPU allocation. A login node cannot
initialize Vulkan.

## 2. Components that were required

There are three separate BEDLAM-related components. Do not confuse them.

1. BEDLAM Core assets are Blueprint/content assets used by the camera system.
2. The BEDLAM C++ plugin supplies BEDLAM camera-shake behavior.
3. BEDLAM's modified Movie Render Pipeline records all temporal camera samples
   and selects the centre sample for the standard camera metadata.

The camera look-at and Linux tick-order fix are separate from all three.

## 3. BEDLAM Core camera assets

The project references assets through `/Engine/PS/Bedlam/Core/`. Therefore the
assets must physically exist under the engine, not only under project content:

```text
/scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2/Engine/Content/PS/Bedlam/Core
```

Important files include:

```text
BE_CineCameraActor_Blueprint.uasset
BE_CameraOperator.uasset
```

Missing assets caused unresolved references and incomplete camera behavior.
Confirm them with:

```bash
test -f /scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2/Engine/Content/PS/Bedlam/Core/BE_CineCameraActor_Blueprint.uasset
test -f /scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2/Engine/Content/PS/Bedlam/Core/BE_CameraOperator.uasset
```

## 4. BEDLAM camera-shake plugin

The original Windows/UE 5.3 plugin was rebuilt for Linux and installed
project-locally:

```text
/scratch/shared/beegfs/kelvin/apps/UnrealProjects/UE_5.3.2/SciFiModularOutpost/Plugins/BEDLAM
```

The working binary is:

```text
Plugins/BEDLAM/Binaries/Linux/libUnrealEditor-BEDLAM.so
```

The plugin declares `GameplayCameras` and its Build.cs includes that module as
a dependency. It is enabled in `SciFiModularOutpost.uproject`.

The original Windows plugin backup is:

```text
/work/kelvin/unreal_plugin_backups/BEDLAM_UE53_Windows
```

This plugin restores deterministic BEDLAM camera shake. It did not fix either
the basic look-at target or the random camera direction changes by itself.

## 5. BEDLAM Movie Render Pipeline metadata

BEDLAM's MovieRenderPipeline is a modified copy of Unreal's complete built-in
plugin. It duplicates the stock plugin and module names, so it was not kept as
a competing project plugin. The working approach for UE 5.3.2 was to build the
modified engine module and replace only the matching engine binary.

Current modified core binary:

```text
/scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2/Engine/Plugins/MovieScene/MovieRenderPipeline/Binaries/Linux/libUnrealEditor-MovieRenderPipelineCore.so
```

Stock rollback backup:

```text
/work/kelvin/unreal_plugin_backups/MovieRenderPipeline_stock_UE53_Linux_before_BEDLAM_20260724
```

BEDLAM source backups:

```text
/work/kelvin/unreal_plugin_backups/MovieRenderPipeline_BEDLAM_UE53_Windows
/work/kelvin/unreal_plugin_backups/MovieRenderPipeline_BEDLAM_UE53_fresh
```

The custom core records however many temporal samples the MRQ job requests:

```text
unreal/camera/bedlam/subframe_0/...
unreal/camera/bedlam/subframe_N/...
```

It selects the centre index using `TemporalSampleCount / 2` and copies that
sample to:

```text
unreal/camera/curPos/...
unreal/camera/curRot/...
```

For one temporal sample, `subframe_0` is the only and therefore centre sample.
For three samples it selects `subframe_1`; for seven it selects `subframe_3`.
BEDLAM warns when the count is even because there is no single centre sample.

BEDLAM does **not** set the temporal sample count and does not require seven.
The MRQ configuration owns that setting. The uploaded queue is authored with
spatial sample count 1 and temporal sample count 1, which produces complete
BEDLAM camera metadata:

```text
unreal/camera/bedlam/subframe_0/...
unreal/camera/curPos/info = Center subframe camera ground truth
unreal/camera/curRot/info = Center subframe camera ground truth
```

Thus the ordinary BEDLAM camera CSV receives the correct centre camera pose
with temporal count 1.
The stock pipeline still renders temporal samples, but it does not provide this
BEDLAM centre-sample metadata behavior.

### Rebuilding one MovieRenderPipeline module

Use a clean temporary host project:

```text
/tmp/bedlam_engine_plugin_host/HostProject.uproject
```

Build only the required module:

```bash
UE53=/scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2

"$UE53/Engine/Build/BatchFiles/Linux/Build.sh" \
  UnrealEditor Linux Development \
  -Project=/tmp/bedlam_engine_plugin_host/HostProject.uproject \
  -plugin="$UE53/Engine/Plugins/MovieScene/MovieRenderPipeline/MovieRenderPipeline.uplugin" \
  -Module=MovieRenderPipelineCore \
  -noubtmakefiles
```

Do not build or replace the entire plugin unless necessary. A whole-plugin
attempt removed/rebuilt unrelated pieces such as `UEOpenExrRTTI` and caused
linking problems. Back up each source and `.so` before replacing it.

## 6. Camera configuration and Linux stabilization

Relevant actors:

```text
Camera:   BE_CineCameraActor_Blueprint
Target:   BE_CameraTarget
Root:     BE_CameraRoot
Operator: BE_CameraOperator
```

The persistent actor in `/Game/SciFiModularOutpost/Maps/ShowCase` must have:

```text
Look-at Tracking Settings
  Actor To Track = BE_CameraTarget
```

The Level Sequence animates whether look-at is enabled, but relies on the
persistent map actor to store the target actor reference. Confirm this setting
after copying a project or map between machines.

The isolated abrupt camera turns on Linux were stabilized with:

```text
tick.AllowAsyncTickDispatch=0
tick.AllowConcurrentTickQueue=0
```

The runtime renderer also adds this tick prerequisite in the PIE world:

```python
camera.add_tick_prerequisite_actor(controller)
```

This forces the PlayerController to tick before the camera. The important
settings are synchronous tick dispatch/queue plus the prerequisite; the
command-line argument order was not the underlying fix.

The problem occurred with UE 5.3.2 and UE 5.4.4, in `-game` and PIE. Integer
frame transform probes were smooth even when rendered frames jumped, which
pointed to runtime/sub-frame evaluation order rather than a persistent
transform-curve discontinuity.

## 7. Production render command

The launcher is:

```text
/athenahomes/kelvin/projects/Syn4D/unreal_linux/run_ue53_bedlam_runtime_probe.slurm
```

Despite its historical name, it now supports the production BEDLAM folder
layout and completion markers. Run it directly with `bash` when already inside
a Slurm GPU allocation; do not submit another Slurm job.

Example:

```bash
env \
  BEDLAM_RUNTIME_RENDER_DIR=/work/kelvin/bedlam2/images/kaggle_eval/sim/outpost_ue53_bedlam_temporal1 \
  BEDLAM_RUNTIME_PROBE_DIR=/work/kelvin/unreal_logs/outpost_ue53_bedlam_temporal1 \
  BEDLAM_RUNTIME_EXEC_CMDS='tick.AllowAsyncTickDispatch 0,tick.AllowConcurrentTickQueue 0' \
  BEDLAM_RUNTIME_PRESERVE_BEDLAM_LAYOUT=1 \
  BEDLAM_RUNTIME_IMAGE_TEMPORAL_SAMPLES=0 \
  BEDLAM_RUNTIME_WRITE_DONE_MARKERS=1 \
  bash /athenahomes/kelvin/projects/Syn4D/unreal_linux/run_ue53_bedlam_runtime_probe.slurm
```

`BEDLAM_RUNTIME_IMAGE_TEMPORAL_SAMPLES=0` means “do not override the saved MRQ
queue.” The queue then uses its authored temporal sample count of 1. Always set
this explicitly while the launcher's historical internal default remains 7.

Do not force seven temporal samples merely to obtain centre-frame camera
metadata. That override was added during Linux development after incorrectly
inferring that the BEDLAM `subframe_0` through `subframe_6` metadata observed
in a test meant seven samples were required. The code actually handles any
odd count, including one.

Forcing seven caused the renderer to evaluate times between the sequence's
per-frame object keys. The thrown-object transform sections use linear Euler
rotation channels with quaternion interpolation disabled, and many keys cross
the `+180/-180` representation boundary. Between-key evaluation consequently
made some objects rotate through the long path. The confirmed temporal-count-1
comparison render removed this behavior and matched the good UE 5.4 render.

Confirmed comparison output:

```text
/work/kelvin/bedlam2/images/kaggle_eval/sim/outpost_ue53_bedlam_temporal1
```

Expected output:

```text
exr_image/seq_000000_0/*.exr
exr_image/seq_000000_0/*.png
exr_depth/seq_000000_0/*.exr
post_ready/seq_000000_0.done
```

The full sequence produces 202 frames including ten negative-numbered warm-up
frames. Post-processing removes the warm-up frames, leaving 192 dataset frames.

If either `BEDLAM_RUNTIME_START_FRAME` or `BEDLAM_RUNTIME_END_FRAME` is set,
the launcher disables completion markers. A partial diagnostic render must not
be advertised as post-processing-ready. The end frame is exclusive, so a
single-frame test uses `[0,1)`, not `[0,0)`.

## 8. Linux multilayer EXR channel-name fix

### Symptom

The depth EXRs contained valid-looking layer prefixes followed by corrupted
channel suffixes. For example, the physical channel was not exactly:

```text
ActorHitProxyMask00.R
FinalImageMovieRenderQueue_WorldDepth.R
```

This caused:

```text
KeyError: 'ActorHitProxyMask00.R'
```

Both OpenEXR Python and `exrheader` observed the malformed physical names, so
this was an Unreal writer bug rather than a Python parser issue.

### Cause and fix

File:

```text
Engine/Plugins/MovieScene/MovieRenderPipeline/Source/MovieRenderPipelineRenderPasses/Private/MoviePipelineEXROutput.cpp
```

`FString::Printf(TEXT("%s.%s"), ...)` was given a `const char*` for its second
TCHAR `%s`. This happened to work on Windows but corrupted names on Linux.

Change the channel arrays and selected pointer from ANSI to TCHAR:

```cpp
static const TCHAR* RGBAChannelNames[] =
    { TEXT("R"), TEXT("G"), TEXT("B"), TEXT("A") };
static const TCHAR* BGRAChannelNames[] =
    { TEXT("B"), TEXT("G"), TEXT("R"), TEXT("A") };
static const TCHAR* GrayChannelNames[] = { TEXT("G") };

const TCHAR** ChannelNames = BGRAChannelNames;
```

Then rebuild only:

```bash
"$UE53/Engine/Build/BatchFiles/Linux/Build.sh" \
  UnrealEditor Linux Development \
  -Project=/tmp/bedlam_engine_plugin_host/HostProject.uproject \
  -plugin="$UE53/Engine/Plugins/MovieScene/MovieRenderPipeline/MovieRenderPipeline.uplugin" \
  -Module=MovieRenderPipelineRenderPasses \
  -noubtmakefiles
```

Current binary:

```text
Engine/Plugins/MovieScene/MovieRenderPipeline/Binaries/Linux/libUnrealEditor-MovieRenderPipelineRenderPasses.so
```

Rollback backup:

```text
/work/kelvin/unreal_plugin_backups/MovieRenderPipelineRenderPasses_UE53_before_EXR_channel_fix_20260725
```

Validate a new EXR:

```bash
exrheader FRAME.exr | grep -E \
  'ActorHitProxyMask00.R|FinalImageMovieRenderQueue_WorldDepth.R'
```

Do not use `python/repair_ue53_linux_exr_channels.py` for production. That
post-hoc repair experiment was not fully validated. Rerender with the corrected
writer.

## 9. Post-processing changes

The post-processing entry point is:

```text
Syn4d_renderer/tools/post_render_pipeline/be_post_render_pipeline_watch.sh
```

Three local changes were needed.

### 9.1 Use the activated repaired Python environment

The watcher previously hard-coded:

```text
$HOME/.virtualenvs/bedlam2
```

The original cluster environment was:

```text
/users/kelvin/miniconda3/envs/bedlam2
```

The hard-coded activation/deactivation and venv existence check were removed.
The watcher now uses the `python3` supplied by the caller's active environment.
Use `/users/kelvin/miniconda3/envs/bedlam2-repaired`, as described in
section 10.

### 9.2 Replace the wrong `parallel`

`/usr/bin/parallel` on the cluster is not GNU Parallel and rejected
`--halt`. In:

```text
tools/post_render_pipeline/exr/exr_save_layers.sh
```

the GNU Parallel invocation was replaced with NUL-safe GNU `xargs`:

```bash
find "$input_exr" -name "*.exr" -print0 |
  xargs -0 -r -P "$num_processes" -n 1 \
    bash -c 'process_exr "$1"' _
```

### 9.3 Provide `oiiotool` without administrator access

The repository's Python requirements do not install `oiiotool`. It is a system
CLI dependency. The local working machine used Ubuntu's:

```text
/usr/bin/oiiotool
openimageio-tools 2.4.17
```

The cluster had only the old OpenImageIO library, not the executable. Installing
OpenEXR/OpenImageIO into the main `bedlam2` environment contaminated its Python
package stack, as documented in section 10. The CLI tools therefore belong in
this isolated environment:

```text
/users/kelvin/miniconda3/envs/bedlam-oiio-tools
```

It contains:

```text
/users/kelvin/miniconda3/envs/bedlam-oiio-tools/bin/oiiotool
/users/kelvin/miniconda3/envs/bedlam-oiio-tools/bin/exrheader
```

The layer script now:

1. uses `OIIOTOOL` if explicitly set;
2. otherwise uses `oiiotool` found on `PATH`;
3. otherwise falls back to the isolated executable above.

Keep `bedlam2-repaired` activated and prepend the tool environment to `PATH`;
do not activate the OIIO environment over the Python environment:

```bash
export PATH="/users/kelvin/miniconda3/envs/bedlam-oiio-tools/bin:$PATH"
```

To recreate the isolated tool:

```bash
/users/kelvin/miniconda3/bin/conda create \
  -p /users/kelvin/miniconda3/envs/bedlam-oiio-tools \
  -c conda-forge \
  openimageio-tools \
  -y
```

The installed CLI is currently 3.1.15. It was tested successfully on the
corrected BEDLAM EXR for RGB PNG and half-float depth extraction.

### 9.4 Mask PNG writer compatibility

The contaminated original environment exposed an OpenCV/NumPy ABI mismatch:
even a contiguous `numpy.ndarray` was rejected by `cv2.imwrite`. In:

```text
tools/post_render_pipeline/exr/exr_save_masks_test.py
```

mask output was changed from OpenCV to Pillow:

```python
Image.fromarray(image_data, mode="L").save(
    output_path, format="PNG", compress_level=9
)
```

This was validated against an EXR containing the corrected
`ActorHitProxyMask00.R` channel. OpenCV works in the repaired environment, but
the Pillow writer is retained as a robust greyscale PNG writer.

## 10. Python environment contamination and safe repair

### 10.1 What broke the original environment

Do not install OpenEXR or OpenImageIO into the main BEDLAM Python environment
with Conda. This command was run on 25 July 2026 and caused the breakage:

```bash
/users/kelvin/miniconda3/bin/conda install -c conda-forge openexr openimageio
```

The transaction installed NumPy 1.26.4, OpenEXR 3.1.11, and OpenImageIO
2.2.18 over an environment that already contained pip-installed NumPy 2.2.6.
Package records later reported NumPy 2.2.6 while Python actually imported
NumPy 1.26.4 from overlapping files. SciPy 1.15.3 and scikit-learn 1.7.2 had
been installed for NumPy 2.x, causing:

```text
ValueError: All ufuncs must have type `numpy.ufunc`.
```

This was an environment-management error, not a dataset, renderer, or vis-PC
problem. `conda list` alone is insufficient after pip/Conda file overlap;
import packages and print both their versions and paths.

The known-good local workstation used Python 3.12, NumPy 2.2.6, SciPy 1.17.0,
scikit-learn 1.8.0, and OpenEXR Python 3.4.4. Its `oiiotool` 2.4.17 and
`exrheader` were system commands. The cluster's exact SciPy/sklearn versions
need not match, provided they import against the selected NumPy ABI. Keep the
CLI tools separate from the Python environment.

### 10.2 Recreate the repaired clone

Preserve the original environment for rollback and clone it:

```bash
/users/kelvin/miniconda3/bin/conda create \
  --clone /users/kelvin/miniconda3/envs/bedlam2 \
  -p /users/kelvin/miniconda3/envs/bedlam2-repaired \
  -y
```

The clone is approximately 4.8 GB and can take several minutes. Save package
inventories before changing it:

```bash
/users/kelvin/miniconda3/bin/conda list \
  -p /users/kelvin/miniconda3/envs/bedlam2-repaired \
  > /tmp/bedlam2-repaired-conda-before.txt

/users/kelvin/miniconda3/envs/bedlam2-repaired/bin/python -m pip freeze \
  > /tmp/bedlam2-repaired-pip-before.txt
```

A normal Conda removal dry-run proposed unrelated Boost, ICU, and libxml
changes. Remove only the three conflicting Conda-owned packages:

```bash
/users/kelvin/miniconda3/bin/conda remove \
  -p /users/kelvin/miniconda3/envs/bedlam2-repaired \
  openimageio openexr numpy \
  --force-remove -y
```

Then restore the required pip packages and their files:

```bash
/users/kelvin/miniconda3/envs/bedlam2-repaired/bin/python -m pip install \
  --force-reinstall \
  --no-cache-dir \
  "numpy==2.2.6" \
  "OpenEXR==3.4.4" \
  "opencv-python-headless==4.12.0.88"
```

This was done only in `bedlam2-repaired`. The original `bedlam2` environment
remains available but broken.

### 10.3 Validate the repaired environment

```bash
conda activate /users/kelvin/miniconda3/envs/bedlam2-repaired

python - <<'PY'
import numpy
import scipy
import sklearn
import OpenEXR
import cv2
import torch
import kaolin
from scipy.spatial import cKDTree

print("numpy", numpy.__version__, numpy.__file__)
print("scipy", scipy.__version__, scipy.__file__)
print("sklearn", sklearn.__version__, sklearn.__file__)
print("OpenEXR", OpenEXR.__version__, OpenEXR.__file__)
print("cv2", cv2.__version__, cv2.__file__)
print("torch", torch.__version__)
print("kaolin", kaolin.__version__)
print("cKDTree import: OK")
PY
```

Validated cluster versions were NumPy 2.2.6, SciPy 1.15.3,
scikit-learn 1.7.2, OpenEXR 3.4.4, OpenCV 4.12.0, Torch 2.4.0+cu121,
and Kaolin 0.18.0. The vis-PC import chain and the metadata, mask, image-layer,
and depth-layer extractors all passed.

`pip check` may report pre-existing optional `diffsynth` or `gpustat`
requirements. Those warnings were not introduced by this repair and did not
block the tested pipeline.

## 11. Running post-processing

Activate the repaired Python environment and expose the isolated CLI tools:

```bash
conda activate /users/kelvin/miniconda3/envs/bedlam2-repaired
export PATH="/users/kelvin/miniconda3/envs/bedlam-oiio-tools/bin:$PATH"

which python
python -c 'import numpy; print(numpy.__version__)'
command -v oiiotool
command -v exrheader

cd /athenahomes/kelvin/projects/Syn4D/Syn4d_renderer/tools/post_render_pipeline

bash be_post_render_pipeline_watch.sh \
  /work/kelvin/bedlam2/images/kaggle_eval/sim/outpost_ue53_bedlam_temporal1 \
  landscape \
  extract_layers \
  extract_masks \
  --workers 2
```

The watcher requires:

- both image and depth pass directories;
- a quiet window after the last file write;
- `post_ready/<sequence>.done`;
- no existing per-sequence lock.

On success it:

- extracts EXR metadata and camera CSVs;
- extracts RGB and depth layers;
- extracts environment/object masks;
- moves/copies final PNGs into the dataset layout;
- removes the ten warm-up frames;
- deletes source EXRs;
- writes `.post_render_processed/<sequence>.done`;
- removes the `post_ready` marker;
- prints `Done: <sequence> (Deleted EXR files: ...)`.

Because watch mode is designed to wait for future sequences, it does not print
a global “everything done” message and normally keeps polling.

## 12. Running vis-PC

Use the active repaired interpreter:

```bash
conda activate /users/kelvin/miniconda3/envs/bedlam2-repaired
cd /athenahomes/kelvin/projects/Syn4D/Syn4d_renderer

python vis_pc_multiview_seg_obj_process_barycentric_final_clean_vgg_single.py \
  --dataset_root /work/kelvin/bedlam2/images/kaggle_eval/sim \
  --scene_name outpost_ue53_bedlam_temporal1 \
  --metadata_root /scratch/shared/beegfs/zeren/Syn4D/metadata \
  --fallback_metadata_root /scratch/shared/beegfs/kelvin/Syn4D/metadata \
  --stride 1 \
  --rgb-source png \
  --tracking-output-format sparse_safetensor \
  --no-clip-barycentric
```

An activated environment does not override an explicitly named interpreter.
Do not invoke `/users/kelvin/miniconda3/envs/bedlam2/bin/python`: that selects
the broken original even if the prompt says `(bedlam2-repaired)`.
`which python` must report:

```text
/users/kelvin/miniconda3/envs/bedlam2-repaired/bin/python
```

## 13. Interrupted watcher and stale locks

The lock is a directory:

```text
.post_render_locks/<sequence>.lock
```

An interrupted process may leave it behind. Before removing it, confirm no
watcher or extractor is running:

```bash
pgrep -af \
  '[b]e_post_render_pipeline_watch.sh|[e]xr_save_masks_test.py|[e]xr_save_layers.sh'
```

Then remove only the confirmed empty stale lock:

```bash
rmdir \
  /work/kelvin/bedlam2/images/kaggle_eval/sim/outpost_ue53_bedlam_temporal1/.post_render_locks/seq_000000_0.lock
```

Do not remove the manifest or `post_ready` marker merely because a lock is
stale.

## 14. Validation checklist

Before post-processing:

```bash
ROOT=/work/kelvin/bedlam2/images/kaggle_eval/sim/outpost_ue53_bedlam_temporal1

find "$ROOT/exr_image/seq_000000_0" -name '*.exr' | wc -l
find "$ROOT/exr_image/seq_000000_0" -name '*.png' | wc -l
find "$ROOT/exr_depth/seq_000000_0" -name '*.exr' | wc -l
cat "$ROOT/post_ready/seq_000000_0.done"
```

Expected full-render counts are 202, 202, and 202.

Check one depth EXR:

```bash
exrheader "$ROOT/exr_depth/seq_000000_0/seq_000000_0_0000.exr" |
  grep -E 'ActorHitProxyMask00.R|FinalImageMovieRenderQueue_WorldDepth.R'
```

Check centre camera metadata in an image EXR:

```bash
exrheader "$ROOT/exr_image/seq_000000_0/seq_000000_0_0000.exr" |
  grep -E 'unreal/camera/bedlam/subframe_0|unreal/camera/cur(Pos|Rot)'
```

With the queue's temporal count of 1, the `curPos` and `curRot` values must
match `subframe_0`, and their `info` fields must say
`Center subframe camera ground truth`.

After post-processing, a successful single-sequence run should have:

```text
192 final PNGs
192 extracted image layers
192 extracted depth layers
ground_truth/meta_exr_csv/<sequence>_camera.csv
ground_truth/meta_exr_depth_csv/<sequence>_camera.csv
.post_render_processed/<sequence>.done
```

The source image/depth EXRs and `post_ready` marker should be gone only after
successful processing.

## 15. Known harmless or unrelated messages

- `Unable to initialize Vulkan` on a login node means the render was not run
  inside a GPU allocation.
- Missing audio capture/PulseAudio messages are irrelevant to silent rendering.
- `ViewportInfo could not be found for Window` is noisy offscreen PIE logging.
- The ShowCase window-attachment construction warnings pre-existed and did not
  prevent rendering.
- MRQ emits noisy `Unable to statfs(...{ext})` checks while determining output
  filenames; successful jobs and output counts are the authoritative result.

## 16. Current successful result

The corrected temporal-count-1 render is:

```text
/work/kelvin/bedlam2/images/kaggle_eval/sim/outpost_ue53_bedlam_temporal1
```

It completed both MRQ jobs with 202 PNGs, 202 image EXRs, 202 depth EXRs, and
the completion marker. Its object motion was visually compared with the good
UE 5.4 render and no longer showed the forced-seven-sample rotation problem.
At the time of this update it had not yet been post-processed, so its source
EXRs remained available.

The earlier end-to-end post-processing test was:

```text
/work/kelvin/bedlam2/images/kaggle_eval/sim/outpost_ue53_bedlam_full
```

That test produced 192 dataset frames, RGB/depth layers, 3,709 masks, two
camera CSV files, and an MP4, proving the Linux post-processing workflow.
However, it was rendered with the unnecessary forced temporal count of 7 and
must not be used as the corrected object-motion result.

## 17. Windows/Linux RGB consistency audit

Reference frames:

```text
Windows:
/work/kelvin/bedlam2/images/kaggle_eval/sim/outpost_windows_reference/png/seq_000000_0

Linux UE 5.3 corrected render:
/work/kelvin/bedlam2/images/kaggle_eval/sim/outpost_ue53_bedlam_temporal1/png/seq_000000_0
```

Both sets contain 192 RGBA PNGs at 1280x720. Frame matching and phase
correlation found no meaningful image translation. Across all 176,947,200
pixels, the absolute RGB error was:

```text
mean per pixel, averaged over RGB:  2.029 / 255
median:                             0.667 / 255
95th percentile:                    8.333 / 255
99th percentile:                   25.000 / 255
maximum:                           255.000 / 255
PSNR:                               31.864 dB
mean SSIM:                           0.98856
```

The mean signed Linux-minus-Windows bias was only `(R +0.075, G +0.103,
B +0.124)`. Per-channel linear slopes were approximately 0.995--0.997.
Therefore this is not principally a global exposure, gamma, white-balance, or
color-grade mismatch.

A 3x3 RGB affine transform and a per-channel cubic curve were trained on one
set of frames and tested on unseen frames. They made mean error approximately
4--5 percent worse. Do not apply a fitted LUT, channel gain, or gamma adjustment
to these files: it cannot correct the dominant residual.

The error correlates strongly with image detail:

```text
Sobel-gradient range     Pixel fraction     Mean RGB MAE
0--2                       2.57%               0.49
2--8                       9.09%               0.82
8--20                     15.67%               1.07
20--50                    24.17%               1.51
50+                       48.49%               2.92
```

Blurred comparisons also reduce the error materially. The residual is
concentrated around geometry edges, texture detail, highlights, reflections,
shadows, and other high-frequency features. It is principally a renderer/RHI
and sampling-equivalence problem, not an output color-space problem.

### Current authored and runtime state

- Linux UE is 5.3.2, changelist 29314046, using `VULKAN_SM5`.
- The inspected GPU used NVIDIA Vulkan driver 595.71.05.
- Windows has `DefaultGraphicsRHI=DefaultGraphicsRHI_Default`; its actual RHI
  was not recorded. The copied Windows editor state shows D3D11, D3D12, and
  Vulkan target formats enabled, but that does not prove which RHI rendered.
- WindowsEditor and LinuxEditor saved scalability groups are identical: every
  quality group is 3 and resolution quality is 0.
- The RGB MRQ job uses one spatial sample, one temporal sample, explicitly
  overrides anti-aliasing to None, and uses 32 engine/render warm-up frames.
- The queue has no explicit MRQ Console Variables, Color Output, or Game
  Overrides setting.
- The launcher forces Vulkan, disables texture streaming, and applies the two
  synchronous tick CVars plus the camera tick prerequisite.
- The launcher default for `BEDLAM_RUNTIME_IMAGE_TEMPORAL_SAMPLES` is now 0,
  meaning it leaves the queue's saved temporal count unchanged.
- The camera post-process blend weight is 1. It fixes exposure to Manual,
  exposure bias 0, and disables physical-camera exposure. Its RGB saturation,
  contrast, gamma, gain, and offset are neutral. Bloom and vignette are
  overridden to zero. These settings are consistent with the negligible global
  color bias measured in the PNGs.
- ShowCase loads DayLight, OverCast, Night, and Sunset lighting sublevels.
  They contain different unbound post-process volumes and strong, different
  color grades. The active streaming-level visibility must be logged inside
  the MRQ PIE world. The present close match indicates that a completely wrong
  lighting level is unlikely, but startup-editor inspection alone cannot prove
  the effective runtime blend.

### Recommended consistency experiments, in order

1. On Windows, capture the render log and record the engine version/changelist,
   `RHIName`, shader platform, GPU and driver, active device profile, and all
   MRQ settings. Do not compare against a Windows render whose actual RHI is
   unknown.
2. Render the same short frame range on Windows with Vulkan. This is the most
   direct RHI-matched comparison with Linux. Keep temporal count 1 and every
   other queue setting unchanged.
3. If both systems must use their native RHIs, test spatial sample count 8 with
   temporal count 1 and AA method None on both. This averages subpixel
   raster/specular differences without reintroducing fractional-time object
   evaluation. Do not force temporal count 7.
4. Pin the complete render state in an MRQ Console Variables setting or a
   versioned render preset: scalability groups, screen percentage, GI,
   reflection method, shadow method/quality, SSR, AO, texture filtering,
   motion blur, DOF, bloom, vignette, eye adaptation, tone mapper, scene-color
   format, GBuffer format, and material quality. Record resolved values in each
   render log.
5. Log the visible streaming levels and effective camera/post-process settings
   after PIE starts and at the first rendered frame.
6. For future scientific comparisons, retain a linear multilayer EXR as the
   canonical RGB source and generate display PNGs through one explicit,
   versioned OCIO transform on the same post-processing environment. This
   standardizes transfer function and quantization, but does not eliminate
   Vulkan-versus-D3D shading differences.
7. Only after the RHI-matched and spatial-sampling tests should individual
   screen-space effects be isolated. Test reflections/SSR first, then shadows,
   AO, fog/atmosphere, and finally material normal/specular response. Use
   one-factor-at-a-time short renders and compare the same frames.

Exact byte-for-byte equality is not a realistic requirement across Vulkan and
D3D for this deferred, screen-space-heavy scene. For strict reproducibility,
use the same UE build, RHI/shader model, GPU architecture and driver, MRQ
preset, project assets, and post-processing transform. A practical acceptance
threshold should be defined from the downstream task rather than from visual
similarity alone.
