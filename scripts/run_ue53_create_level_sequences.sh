#!/usr/bin/env bash

set -euo pipefail

UE_ROOT="${UE_ROOT:-/scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2}"
PROJECT="${PROJECT:-/work/kelvin/unreal_linux/simulation_tests/projects/VictorianStreet/VictorianStreet.uproject}"
MAP="${MAP:-/Game/VictorianStreet/Maps/Showcase}"
MAP_FILE="${MAP_FILE:-/work/kelvin/unreal_linux/simulation_tests/projects/VictorianStreet/Content/VictorianStreet/Maps/Showcase.umap}"
WRAPPER_SCRIPT="${WRAPPER_SCRIPT:-/athenahomes/kelvin/projects/Syn4D/unreal_linux/python/run_create_level_sequences_csv.py}"

export BEDLAM_LEVEL_SEQUENCE_SCRIPT="${BEDLAM_LEVEL_SEQUENCE_SCRIPT:-$UE_ROOT/Engine/Content/PS/Bedlam/Core/Python/create_level_sequences_csv.py}"
export BEDLAM_LEVEL_SEQUENCE_CSV_PATH="${BEDLAM_LEVEL_SEQUENCE_CSV_PATH:-/work/kelvin/unreal_linux/simulation_tests/outputs/street/be_seq_sim.csv}"
export BEDLAM_LEVEL_SEQUENCE_STATUS_DIR="${BEDLAM_LEVEL_SEQUENCE_STATUS_DIR:-$(dirname "$BEDLAM_LEVEL_SEQUENCE_CSV_PATH")}"
export BEDLAM_LEVEL_SEQUENCE_CAMERA_TYPE="${BEDLAM_LEVEL_SEQUENCE_CAMERA_TYPE:-Default}"
export BEDLAM_LEVEL_SEQUENCE_ROOT="${BEDLAM_LEVEL_SEQUENCE_ROOT:-/Game/Bedlam/LevelSequences}"
export BEDLAM_LEVEL_SEQUENCE_START_DELAY="${BEDLAM_LEVEL_SEQUENCE_START_DELAY:-15}"
export BEDLAM_LEVEL_SEQUENCE_START_TIMEOUT="${BEDLAM_LEVEL_SEQUENCE_START_TIMEOUT:-120}"

RUN_TAG="${SLURM_JOB_ID:-manual}_$(date +%Y%m%d_%H%M%S)"
ZEN_DIR="/tmp/${USER}/unreal_zen_5.3.2_sequences_${RUN_TAG}"
DDC_DIR="/tmp/${USER}/unreal_ddc_5.3.2"
mkdir -p "$ZEN_DIR" "$DDC_DIR" "$BEDLAM_LEVEL_SEQUENCE_STATUS_DIR"

test -x "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
test -f "$PROJECT"
test -f "$MAP_FILE"
test -f "$WRAPPER_SCRIPT"
test -f "$BEDLAM_LEVEL_SEQUENCE_SCRIPT"
test -f "$BEDLAM_LEVEL_SEQUENCE_CSV_PATH"

echo "Project:   $PROJECT"
echo "Map:       $MAP"
echo "Map file:  $MAP_FILE"
echo "Input CSV: $BEDLAM_LEVEL_SEQUENCE_CSV_PATH"
echo "Root:      $BEDLAM_LEVEL_SEQUENCE_ROOT"

"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" \
    "$PROJECT" \
    "$MAP_FILE" \
    "-ExecCmds=py $WRAPPER_SCRIPT" \
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

echo "Level Sequence generation exited. Status: $BEDLAM_LEVEL_SEQUENCE_STATUS_DIR/linux_level_sequence_status.json"
