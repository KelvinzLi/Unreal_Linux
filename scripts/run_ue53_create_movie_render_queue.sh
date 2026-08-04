#!/usr/bin/env bash

set -euo pipefail

UE_ROOT="${UE_ROOT:-/scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2}"
PROJECT="${PROJECT:-/work/kelvin/unreal_linux/simulation_tests/projects/VictorianStreet/VictorianStreet.uproject}"
MAP="${MAP:-/Game/VictorianStreet/Maps/Showcase}"
MAP_FILE="${MAP_FILE:-/work/kelvin/unreal_linux/simulation_tests/projects/VictorianStreet/Content/VictorianStreet/Maps/Showcase.umap}"
WRAPPER="${WRAPPER:-/athenahomes/kelvin/projects/Syn4D/unreal_linux/python/run_create_movie_render_queue.py}"

export BEDLAM_MRQ_GENERATOR_SCRIPT="${BEDLAM_MRQ_GENERATOR_SCRIPT:-$UE_ROOT/Engine/Content/PS/Bedlam/Core/Python/create_movie_render_queue.py}"
export BEDLAM_MRQ_SEQUENCE_ROOT="${BEDLAM_MRQ_SEQUENCE_ROOT:-/Game/Bedlam/LevelSequences}"
export BEDLAM_MRQ_OUTPUT_DIR="${BEDLAM_MRQ_OUTPUT_DIR:-/work/kelvin/unreal_linux/simulation_tests/renders/street}"
export BEDLAM_MRQ_PRESET="${BEDLAM_MRQ_PRESET:-1-1-1_EXR_PNG_DepthMask}"
export BEDLAM_MRQ_RESOLUTION="${BEDLAM_MRQ_RESOLUTION:-1280x720}"
export BEDLAM_MRQ_BATCHES="${BEDLAM_MRQ_BATCHES:-1}"
export BEDLAM_MRQ_EXPECTED_MAP="${BEDLAM_MRQ_EXPECTED_MAP:-$MAP}"
export BEDLAM_MRQ_START_DELAY="${BEDLAM_MRQ_START_DELAY:-5}"
export BEDLAM_MRQ_START_TIMEOUT="${BEDLAM_MRQ_START_TIMEOUT:-180}"

RUN_TAG="${SLURM_JOB_ID:-manual}_$(date +%Y%m%d_%H%M%S)"
ZEN_DIR="/tmp/${USER}/unreal_zen_5.3.2_mrq_${RUN_TAG}"
DDC_DIR="/tmp/${USER}/unreal_ddc_5.3.2"
mkdir -p "$ZEN_DIR" "$DDC_DIR" "$BEDLAM_MRQ_OUTPUT_DIR"

test -x "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
test -f "$PROJECT"
test -f "$MAP_FILE"
test -f "$WRAPPER"
test -f "$BEDLAM_MRQ_GENERATOR_SCRIPT"

echo "Project:      $PROJECT"
echo "Map:          $BEDLAM_MRQ_EXPECTED_MAP"
echo "Sequences:    $BEDLAM_MRQ_SEQUENCE_ROOT"
echo "Output:       $BEDLAM_MRQ_OUTPUT_DIR"
echo "Preset:       $BEDLAM_MRQ_PRESET"
echo "Resolution:   $BEDLAM_MRQ_RESOLUTION"

"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" \
    "$PROJECT" \
    "$MAP_FILE" \
    "-ExecCmds=py $WRAPPER" \
    -RenderOffscreen \
    -vulkan \
    -unattended \
    -NoSplash \
    -NoTextureStreaming \
    "-ZenDataPath=$ZEN_DIR" \
    "-LocalDataCachePath=$DDC_DIR" \
    -stdout \
    -FullStdOutLogOutput
