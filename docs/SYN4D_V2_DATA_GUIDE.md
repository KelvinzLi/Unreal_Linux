# Syn4D V2 data layout and usage guide

Inventory date: 25 November 2026.

Syn4D V2 contains three main collections: simulated mixed scenes, corrected variable-length scenes without physics simulation, and fixed-position rotating-camera scenes for novel-view synthesis and outpainting. Together they contain **5,800 camera videos**. RGB, depth, camera calibration, object identities and motion, sparse pixel-to-mesh tracking, and companion attachment data support RGB-D reconstruction and time-dependent point tracking.

The essential distinction is that **tracking safetensors are not dense XYZ trajectories**. They associate source pixels with faces of animated meshes. The attachment files add barycentric coordinates and signed plane distances. Reconstructing trajectories requires the corresponding mesh animation NPZs and the scene placement transforms. A video alone, or an attachment file alone, is insufficient.

## Contents

1. [Roots and dataset selection](#roots-and-dataset-selection)
2. [Dataset sizes and scene coverage](#dataset-sizes-and-scene-coverage)
3. [Complete V2 root directory catalogue](#complete-v2-root-directory-catalogue)
4. [Scene and sequence layout](#scene-and-sequence-layout)
5. [Camera conventions and depth](#camera-conventions-and-depth)
6. [Masks and identity](#masks-and-identity)
7. [Mesh metadata and animation alignment](#mesh-metadata-and-animation-alignment)
8. [Tracking and attachment schemas](#tracking-and-attachment-schemas)
9. [Reconstructing and using tracks](#reconstructing-and-using-tracks)
10. [Visualization commands](#visualization-commands)
11. [Quality limitations and validation](#quality-limitations-and-validation)
12. [Packing downloading and publication](#packing-downloading-and-publication)
13. [Pipeline and maintenance scripts](#pipeline-and-maintenance-scripts)
14. [Commit state and evidence](#commit-state-and-evidence)

## Roots and dataset selection

All dataset-relative paths below are relative to:

```text
/scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2
```

| Purpose | Absolute path |
| --- | --- |
| Simulated mixed production data | `/scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2/mixed` |
| Corrected no-simulation production data | `/scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2/mixed_no_sim_corrected` |
| NVS and outpainting production data | `/scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2/nvs_outpaint` |
| Corrected object animation metadata | `/scratch/shared/beegfs/kelvin/Syn4D/metadata/new_weight_bone` |
| Shared BEDLAM body metadata | `/scratch/shared/beegfs/zeren/Syn4D/metadata/bedlam2_smpl_npz` |
| Shared BEDLAM clothing metadata | `/scratch/shared/beegfs/zeren/Syn4D/metadata/b2_assetdata_download/clothing/npz` |
| Renderer source | `/athenahomes/kelvin/projects/Syn4D/Syn4d_renderer` |
| Linux orchestration source | `/athenahomes/kelvin/projects/Syn4D/unreal_linux` |
| Dataset-facing viewer source | `/athenahomes/kelvin/projects/Syn4D/Syn4D/code/visualizer` |
| Local viewer and reader source | `/athenahomes/kelvin/projects/Syn4D/syn4d_vis/visual_track_multiple` |
| Offline visualization scripts | `/athenahomes/kelvin/projects/Syn4D/Syn4D_plots` |

**Use `mixed_no_sim_corrected`, not `mixed_no_sim`, for the completed corrected no-sim collection.** The latter is an earlier partial run. The remote upload script deliberately calls the corrected collection `V2/mixed_no_sim`; this is a naming mapping, not a different production dataset.

World-benchmark data is separate: `/scratch/shared/beegfs/kelvin/Syn4D/subsets/world_bench`. It is not included in the V2 totals or the scene table below. Likewise, V1, Kaggle evaluation and Objaverse filtering/review datasets outside this root are not additional V2 splits.

## Dataset sizes and scene coverage

The following are current directory counts. For every listed video, the inventory found the same sequence name in RGB and depth camera CSVs, tracking shard/index/log files, and attachment shard/index/log files. This is a **presence and naming audit**, not a full decode, checksum or geometry audit of every payload.

| Collection | Environments | Independent setups per environment | Cameras per setup | Videos | Frames per video | Camera frame rows total |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| `mixed` | 30 | 10 | 8 | 2,400 | 192 | 460,800 |
| `mixed_no_sim_corrected` | 30 | 10 | 8 | 2,400 | 63–480; median 140 | 453,464 |
| `nvs_outpaint` | 20 | 50 | 1 | 1,000 | 192 | 192,000 |
| Total | 30 distinct environments | 1,600 setups across collections | — | 5,800 | — | 1,106,264 |

The intended production resolution is 1280×720 at 30 FPS. Sample depth headers and tracking record dimensions confirm 1280×720; the corrected no-sim Hangar `seq_000000_0` MP4 header confirms 30 FPS and 166 frames, matching its camera CSV. A 192-frame video is 6.4 seconds. Frame indices are zero-based: its final stored frame is **191**, not 192. Duration should always come from the actual sequence metadata or camera CSV rather than the split name.

### Scene inventory

Both mixed collections contain all 30 environments. NVS uses the following 20; Gasstation is included and Aztec is not.

| Scene | Mixed videos | Corrected no-sim videos | No-sim frame range | NVS videos |
| --- | ---: | ---: | --- | ---: |
| aztec | 80 | 80 | 74–480 | — |
| boxing | 80 | 80 | 109–278 | — |
| bureau | 80 | 80 | 74–480 | 50 |
| carnival | 80 | 80 | 74–480 | 50 |
| cartoonnight | 80 | 80 | 65–306 | 50 |
| citynight | 80 | 80 | 68–480 | 50 |
| containers | 80 | 80 | 63–480 | 50 |
| courtyard | 80 | 80 | 121–360 | — |
| depot | 80 | 80 | 68–381 | — |
| gallery | 80 | 80 | 77–438 | — |
| gasstation | 80 | 80 | 87–480 | 50 |
| greekstreet | 80 | 80 | 99–183 | — |
| hangar | 80 | 80 | 130–480 | 50 |
| harbour | 80 | 80 | 65–367 | 50 |
| hotel | 80 | 80 | 69–480 | — |
| mall | 80 | 80 | 118–335 | 50 |
| medieval | 80 | 80 | 66–480 | — |
| metro | 80 | 80 | 79–480 | 50 |
| modsci | 80 | 80 | 78–480 | — |
| nyc | 80 | 80 | 68–253 | 50 |
| oakforest | 80 | 80 | 65–306 | 50 |
| parking | 80 | 80 | 64–218 | — |
| roman | 80 | 80 | 87–480 | 50 |
| scandivillage | 80 | 80 | 77–480 | 50 |
| scifihangar | 80 | 80 | 87–480 | 50 |
| smalltown | 80 | 80 | 73–480 | 50 |
| snowtown | 80 | 80 | 65–252 | 50 |
| urbancity | 80 | 80 | 82–480 | 50 |
| wasteland | 80 | 80 | 71–480 | 50 |
| woodland | 80 | 80 | 69–480 | 50 |

### What distinguishes the collections

**Mixed:** each setup starts from one BEDLAM human and three placement-sampled animated objects, with additional simulated objects recorded in the final scene CSV. Do not assume there are only three objects in the rendered scene or that every object is Objaverse: simulation metadata also references other groups, including GSO. The eight camera views reuse the same physical setup. Object uniqueness at setup allocation does not mean an object occurs in only one camera video.

**Corrected no-sim:** one BEDLAM human and three animated objects per setup, without the physics-simulation stage. This does **not** mean a static scene: source animations and sampled object global motion still play. Duration is the longest window all non-looping sources can cover: the minimum of the BEDLAM usable length and each non-looping object's usable length. The object pipeline drops source frame zero, so a 64-source-frame non-looping object may yield a 63-frame rendered clip. Looping objects can repeat and do not set the limiting length. Do not change playback speed to force all clips to 192 frames.

The corrected no-sim allocation explicitly uses a measured scale-ratio interval of `[0.8, 1.2]`. The original restored `mixed` collection is not thereby retroactively resampled or revalidated against that corrected allocation.

Both mixed collections use the mixed-camera sampler: paired versus orthogonal layout weight 8:2; moving orbit versus dolly weight 8:2; paired cameras follow moving `body_0` with shared sampled shake; orthogonal cameras target a fixed `cameraroot` without shake. The saved global camera summaries report 228 paired/72 orthogonal groups for mixed and 242/58 for corrected no-sim. These are realized layout **group counts**, not counts of camera-motion types. Sampling and collision rejection mean exact 80/20 counts are not guaranteed. Read each sequence's camera info instead of assigning a mode from its suffix.

The production mixed recipes use RGB spatial AA16, depth spatial AA1 and motion blur enabled. Separate RGB/depth render jobs must maintain matching camera evaluation. MP4 GOP25 means a keyframe interval for seeking, **not** 25-frame video files, 25 FPS, or a tracking stride of 25.

**NVS/outpainting:** ten distinct Objaverse objects within each setup, no BEDLAM human and no added object global motion; intrinsic object animations still play. Objects can repeat across different setups and earlier datasets. The configured pool has 1,516 entries. Camera centres are sampled in a 2 m disk about the scene centre, with 4 m object-placement exclusion, 90 cm camera height, 60° horizontal FOV, 192 frames, AA16/AA1 and no motion blur. Placement expands in a circle, starting at 4.5 m radius; later attempts use 0.2 m expansion steps per 100 attempts. The exclusion is based on placement footprints, not a guarantee of unobstructed 3D sightlines or perfectly uniform final positions.

NVS samples `full`, `half-return`, or `quarter-reverse`, each with either direction sign:

| Pattern | Relative yaw milestones before applying direction sign |
| --- | --- |
| `full` | 0 → 360° |
| `half-return` | 0 → 180° → 0 |
| `quarter-reverse` | 0 → 90° → −90° → 0 |

The last row is a 90° turn, a 180° reversal, then a 90° return. A separate seeded stream samples initial facing in `[0, 360)`. The production notes record that 11 already-completed videos retained their earlier fixed heading when this policy was introduced; inspect recorded camera data rather than assuming all 1,000 starts were randomized. Rotation is driven by an animated `Type=Empty`, `Body=empty_focus` look-at target. The camera position remains fixed within each clip. A constant camera-root transform in the camera JSON therefore does not imply a static viewing direction.

## Complete V2 root directory catalogue

This table covers every top-level directory observed in the V2 root on the inventory date.

| Relative directory | Content and appropriate use |
| --- | --- |
| `mixed` | Original simulated mixed production scenes, 80 camera sequences each. Includes orchestration and recovery state. |
| `mixed_attachments` | Matching attachment sidecars, under `<scene>/tracking_attachments_safetensors`. |
| `mixed_archives` | Thirty `<scene>.tar.zst` data archives; about 0.976 decimal TB in total. |
| `mixed_attachments_archives` | Thirty separate attachment archives; about 1.085 TB. |
| `mixed_no_sim_corrected` | Corrected, completed variable-length no-simulation data. |
| `mixed_no_sim_corrected_attachments` | Matching no-sim attachment sidecars. |
| `mixed_no_sim_corrected_archives` | Thirty corrected no-sim data archives; about 0.821 TB. |
| `mixed_no_sim_corrected_attachments_archives` | Thirty corrected no-sim attachment archives; about 0.555 TB. |
| `nvs_outpaint` | Assembled 20-scene, 1,000-video collection plus source batches, setup records and experiments. |
| `nvs_outpaint_attachments` | Matching NVS attachment sidecars for all 1,000 sequences. No sibling NVS archive root was present. |
| `mixed_no_sim` | Earlier partial no-sim run: nine scene directories plus inputs/projects/queue. Not the corrected release. |
| `_maps` | Original 30-scene placement maps plus `_cached`. Contains valid placement, missing-ground and obstacle masks, map geometry JSON and generation logs. Not rendered training depth. |
| `_mixed_before_corrected_20260913_metadata` | Per-scene metadata recovery snapshot, allocation and cleanup manifest. This is not a complete RGB/depth/tracking backup. |
| `_mixed_cleanup_guard_stopped_20260913` | Historical cleanup guard containing `.cleanup_pending`. Not a training artifact or proof a cleanup is running now. |
| `_mixed_no_sim_duration_smoke_20260912` | `short` and `long` duration experiments. |
| `_mixed_no_sim_duration_smoke_20260912_materials_v2` | Revised `short` and `long` smoke experiments with corrected material selection. |
| `_packing_no_sim_6` | Packing-claim area, empty at inspection. |
| `_packing_original_mixed_10` | Original mixed packing-claim area, empty at inspection. |
| `_upload_motionplayground` | Four upload locks and timestamped upload logs. These are local records, not a live remote integrity check. |

Archive sizes above are sums of existing archive file sizes, not recursive usage estimates of unpacked source data. Keeping source and archives consumes storage for both.

### Operational folders inside production roots

In `mixed`: `_allocation` and `_inputs` preserve asset selection and intermediate scene inputs; `_pipeline_logs` records preparation; `_render_queue`, `_recovery_queue` and `_vispc_queue` record worker ownership/status/logs; `_recovery_projects` contains project state for resumed rendering.

In `mixed_no_sim_corrected`: `_inputs`, `_projects`, `_queue` and `_vispc_queue` serve the corresponding placement, isolated-project, render/preparation and tracking roles.

In `nvs_outpaint`:

- `configuration.json` and `whitelist.txt` preserve production settings and the pool.
- `_queue` records per-setup work; `_batch_queue` records batched preparation/rendering; `_vispc_queue` records scene-level tracking jobs.
- `_batches/<scene>/batch_*` contains actual batch render files and metadata.
- `<scene>/setup_*` contains individual placement attempts and some original render outputs.
- `<scene>/assembly_manifest.json` maps each assembled sequence back to its source output directory.
- `_batch_smoke`, `_heading_smoke_v1`, `_heading_smoke_single_v1`, `_vispc_smoke_6class` are smoke tests.
- `_foliage_coverage_test`, `_foliage_hitproxy_test`, `_foliage_disabled_test`, `_foliage_vispc_test` contain isolated foliage experiments; they do not automatically replace production scenes.

**Do not delete NVS `_batches` or setup outputs as disposable intermediates.** The assembled scene's MP4, PNG, depth, masks and camera metadata frequently symlink to them. Copying only links or deleting targets makes the assembled dataset unusable. Ordinary mixed/no-sim examples inspected were physical scene files; NVS examples were links.

The expanded placement maps used by NVS are outside this root:

```text
/scratch/shared/beegfs/kelvin/Syn4D/subsets/_empty_focus_maps_10m_20260930
```

## Scene and sequence layout

For example, the simulated Hangar scene is:

```text
/scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2/mixed/hangar
├── be_seq.csv
├── be_seq_transform_channels.json
├── be_camera_animations.json
├── be_seq_base.csv                         # intermediate, when present
├── be_seq_sim.csv                          # simulated mixed intermediate
├── be_seq_mixed8.csv                       # camera-expanded intermediate
├── mp4/seq_000000_0.mp4
├── png/seq_000000_0/seq_000000_0_0000.png
├── exr_layers/
│   ├── depth/seq_000000_0/seq_000000_0_0000_depth.exr
│   ├── masks/seq_000000_0/...
│   └── image/seq_000000_0/...               # extracted RGB EXR intermediate
├── ground_truth/
│   ├── meta_exr_csv/seq_000000_0_camera.csv
│   ├── meta_exr_depth_csv/seq_000000_0_camera.csv
│   ├── meta_exr/seq_000000_0/*_meta.json
│   └── meta_exr_depth/seq_000000_0/*_meta.json
├── tracking_safetensors/
│   ├── seq_000000_0.safetensors
│   ├── seq_000000_0_index.json
│   └── seq_000000_0_log.json
├── exr_image/                              # raw MRQ intermediates
├── exr_depth/                              # raw MRQ intermediates
├── unreal_assets/
├── unreal_logs/
└── .post_render_processed/seq_000000_0.done
```

Companion attachment paths deliberately live outside the main scene:

```text
.../Syn4D_V2/mixed_attachments/hangar/tracking_attachments_safetensors/
    seq_000000_0.safetensors
    seq_000000_0_index.json
    seq_000000_0_log.json
```

Replace `mixed` with `mixed_no_sim_corrected` or `nvs_outpaint` and use the corresponding `_attachments` sibling for the other collections.

### Naming and scene metadata

`seq_000008_4` means setup 8, camera slot 4 **within that scene and split**. A frame stem such as `seq_000008_4_0191` adds zero-based frame 191. The same sequence name in another scene/split does not identify the same animation. Mixed setups have slots 0–7. NVS has 50 different setups, each using slot 0; adjacent NVS videos are not alternate cameras of the same setup.

| File | Role |
| --- | --- |
| `be_seq.csv` | Final authoritative render input: Group rows identify sequences and frame counts; Body/Object rows identify sources and placement; Empty rows can animate camera targets. |
| `be_seq_transform_channels.json` | Evaluated per-sequence transform records and the map target's world offset; required by geometry reconstruction. Indexed by sequence and object index, not by arbitrary row position. |
| `be_camera_animations.json` | Intended camera controls, keyframes, look-at targets, shake and sampling info. Not a replacement for recorded render-time camera CSVs. |
| `be_seq_base.csv` | Placement output before simulation/camera expansion. Not sufficient to reconstruct a final simulated render. |
| `be_seq_sim.csv` | Physics-result motion and additional objects before camera expansion. |
| `be_seq_mixed8.csv` | Expanded eight-camera scene description. Prefer the finalized `be_seq.csv` for readers. |
| `assembly_manifest.json` | NVS source-directory mapping; establishes where linked media physically lives. |
| `.post_render_processed/*.done` | Postprocessing bookkeeping; does not certify tracking accuracy. |

CSV fields include `Index,Type,Body,X,Y,Z,Yaw,Pitch,Roll,Shift,Scale,Comment,PerFrameMotion`. `Comment` is semicolon-delimited `key=value` metadata; `PerFrameMotion` can be a long JSON array. Set a sufficiently high `csv.field_size_limit` when using Python CSV readers. Do not split CSV lines manually on commas.

`Type=Empty` is a non-rendering actor, not an object mask or an animated mesh dependency. NVS uses it to control the camera's viewing direction while keeping the camera centre fixed.

## Camera conventions and depth

### Recorded camera metadata

Each camera CSV has one row per image, keyed by `name`:

```text
name,x,y,z,yaw,pitch,roll,focal_length,sensor_width,sensor_height,hfov
```

- `x,y,z`: Unreal world-space camera location in centimetres.
- `yaw,pitch,roll,hfov`: degrees.
- Focal length and sensor dimensions: matching physical lens units, used as ratios to derive pixel focal lengths.
- `meta_exr_csv` describes the RGB pass; `meta_exr_depth_csv` describes the depth pass.
- Per-frame JSON preserves additional EXR metadata. Use the CSV for ordinary loading and JSON for render diagnostics.

Use the **recorded** camera pose rather than re-evaluating the planned camera JSON: look-at tracking, shake, interpolation and warmup can affect the actual pose. When checking pass alignment, compare translations and full rotations, with angular wraparound handled correctly. Numerical roundoff is not a mismatch. A successful render process alone does not prove RGB and depth agree.

### Depth storage

Use `exr_layers/depth/<seq>/<frame_stem>_depth.exr`. The channel is named **`Depth`**, not necessarily `R`. A sampled production file stores this channel as HALF (16-bit floating point); OpenEXR can decode it to float32. Float32 decoding does not restore precision lost during half-precision storage.

The reader divides depth by 100 to obtain metres and treats it as **camera-axis Z depth**, not Euclidean ray length. Camera translations must also be divided by 100. Depth is not normalized to `[0,1]`, not inverse depth and not log depth. A colourized depth preview is not training depth.

For native width `W`, height `H`, focal length `f`, sensor dimensions `sw,sh`:

```text
fx = f / sw * W                  fy = f / sh * H
cx = W / 2                      cy = H / 2
Xcamera = ((u-cx)*Z/fx, (v-cy)*Z/fy, Z)
Xworld = Rcamera_to_world @ Xcamera + tcamera_to_world
```

Do not substitute `(W−1)/2` for the principal point if reproducing this pipeline exactly. After a crop or resize, update intrinsics consistently; face-ID pixel indices remain defined at the original record resolution.

The camera-coordinate basis is x-right, y-down, z-forward. Unreal world coordinates are x-forward, y-right, z-up. The existing reader uses a convention-specific Euler conversion:

```text
Rcamera_to_world = Ryaw @ Rpitch @ Rroll @ [[0,0,1],[1,0,0],[0,-1,0]]
```

Pitch/roll signs are defined by the implementation, not by a generic Euler helper. Reuse `euler_to_rotation_matrix` and `depth_to_world` in:

```text
/athenahomes/kelvin/projects/Syn4D/Syn4D_plots/render_static_pointcloud_camera_path.py
```

or the corresponding methods in `Syn4D/code/visualizer/syn4d_track.py`. `camera_pose` is camera-to-world; invert it to project world points into an image. Object and BEDLAM transforms use different source-axis conversions from the camera conversion.

### Minimal depth reader

Run in an environment with NumPy, OpenEXR and Imath; this only reads one frame:

```python
from pathlib import Path
import numpy as np
import OpenEXR, Imath

p = Path('/scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2/mixed/hangar/'
         'exr_layers/depth/seq_000000_0/seq_000000_0_0000_depth.exr')
f = OpenEXR.InputFile(str(p))
dw = f.header()['displayWindow']
w = dw.max.x - dw.min.x + 1
h = dw.max.y - dw.min.y + 1
depth_m = np.frombuffer(
    f.channel('Depth', Imath.PixelType(Imath.PixelType.FLOAT)),
    dtype=np.float32,
).reshape(h, w) / 100.0
f.close()
valid = np.isfinite(depth_m) & (depth_m > 0)
```

The standard viewer additionally limits very distant depth (300 m) and applies its tracking validity policy. These are reader decisions, not the EXR's storage format. Sky, invalid depth and non-finite values must not become valid points at the world origin.

## Masks and identity

Raw masks live under `exr_layers/masks/<seq>`. Typical filenames are:

```text
seq_000000_0_0000_00_body.png
seq_000000_0_0000_00_clothing.png
seq_000000_0_0000obj_01.png
seq_000000_0_0000_env.png
```

The missing underscore before `obj_01` is intentional in the existing naming convention. Tracking record keys use the logical names `_00_body`, `_00_clothing` and `obj_01`. Read the index and final CSV rather than guessing object identity from a filename alone.

Mixed/no-sim object masks generally start at `obj_01` because a BEDLAM body is present; object-only NVS starts at `obj_00`. The loader infers the object-mask offset. Empty camera targets do not consume mesh masks. Environment masks identify background and are used for static-background tracking.

Absent masks can mean the object is off-screen or occluded. They do not automatically indicate a corrupt asset. Conversely, a nonempty mask does not guarantee correct depth ownership: foliage/transparent-material cases can label pixels as belonging to an object behind foreground vegetation.

Some packaging workflows support `env_mask_safetensors/<seq>.safetensors` with an index. Its tensors contain concatenated **encoded PNG bytes** (`png_bytes_values`, uint8) plus offsets, not decoded H×W arrays. Slice bytes and decode the PNG. This is an optional packaging representation; the inspected V2 scene examples still have raw masks, and this guide does not assume they were converted to environment-mask shards.

## Mesh metadata and animation alignment

### Object metadata

For an Object row with `object_group=000-063` and a particular ID:

```text
/scratch/shared/beegfs/kelvin/Syn4D/metadata/new_weight_bone/
    000-063/<object_id>/vertices_sequence.npz
```

GSO uses the same group/object/NPZ pattern with its own group value. Core arrays are `vertices_seq` (time × vertices × xyz) and `faces` (triangles × three vertex indices). Source mesh vertices are used in metres; the placement scale is dimensionless. Face order and topology are part of the tracking contract: a topologically equivalent re-export with reordered faces is not interchangeable.

The production reconstruction repeats object source frames as needed, selects `vertices_seq[1:1+sequence_frames]`, flips the source Y axis, and applies the per-frame placement scale, rotation and translation including the map offset. Frame zero of the rendered object is therefore not generally NPZ frame zero. Implementations are in the main VisPC script and `Syn4D_Track`; do not apply another frame shift on top of their existing shift.

`PerFrameMotion` can override position, rotation and scale at each frame. A constant transform from `be_seq_transform_channels.json` alone does not describe a simulated object. Avoid double-adding the map target location: the loader combines scene-local CSV positions with the recorded world offset exactly once.

The normalization consistency ratio is:

```text
Unreal_scale / NPZ_scale = NPZ_p90_extent_cm / Unreal_p90_extent_cm
```

Both sides must use the same target size and corresponding animation. A prior CSV generated from pre-correction NPZs is not a valid audit of regenerated geometry. Passing this scale test is not proof of per-frame pose/topology agreement or on-screen visibility.

### BEDLAM metadata

Body geometry:

```text
/scratch/shared/beegfs/zeren/Syn4D/metadata/bedlam2_smpl_npz/
    <subject>/<subject>_<animation_id>.npz
```

Clothing geometry:

```text
/scratch/shared/beegfs/zeren/Syn4D/metadata/b2_assetdata_download/clothing/npz/
    archive_map.json
    <archives named by archive_map.json>
```

The archive map maps `<subject>/<animation_id>/<animation_id>.npz` members to the containing archive. Clothing texture downloads are a separate rendering dependency; they do not replace clothing geometry NPZs. Body and clothing use the CSV `start_frame` and their source-specific coordinate conventions. BEDLAM identity is a subject-animation pair, not just an animation number or a clothing texture.

### Correct metadata precedence

For the viewer, use:

```text
--metadata-root /scratch/shared/beegfs/kelvin/Syn4D/metadata
--fallback-metadata-root /scratch/shared/beegfs/zeren/Syn4D/metadata
```

This selects corrected Kelvin object NPZs while resolving missing BEDLAM dependencies from the shared root. The production VisPC wrappers instead use the shared root first **and explicitly override `--obj-npz-root` to Kelvin's corrected object directory**. These two policies serve the same purpose; dropping the explicit object override while keeping the shared root first is not equivalent.

Even the object-only viewer currently opens the clothing archive map during initialization. If it raises `archive_map.json` missing, provide the shared metadata fallback; do not create a fake empty file or assume the object data is defective.

The September metadata staging inventory covers **2,167 object dependencies** from mixed and corrected no-sim: 1,267 in mixed and 900 in corrected no-sim. Its total recorded size is about 83.39 GB. It includes simulation objects, not just the three placement objects. These are historical staging counts, not a fresh audit of every production NPZ. NVS was generated later and is outside that staging script's scope; audit NVS references before assuming the older upload covers it.

Staging and provenance:

```text
/athenahomes/kelvin/projects/Syn4D/unreal_linux/analysis/v2_metadata_update_20260915/
    summary.json
    upload/manifest.json
    upload/new_weight_bone/...
```

The staging tree contains links to production metadata. The current upload script targets `Syn4D/Syn4D`, repository path `data/metadata/`, although the historical summary still contains an older MotionPlayground destination. Follow the actual uploader, not that stale summary field.

Do not overwrite V1/evaluation reconstruction metadata with corrected V2 NPZs merely because IDs match. The saved comparison against the shared root reports 279 geometry differences and seven incomplete comparisons among 286 entries. That report is not proof that every differing asset was used by V1. Preserve dataset-specific metadata versions or hashes and establish actual references before replacing anything.

## Tracking and attachment schemas

### Main tracking shard

`<split>/<scene>/tracking_safetensors/<seq>.safetensors` contains:

| Tensor | Dtype and shape | Meaning |
| --- | --- | --- |
| `offsets` | int64 `[R+1]` | Start/end positions of each frame-mask record in concatenated point arrays. |
| `record_hw` | int32 `[R,2]` | Original image height and width for each record. |
| `valid_flat_idx_values` | int32 `[P]` | Source image pixel index, row-major: `v*W+u`. |
| `face_ids_values` | int32 `[P]` | Triangle index in the corresponding body's/clothing's/object's `faces` array. |

The index format is `syn4d_compact_faceid_safetensors_v1`. It includes scene, sequence, shard name, `num_records`, `num_points`, and `record_key_to_id`. A record key is:

```text
seq_000000_0_0000/_00_body
seq_000000_0_0000/obj_01
```

**Resolve the record ID through the mapping. JSON key order is not record order.** For record `r`, use `[offsets[r]:offsets[r+1]]`. There is no universal cross-object meaning to face ID 100: it is local to the mask's mesh. A source record identifies pixels visible at that source frame; the same array offset in another record does not identify the same physical point.

The log contains counts and lists of skipped unreliable records and missing objects. Empty `failed_records` in the index does not imply no skipped masks; consult `<seq>_log.json` too.

### Attachment shard

`<split>_attachments/<scene>/tracking_attachments_safetensors/<seq>.safetensors` contains:

| Tensor | Dtype and shape | Meaning |
| --- | --- | --- |
| `barycentric_values` | float32 `[P,2]` | Weights `w1,w2` for ordered face vertices 1 and 2. |
| `signed_distance_values` | float32 `[P]` | Signed source-point offset from the selected face plane, in metres. |

The index format is `syn4d_tracking_attachments_safetensors_v1`. Attachments intentionally do not duplicate offsets, face IDs, pixel indices or record mapping. They use **the main tracking shard's record IDs, offsets and exact point order**.

Both indexes should agree on scene, sequence, record count and point count; tensor lengths and offsets must agree. Source size and mtime are recorded for local resume checks. A copied archive may change timestamps, so mtime alone is not a portable identity proof. Preserve publication pairing and, for strong cross-copy validation, content hashes. Equal counts alone cannot prove two independently regenerated files are identical.

Barycentric weights are intentionally **unclipped**. Negative values or values above one can legitimately describe the point's projection onto the face plane outside its triangle. Do not clamp or renormalize them silently.

Degenerate triangles can produce NaN/Inf values. These are retained to preserve alignment. Apply a finite mask to the selected record, together with valid face/pixel indices and nondegenerate target triangles. Do not delete elements globally and then reuse the old offsets. As a concrete example, the sampled corrected no-sim Hangar sequence has 195,167 non-finite attachment points among 9,918,239 stored points; these cannot be treated as valid tracks.

### Minimal aligned record read

This reads one existing record without loading an entire sequence's point arrays:

```python
import json
from pathlib import Path
import numpy as np
from safetensors import safe_open

root = Path('/scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2')
scene, seq = 'hangar', 'seq_000000_0'
tracking = root / 'mixed' / scene / 'tracking_safetensors'
attachments = root / 'mixed_attachments' / scene / 'tracking_attachments_safetensors'
index = json.loads((tracking / f'{seq}_index.json').read_text())
ai = json.loads((attachments / f'{seq}_index.json').read_text())
assert all(index[k] == ai[k] for k in ('scene', 'seq', 'num_records', 'num_points'))
key = f'{seq}_0000/_00_body'   # inspect mapping for other available frame/masks
r = index['record_key_to_id'][key]

with safe_open(str(tracking / f'{seq}.safetensors'), framework='np') as f:
    offsets = f.get_tensor('offsets')
    lo, hi = map(int, offsets[r:r+2])
    h, w = map(int, f.get_tensor('record_hw')[r])
    pixel = f.get_slice('valid_flat_idx_values')[lo:hi]
    face = f.get_slice('face_ids_values')[lo:hi]
with safe_open(str(attachments / f'{seq}.safetensors'), framework='np') as f:
    bary2 = f.get_slice('barycentric_values')[lo:hi]
    distance = f.get_slice('signed_distance_values')[lo:hi]
u, v = pixel % w, pixel // w
finite = np.isfinite(bary2).all(axis=1) & np.isfinite(distance)
```

Cache handles and indexes per sequence instead of reopening them per pixel/frame. A sampled mixed Hangar shard is about 400 MB and contains nearly 50 million point observations, so loading all shards at once is inappropriate.

## Reconstructing and using tracks

Given a selected face with ordered target-frame world-space vertices `a,b,c`:

```text
w0 = 1 - w1 - w2
n = normalize(cross(b-a, c-a))
Xtarget = w0*a + w1*b + w2*c + signed_distance*n
```

Use the same face ID, topology and winding at source and target. `a,b,c` must already include the correct source animation frame, axis conversion, placement scale and global motion in metres. The offset preserves the source depth point's displacement from the mesh plane; ignoring it changes the reconstruction. The stored offset is not automatically rescaled by a later target transform.

Without attachments, the existing reader recovers barycentric coordinates and the signed offset from source depth, source camera calibration and the selected source triangle. This avoids repeating nearest-face search but still requires source geometry. The current public/local Viser readers inspected here use this face-ID reconstruction path; simply placing attachment files next to them does **not** automatically enable attachment loading. For attachment integration, use the documented contract in:

```text
/athenahomes/kelvin/projects/Syn4D/Syn4d_renderer/tools/tracking_attachments/ATTACHMENT_DATALOADER_USAGE.txt
```

Its format explanation applies to V2, but its example dataset paths and aggregate statistics describe an older V1 backfill. Do not copy those statistics into a V2 report.

### From world tracks to pixels

For target camera pose `C2W`, use `W2C = inverse(C2W)`, transform `Xtarget` to camera coordinates and project with the target intrinsics. Require positive camera Z and image bounds. To claim the point is visible, also compare against target depth and appropriate masks. **A geometrically propagated track is not automatically a visible correspondence.** Occluded or off-screen points may still have valid world trajectories.

Static background points are lifted from source depth and remain fixed in world coordinates, using the environment mask. Wind-animated foliage and other moving environment effects violate this static-background approximation; they are not given full animated mesh tracks by these object metadata files.

For training, group by `(split, scene, setup)` when creating train/validation partitions if alternate-camera leakage matters. Splitting the eight views of one setup across train/test gives nearly the same objects and motion to both. NVS also allows asset reuse across setups, so unique sequence names do not imply disjoint objects. Treat RGB appearance, geometry correctness, visibility and tracking validity as separate signals.

### Reader outputs and timing caveats

After `Syn4D_Track` passes through its base dataset, each view exposes:

| Key | Meaning |
| --- | --- |
| `img` | RGB tensor after the selected normalization/crop/resize transform. The supplied `ImgNorm` uses normalized rather than raw uint8 values. |
| `depthmap` | Processed camera-Z depth map in metres. |
| `camera_intrinsics` | Intrinsics adjusted for the view's crop/resize. |
| `camera_pose` | Camera-to-world 4×4 transform. |
| `pts3d`, `valid_mask` | Current-frame world-space depth point map and validity. |
| `track`, `track_valid_mask` | Target-time world positions of query-frame pixels, and their tracking validity. The pixel grid is tied to the query frame, not necessarily the currently displayed RGB pixel identities. |
| `track_query_idx` | Query/reference frame in the sampled view list. |
| `c2w_aligned`, `w2c_aligned` | Camera transforms relative to the first loaded camera. |
| `pts3d_global_aligned`, `track_global_aligned` | Geometry expressed in that anchor-camera coordinate system. |

Inside `_get_views`, `track` temporarily uses target-camera coordinates; the base dataset converts it to world space. Do not bypass the base class and assume the intermediate array already has the public output convention. Invalid arrays may contain placeholder coordinates: always use their masks rather than testing for XYZ equal to zero.

The inspected viewer reader still sets its returned `fps` field to `24 // stride`. That is a **legacy reader value**, not authoritative timing for these 30-FPS renders. For physical velocity, temporal losses or export, use recorded 30-FPS sequence timing and actual frame index differences; for stride `s`, ordinary consecutive sampled frames are `s/30` seconds apart. This documentation does not silently modify the reader.

The base dataset can fall back to another index when a sample has no usable geometry/tracks. For controlled debugging, verify returned labels and frame paths, not just the requested index. Otherwise a seemingly successful visualization can be showing the next valid sample rather than the failure case.

## Visualization commands

These commands are examples to run on a suitable allocated node. They were not used to start new GPU jobs during this documentation audit. `vdpm` imports for Torch, OpenEXR, safetensors, OpenCV, Viser and the viewer dependencies passed; the sample EXR and tracking/attachment record read also passed.

For the Python preview commands, these optional shell settings keep Matplotlib out of the home quota and make the existing FFmpeg installation available for browser-friendly H.264 copies:

```bash
export MPLCONFIGDIR=/tmp/matplotlib-syn4d-v2
export PATH=/users/kelvin/miniconda3/envs/bedlam2-repaired/bin:"$PATH"
```

The commands below still select the `vdpm` Python explicitly; adding FFmpeg to `PATH` does not change that interpreter.

### Watch an RGB video directly

Example file:

```text
/scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2/mixed/hangar/mp4/seq_000000_0.mp4
```

Download from the local machine:

```bash
scp -J kelvin@login.robots.ox.ac.uk \
  kelvin@athena.robots.ox.ac.uk:/scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2/mixed/hangar/mp4/seq_000000_0.mp4 .
```

For a physical directory, use lowercase `-r`, not uppercase `-R`. For NVS linked trees, stage a dereferenced copy on the cluster before downloading a portable bundle; see the packing section.

### Interactive point cloud and tracking viewer

On the allocated node:

```bash
cd /athenahomes/kelvin/projects/Syn4D
/users/kelvin/miniconda3/envs/vdpm/bin/python \
  Syn4D/code/visualizer/run.py \
  --dataset-root /scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2/mixed_no_sim_corrected \
  --metadata-root /scratch/shared/beegfs/kelvin/Syn4D/metadata \
  --fallback-metadata-root /scratch/shared/beegfs/zeren/Syn4D/metadata \
  --scene-name hangar --select-idx-view0 0 \
  --tracking-format safetensor --rgb-source mp4 \
  --stride 1 --num-frames 16 --track-query-idx 0 \
  --resolution 640x360 --host 127.0.0.1 --port 8020
```

Use `mixed` or `nvs_outpaint` as the dataset root to inspect those collections. Pass the split root, **not** the V2 parent containing all splits or the scene directory itself. Explicit `--scene-name` avoids scanning queue/test directories as scenes. `--rgb-source mp4` avoids many small RGB reads; `auto` prefers PNG if that directory exists. If a partially pruned PNG tree exists, explicitly choosing MP4 is safer than assuming auto detects all missing frames.

From the local machine, replacing `COMPUTE_NODE` with the node running the viewer:

```bash
ssh -N -J kelvin@login.robots.ox.ac.uk \
  -L 8020:127.0.0.1:8020 kelvin@COMPUTE_NODE
```

Then open `http://127.0.0.1:8020`. The tunnel must reach the actual viewer node, not an unrelated login node. Use a different port consistently if 8020 is occupied.

`--select-idx-view0` and optional `--select-idx-view1` are **dataset indexes**, not literal suffixes from filenames. Verify the loaded sequence, especially when selecting a non-first clip. For exact named-sequence output, the offline trajectory script below has `--seq-name`.

The viewer reconstructs geometry before the cloud appears; seeing the UI first is normal. Start with 16 frames and moderate display resolution. Lower display resolution does not necessarily eliminate native-resolution source geometry work. CPU reconstruction is supported, but full sequences can require substantial RAM/time: use an allocated compute node, not a shared login node for sustained work. VisPC generation itself requires CUDA. The Viser display aligns to an anchor camera and normalizes the point cloud for viewing; do not measure metric distances directly from normalized display coordinates.

### Render a trajectory overlay for an exact sequence

```bash
cd /athenahomes/kelvin/projects/Syn4D
/users/kelvin/miniconda3/envs/vdpm/bin/python \
  Syn4D_plots/render_tracking_trajectories.py \
  --dataset-root /scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2/mixed_no_sim_corrected \
  --metadata-root /scratch/shared/beegfs/kelvin/Syn4D/metadata \
  --fallback-metadata-root /scratch/shared/beegfs/zeren/Syn4D/metadata \
  --scene-name hangar --seq-name seq_000000_0 \
  --stride 1 --num-frames 24 --resolution 640x360 \
  --tracking-format safetensor --rgb-source mp4 \
  --projection-camera actual --background actual-rgb \
  --output /tmp/hangar_tracking_preview.mp4
```

`--projection-camera actual` overlays tracks in each actual camera frame. `query` projects trajectories into the fixed query camera and is a different visualization. `--fps` controls playback of the preview, not source animation geometry. Output depends on valid query-frame points and is not a replacement for all-frame tracking evaluation.

### Visualize one RGB-D frame from a virtual camera

This requires no animated mesh NPZs and is useful for checking camera/depth convention:

```bash
cd /athenahomes/kelvin/projects/Syn4D
/users/kelvin/miniconda3/envs/vdpm/bin/python \
  Syn4D_plots/render_static_pointcloud_camera_path.py \
  --dataset-root /scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2/mixed \
  --scene-name hangar --seq-name seq_000000_0 --frame-idx 0 \
  --num-frames 60 --point-stride 4 \
  --output /tmp/hangar_rgbd_pointcloud.mp4
```

This animates a **virtual camera around one static reconstructed point cloud**. It does not reconstruct the scene's real animation or fill newly revealed surfaces. Holes behind foreground surfaces are expected. A first-frame PNG is written beside the video for alignment inspection.

### Additional diagnostic entry points

| Tool | Purpose |
| --- | --- |
| `Syn4D_plots/render_combined_sequence_batch.py` | Batch report videos combining scene geometry/tracking; defaults are for a V1 experiment, so explicitly set V2 roots and clear/replace the default `bald` scene filter. |
| `Syn4d_renderer/rasterize_object_visibility_debug_gpu.py` | GPU comparison of reconstructed NPZ geometry with rendered depth/masks for a named sequence/frame. Supports `--save-depth-comparison`, `--run-unreliability-test`, `--save-distance-outliers`. |
| `Syn4d_renderer/tools/checks/check_vispc_depth_rgb_consistency.py` | Diagnostic consistency checks; inspect its CLI and metadata selection before use. |
| `Syn4d_renderer/tools/checks/plot_npz_vs_exr_depth.py` | NPZ/rendered-depth diagnostic plots. |
| `unreal_linux/python/diagnostic/compare_depth_camera_projection.py` | Controlled camera-pose/intrinsics projection ablations. |
| `Syn4d_renderer/tools/tracking_attachments/benchmark_target_wrapping.py` | Attachment-based target reconstruction benchmark. |

These paths are relative to `/athenahomes/kelvin/projects/Syn4D`. Several diagnostic scripts remain untracked local tools, not a portable installed package. Use `--help` and an isolated output path; do not overwrite production tracking just to make a preview.

## Quality limitations and validation

### What the unreliable flag means

The sparse VisPC producer computes closest-surface distances for depth points in a mask. It skips a **non-body** frame-mask record when distance standard deviation exceeds 0.01 m. `_00_body` is explicitly exempt; clothing is not. The log's unreliable ratio is a frame-mask-record statistic, not automatically a percentage of pixels, videos or objects.

A low standard deviation is not a bound on absolute error: points can be consistently displaced yet have little distance variation. Therefore an unflagged body record or a low global unreliable ratio does not certify geometric alignment. Distinguish this production record filter from the stricter object-screening statistics mode, which can require success in every sampled frame or multiple independent sequences.

The face-ID-only viewer has further finite/degenerate/plane-distance validity checks. Its compact reconstruction uses a 0.1 m plane-distance gate; this is not the producer's 0.01 m record-level standard-deviation threshold. Avoid presenting the two as the same acceptance criterion.

### Known issues to keep visible

| Issue | Interpretation and handling |
| --- | --- |
| BEDLAM endpoint mismatch | The earlier external audit reported 88 large body-observation mismatches at output frame 191, 87 at source-animation endpoints, plus a separate sparse-tracking case. These totals were not independently rerun in this inventory. The local endpoint probe identifies the source-window boundary and models geometry-cache wrapping as a hypothesis, not an imported-cache duration measurement. Treat affected endpoints as suspect; a training mask that excludes the final frame mitigates this specific endpoint case, not every other error. |
| Body reliability exemption | The producer can retain a bad BEDLAM body record despite no unreliable flag. Validate endpoint source geometry against depth rather than relying on skipped-record counts. |
| Old mixed scale inconsistencies | Restoring or rerendering original mixed scenes does not automatically apply corrected NPZ/Unreal ratio filtering. Do not describe original mixed as uniformly passing the later corrected no-sim whitelist. |
| Foliage mask/depth ownership | Wasteland and Oakforest NVS contain investigated foreground foliage issues. Separate disabled-foliage and hit-proxy experiments exist; their existence is not evidence production was fixed. |
| Statistics-mode empty masks | In the saved foliage comparisons, run summaries reject all ten objects under the strict all-frame rule; object summaries show empty-mask frames contribute to rejection. A rotating camera cannot keep every object visible throughout. Separate observed-frame geometric failures from absent visibility before judging the fix. |
| Non-finite attachments | Filter invalid source barycentrics/distances and degenerate target triangles. Never convert NaNs to zero and label them valid. |
| RGB/depth camera ordering | Runtime fixes order camera look-at after its animated target. This addressed earlier misalignment; verify actual paired camera CSVs when inspecting a suspicious rerender rather than assuming any job using AA16 is correct. |
| Smalltown ground appearance | A scene-ground/material problem was reported earlier. No new image review of that issue is part of this inventory; do not infer visual approval from complete file counts. |
| Shared-filesystem errors | `Remote I/O error` or `Communication error on send` indicates failed reads, not proof of bad geometry. Do not silently mark those assets invalid or accept partially written outputs. |

Foliage experiment results are under:

```text
.../Syn4D_V2/nvs_outpaint/_foliage_vispc_test/
    enabled/{oakforest,wasteland}/vispc_statistics/
    disabled/{oakforest,wasteland}/vispc_statistics/
```

Read `object_summary.csv`, per-sequence records and `run_summary.json` together. Keep those experimental results separate from the main production `tracking_safetensors`.

### Before training or publishing

1. Confirm sequence names and actual frame counts across MP4, camera CSV and depth. Decode videos where integrity matters; file counts alone are insufficient.
2. Check RGB/depth pose and intrinsics alignment, including first/last frames and high-shake clips.
3. Pin the exact object/body/clothing geometry version and preserve face ordering. Check source-frame offsets, global transforms and units.
4. Validate tracking/attachment record alignment, tensor lengths, face/pixel bounds and non-finite masks.
5. Inspect unreliable/missing-object logs and independent absolute-distance diagnostics; include BEDLAM bodies even though the producer exempts them.
6. Define visibility handling separately from point propagation and source validity.
7. Define endpoint exclusions and scene-specific quality exclusions explicitly in the training manifest, not by silently editing source videos.
8. For NVS copies, resolve symlinks and confirm batch sources are included or materialized.
9. Verify archive integrity and required metadata before deleting any local source. This guide authorizes no cleanup.

## Packing downloading and publication

### Current archive mapping

The configured dataset repository is `KelvinzLi/MotionPlayground`. The local uploader maps:

| Local archive directory under V2 | Repository path |
| --- | --- |
| `mixed_archives` | `V2/mixed/<scene>.tar.zst` |
| `mixed_attachments_archives` | `V2/mixed_attachments/<scene>.tar.zst` |
| `mixed_no_sim_corrected_archives` | `V2/mixed_no_sim/<scene>.tar.zst` |
| `mixed_no_sim_corrected_attachments_archives` | `V2/mixed_no_sim_attachments/<scene>.tar.zst` |

This is the script's configured mapping; live remote inventory and checksums were not queried during this local audit. The uploader has no NVS group, so it must not be assumed to publish `nvs_outpaint`.

The uploader is:

```text
/athenahomes/kelvin/projects/Syn4D/unreal_linux/runs/upload_v2_motionplayground.sh
```

Its `all --check` mode checks expected local scene archives without uploading:

```bash
cd /athenahomes/kelvin/projects/Syn4D/unreal_linux
bash runs/upload_v2_motionplayground.sh all --check
```

Object metadata upload is separate:

```text
/athenahomes/kelvin/projects/Syn4D/unreal_linux/runs/upload_v2_metadata.sh
```

It targets `Syn4D/Syn4D` → `data/metadata/`, checks staged file stats, and checks shared GSO content conflicts before upload. It does not upload Unreal assets or BEDLAM clothing/body geometry. Metadata redistribution must respect the source asset/data licences; having local cluster access is not itself redistribution permission.

### Archive contents and safe extraction

Data archives are rooted at `<scene>/...`; attachment archives are rooted at `<scene>/tracking_attachments_safetensors/...`. Extract them into separate split roots if preserving the cluster structure, or alongside one another only when the consuming loader expects that layout. Do not put an attachment archive inside an extra duplicate `<scene>/<scene>` level.

```bash
mkdir -p ./V2/mixed ./V2/mixed_attachments
zstd -t ./hangar.tar.zst
tar --zstd --no-same-owner --no-same-permissions -xf ./hangar.tar.zst -C ./V2/mixed
# Extract the separately downloaded attachment archive into ./V2/mixed_attachments.
```

Use a new extraction directory rather than merging blindly with an older release. Archives preserve Unix modes; directories need execute/traverse permission. The first members inspected in the existing Hangar data archive had directory mode 0775 and file mode 0664, but that small check does not certify every member of all archives. Diagnose permission problems with `namei -l` and ownership checks; do not recursively change permissions on unrelated datasets.

The actual per-scene packer excludes raw `exr_image`, `exr_depth`, redundant `exr_layers/image`, `unreal_assets`, `unreal_logs`, and several transient bookkeeping folders. It does **not** by itself delete originals or universally remove PNGs/masks/camera JSONs. The sampled existing archive includes per-frame camera JSON. A newer generic `finalize_syn4d_split.sh` can pack environment masks and detach optional high-count files, but its availability does not mean that workflow was applied to these September archives.

### NVS needs portable materialization

For example, stage one scene's viewable/training artifacts into a new location, dereferencing links, before archiving or transferring it:

```bash
NVS_SOURCE=/scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2/nvs_outpaint/hangar
NVS_COPY=/scratch/shared/beegfs/kelvin/Syn4D/download_staging/nvs_hangar_portable/hangar
mkdir -p "$NVS_COPY"
rsync -aL --relative "$NVS_SOURCE/./mp4" "$NVS_SOURCE/./png" \
  "$NVS_SOURCE/./exr_layers/depth" "$NVS_SOURCE/./exr_layers/masks" \
  "$NVS_SOURCE/./ground_truth" "$NVS_SOURCE/./tracking_safetensors" \
  "$NVS_SOURCE/./be_seq.csv" "$NVS_SOURCE/./be_seq_transform_channels.json" \
  "$NVS_SOURCE/./be_camera_animations.json" "$NVS_COPY/"
```

This copies data and can require substantial space. For RGB-only review, copy only `mp4`. Attachments remain a separate sibling collection and must be copied separately if needed. Verify the staged copy before publishing. Do not archive only the scene symlinks and expect an external recipient to have the cluster batch paths.

## Pipeline and maintenance scripts

All paths here are rooted at `/athenahomes/kelvin/projects/Syn4D`.

| Stage | Primary code and role |
| --- | --- |
| Scene/project/map configuration | `unreal_linux/config/syn4d_v2_placement_scenes.tsv`; `unreal_linux/SYN4D_V2_SCENE_MAPS.md`. |
| Placement | `Syn4d_renderer/tools/sample_object_footprint_placements_perframe_motion.py`; creates collision-checked placements, global motion and optional circular exclusions. |
| Physics simulation | `Syn4d_renderer/unreal/render/Core/Python/tools/sim_throw_csv_objects.py` and `_batch.py`; records transforms of simulated objects into scene inputs. |
| Mixed camera sampling | `Syn4d_renderer/unreal/render/Core/Python/tools/camera_sampling/generate_validated_mixed_camera_layouts.py`; shared samplers and scheduler in the same folder. |
| Level Sequence creation | `Syn4d_renderer/unreal/render/Core/Python/create_level_sequences_csv_nohair.py`; includes decal suppression and Empty look-at targets. |
| Preparation workflow | `unreal_linux/scripts/run_ue53_camera_placement_to_mrq_workflow.sh`; placement CSV/camera sampling through Level Sequence and MRQ preparation. |
| Runtime rendering | `unreal_linux/scripts/run_ue53_bedlam_render.sh`; `unreal_linux/python/render_bedlam_mrq.py`; readiness, job filters, completion reporting and camera tick ordering. |
| Mixed queue | `unreal_linux/runs/syn4d_v2_mixed/render_worker.sh`, `render_scene.sh`; dynamic scene/project ownership and resume. |
| Corrected no-sim queue | `unreal_linux/python/mixed_no_sim.py`, `mixed_no_sim_worker.py`; `runs/syn4d_v2_mixed_no_sim/corrected_worker.sh`. |
| NVS placement and batches | `unreal_linux/python/empty_focus_placement_batch.py`, `empty_focus_worker.py`, `empty_focus_batch_worker.py`; `runs/empty_focus_production/production.sbatch`. |
| NVS scene assembly | `unreal_linux/python/assemble_empty_focus_scenes.py`; merges metadata and links outputs without duplicating render payloads. |
| Postprocessing | `Syn4d_renderer/tools/post_render_pipeline/be_post_render_pipeline_watch.sh`; extracts layers/masks, camera metadata and MP4, with readiness/done checks. |
| VisPC generation | `Syn4d_renderer/vis_pc_multiview_seg_obj_process_barycentric_final_clean_vgg_single.py`; nearest-face associations, statistics-only mode or tracking plus attachments. |
| Tracking writer | `Syn4d_renderer/tracking_safetensor_writer.py`; publishes sequence shards, indexes and diagnostic logs. |
| Mixed/no-sim VisPC workers | `unreal_linux/runs/syn4d_v2_mixed/vispc_scene.sh`, `vispc_worker.sh`; `unreal_linux/python/no_sim_vispc_worker.py`. |
| NVS VisPC worker | `unreal_linux/python/empty_focus_vispc_worker.py`; scene claims and 50-sequence preflight. |
| Attachment backfill | `Syn4d_renderer/tools/tracking_attachments/generate_from_faceid.py`; reconstructs attachments for existing face IDs without recomputing closest-face search. |
| Packing | `unreal_linux/python/pack_no_sim_worker.py`, `pack_original_mixed_worker.py`; renderer `tools/dataset_packaging/pack_scene_archives.sh` and `tools/tracking_attachments/pack_scene_archives.sh`. |
| Shared lock primitive | `unreal_linux/python/directory_claim.py`; atomic directory claims with conservative owner recovery. |
| Inventory used for this guide | `unreal_linux/docs/inventory_v2.py`; no dataset mutations, no tensor payload scan. |

Render/preparation locks protect shared Unreal projects and generated-asset paths. VisPC workers claim scenes separately. More GPU workers help only if independent claimable work exists and BeeGFS throughput permits it. Do not run two uncoordinated writers against the same scene/shard or remove a lock based only on its age.

The September launch recipes contain dated allocation manifests, cluster paths and external assets. Many remain untracked and were explicitly held out of the first commit batch; they are not yet a self-contained fresh-clone release. Avoid invoking allocation, restore, cleanup or rerender commands merely to read existing data.

DDC is a regenerable Unreal shader/asset cache, not training metadata. The render wrapper explicitly overrides the local cache path to avoid accidental home-quota use and accepts a shared-cache configuration. Cache deletion cannot substitute for preserving `be_seq.csv`, camera transforms, depth or animated mesh metadata.

## Commit state and evidence

Nine scoped local commits were made on 25 November 2026; nothing was pushed:

| Repository | Commit | Content |
| --- | --- | --- |
| `Syn4d_renderer` | `bf0366b` | NPZ mesh selection and resumable Linux conversion. |
| `Syn4d_renderer` | `bb9dc3f` | Unreal animation bounds sampling and whitelist parsing. |
| `Syn4d_renderer` | `e496d35` | Cached grounded repeatable object-filter batches. |
| `Syn4d_renderer` | `3c5ece8` | Integrated tracking attachments and safe resume checks. |
| `Syn4d_renderer` | `da2e053` | Animated Empty camera targets. |
| `Syn4d_renderer` | `bb2dbe0` | Circular placement and clearance exclusions. |
| `unreal_linux` | `c9ec141` | Cross-node directory claims. |
| `unreal_linux` | `e8f094e` | Look-at target repair and camera regression tests. |
| `unreal_linux` | `00fbace` | Plugin provenance and shared DDC documentation. |

The renderer remains on `features/additional_global_motion_linux_render`; Linux orchestration remains on `main`. Existing remote divergence was not reconciled or force-pushed. Held files and unrelated untracked files remain untouched. The source review included 70 passing CPU tests plus a cancellation check, not a fresh full Unreal/Blender integration run.

The currently installed engine-side `create_level_sequences_csv.py` matched the older renderer revision `ad4383e` during the source audit. Empty-target wrappers explicitly select the repository nohair script. A generic launcher that defaults to the engine copy does not automatically acquire newly committed source changes; deployment must be deliberate and verified.

Evidence and detailed inventory:

```text
/athenahomes/kelvin/projects/Syn4D/unreal_linux/docs/v2_inventory_20261125.json
/athenahomes/kelvin/projects/Syn4D/commit_preparation_20261125/plan.json
/athenahomes/kelvin/projects/Syn4D/commit_preparation_20261125/validation.json
```

The JSON inventory contains every main scene's sequence-level artifact counts, per-sequence RGB-camera row counts, metadata samples, safetensor headers and example resolved link destinations. It does not hash all datasets, decode every MP4, verify all depth/mask frames, or establish a current remote upload state.

To regenerate a local inventory without changing dataset content:

```bash
cd /athenahomes/kelvin/projects/Syn4D
timeout 300 python -B unreal_linux/docs/inventory_v2.py \
  --root /scratch/shared/beegfs/kelvin/Syn4D/subsets/Syn4D_V2 \
  --output /tmp/syn4d_v2_inventory.json
```

Stop and investigate filesystem errors rather than turning missing reads into zero-count scenes. Retain the inventory date alongside any shared summary because active processing or later materialization can change the physical layout.
