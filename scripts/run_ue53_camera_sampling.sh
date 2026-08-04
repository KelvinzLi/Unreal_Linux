#!/usr/bin/env bash

set -euo pipefail

UE_ROOT="${UE_ROOT:-/scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2}"
PROJECT="${PROJECT:-/work/kelvin/unreal_linux/simulation_tests/projects/VictorianStreet/VictorianStreet.uproject}"
MAP_FILE="${MAP_FILE:-/work/kelvin/unreal_linux/simulation_tests/projects/VictorianStreet/Content/VictorianStreet/Maps/Showcase.umap}"
WRAPPER="${WRAPPER:-/athenahomes/kelvin/projects/Syn4D/unreal_linux/python/run_camera_sampling.py}"

export BEDLAM_CAMERA_SAMPLING_SCRIPT="${BEDLAM_CAMERA_SAMPLING_SCRIPT:-/athenahomes/kelvin/projects/Syn4D/Syn4d_renderer/unreal/render/Core/Python/tools/camera_sampling/generate_validated_orbit_camera_animations.py}"
export BEDLAM_CAMERA_SAMPLING_CSV_PATH="${BEDLAM_CAMERA_SAMPLING_CSV_PATH:-/work/kelvin/unreal_linux/simulation_tests/outputs/street/be_seq_sim.csv}"
export BEDLAM_CAMERA_SAMPLING_OUTPUT_CSV="${BEDLAM_CAMERA_SAMPLING_OUTPUT_CSV:-/work/kelvin/unreal_linux/simulation_tests/outputs/street/be_seq_sim_multicam.csv}"
export BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON="${BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON:-/work/kelvin/unreal_linux/simulation_tests/outputs/street/be_camera_animations.json}"
export BEDLAM_CAMERA_SAMPLING_SEQUENCE_ROOT="${BEDLAM_CAMERA_SAMPLING_SEQUENCE_ROOT:-/Game/Bedlam/LevelSequences}"
export BEDLAM_CAMERA_SAMPLING_SEED="${BEDLAM_CAMERA_SAMPLING_SEED:-}"
export BEDLAM_CAMERA_SAMPLING_START_DELAY="${BEDLAM_CAMERA_SAMPLING_START_DELAY:-120}"

RUN_TAG="${SLURM_JOB_ID:-manual}_$(date +%Y%m%d_%H%M%S)"
ZEN_DIR="/tmp/${USER}/unreal_zen_5.3.2_camera_${RUN_TAG}"
DDC_DIR="/tmp/${USER}/unreal_ddc_5.3.2"
mkdir -p "$ZEN_DIR" "$DDC_DIR" "$(dirname "$BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON")"

test -x "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
test -f "$PROJECT"
test -f "$MAP_FILE"
test -f "$WRAPPER"
test -f "$BEDLAM_CAMERA_SAMPLING_SCRIPT"
test -f "$BEDLAM_CAMERA_SAMPLING_CSV_PATH"

"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" \
    "$PROJECT" \
    "$MAP_FILE" \
    "-ExecCmds=tick.AllowAsyncTickDispatch 0,tick.AllowConcurrentTickQueue 0,py $WRAPPER" \
    -RenderOffscreen \
    -vulkan \
    -unattended \
    -NoSplash \
    -NoTextureStreaming \
    -ResX=640 \
    -ResY=360 \
    "-ZenDataPath=$ZEN_DIR" \
    "-LocalDataCachePath=$DDC_DIR" \
    -stdout \
    -FullStdOutLogOutput
