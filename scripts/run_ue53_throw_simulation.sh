#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/load_config.sh"
load_bedlam_config

UE_ROOT="${UE_ROOT:-}"
PROJECT="${PROJECT:-}"
MAP="${MAP:-}"
WRAPPER_SCRIPT="${WRAPPER_SCRIPT:-$REPO_ROOT/python/run_throw_simulation_batch.py}"
require_bedlam_setting UE_ROOT
require_bedlam_setting PROJECT
require_bedlam_setting MAP
require_bedlam_setting SYN4D_RENDERER_ROOT
require_bedlam_setting BEDLAM_SIM_CSV_PATH

export BEDLAM_SIM_BATCH_SCRIPT="${BEDLAM_SIM_BATCH_SCRIPT:-$SYN4D_RENDERER_ROOT/unreal/render/Core/Python/tools/sim_throw_csv_objects_batch.py}"
export BEDLAM_SIM_CSV_PATH
export BEDLAM_SIM_OUTPUT_DIR="${BEDLAM_SIM_OUTPUT_DIR:-$(dirname "$BEDLAM_SIM_CSV_PATH")/simulation_output}"
export BEDLAM_SIM_NUM_THROW_OBJECTS="${BEDLAM_SIM_NUM_THROW_OBJECTS:-20}"
export BEDLAM_SIM_SCALE_MULTIPLIER="${BEDLAM_SIM_SCALE_MULTIPLIER:-0.5}"
export BEDLAM_SIM_PHYSICS_SUBSTEPPING="${BEDLAM_SIM_PHYSICS_SUBSTEPPING:-1}"
export BEDLAM_SIM_PHYSICS_SUBSTEP_FPS="${BEDLAM_SIM_PHYSICS_SUBSTEP_FPS:-480}"
export BEDLAM_SIM_PHYSICS_MAX_SUBSTEPS="${BEDLAM_SIM_PHYSICS_MAX_SUBSTEPS:-32}"
export BEDLAM_SIM_MAX_RESIMULATION_ATTEMPTS="${BEDLAM_SIM_MAX_RESIMULATION_ATTEMPTS:-8}"
export BEDLAM_SIM_SEED="${BEDLAM_SIM_SEED:-12345}"
export BEDLAM_SIM_LIMIT="${BEDLAM_SIM_LIMIT:-0}"
export BEDLAM_SIM_CONTINUE_ON_ERROR="${BEDLAM_SIM_CONTINUE_ON_ERROR:-0}"

RUN_TAG="${SLURM_JOB_ID:-manual}_$(date +%Y%m%d_%H%M%S)"
ZEN_DIR="/tmp/${USER}/unreal_zen_5.3.2_sim_${RUN_TAG}"
DDC_DIR="/tmp/${USER}/unreal_ddc_5.3.2"
mkdir -p "$ZEN_DIR" "$DDC_DIR" "$BEDLAM_SIM_OUTPUT_DIR"

test -x "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
test -f "$PROJECT"
test -f "$WRAPPER_SCRIPT"
test -f "$BEDLAM_SIM_BATCH_SCRIPT"
test -f "$BEDLAM_SIM_CSV_PATH"

echo "Project:    $PROJECT"
echo "Map:        $MAP"
echo "Input CSV:  $BEDLAM_SIM_CSV_PATH"
echo "Output:     $BEDLAM_SIM_OUTPUT_DIR"
echo "Sequences:  ${BEDLAM_SIM_LIMIT} (0 means all)"
echo "Objects:    $BEDLAM_SIM_NUM_THROW_OBJECTS"
echo "Seed:       $BEDLAM_SIM_SEED"

"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" \
    "$PROJECT" \
    "$MAP" \
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

echo "Simulation process exited. Status: $BEDLAM_SIM_OUTPUT_DIR/linux_simulation_status.json"
