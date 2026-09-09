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
export BEDLAM_SIM_FIXED_STEP_FPS="${BEDLAM_SIM_FIXED_STEP_FPS:-0}"
export BEDLAM_SIM_PREINITIALIZE_SEQUENCE_PLAYER="${BEDLAM_SIM_PREINITIALIZE_SEQUENCE_PLAYER:-0}"
export BEDLAM_SIM_MAX_RESIMULATION_ATTEMPTS="${BEDLAM_SIM_MAX_RESIMULATION_ATTEMPTS:-8}"
export BEDLAM_SIM_RERUN_ON_BAD_SPEED="${BEDLAM_SIM_RERUN_ON_BAD_SPEED:-0}"
export BEDLAM_SIM_BAD_SPEED_EARLY_MEDIAN_CM_S="${BEDLAM_SIM_BAD_SPEED_EARLY_MEDIAN_CM_S:-240}"
export BEDLAM_SIM_BAD_SPEED_EARLY_GAP_END_FRAME="${BEDLAM_SIM_BAD_SPEED_EARLY_GAP_END_FRAME:-15}"
export BEDLAM_SIM_BAD_SPEED_MIN_EARLY_GAP_FRAMES="${BEDLAM_SIM_BAD_SPEED_MIN_EARLY_GAP_FRAMES:-6}"
export BEDLAM_SIM_SEED="${BEDLAM_SIM_SEED:-12345}"
export BEDLAM_SIM_LIMIT="${BEDLAM_SIM_LIMIT:-0}"
export BEDLAM_SIM_CONTINUE_ON_ERROR="${BEDLAM_SIM_CONTINUE_ON_ERROR:-0}"

RUN_TAG="${SLURM_JOB_ID:-manual}_$$_$(date +%Y%m%d_%H%M%S)"
ZEN_DIR="/tmp/${USER}/unreal_zen_5.3.2_sim_${RUN_TAG}"
DDC_DIR="${UE_LocalDataCachePath:-/tmp/${USER}/unreal_ddc_5.3.2}"
export UE_LocalDataCachePath="$DDC_DIR"
UE_USER_DIR="${BEDLAM_UE_USER_DIR:-/tmp/${USER}/unreal_user_5.3.2_sim_${RUN_TAG}}"
export XDG_CONFIG_HOME="${BEDLAM_XDG_CONFIG_HOME:-$UE_USER_DIR/.config}"
mkdir -p "$ZEN_DIR" "$DDC_DIR" "$UE_USER_DIR" "$XDG_CONFIG_HOME" "$BEDLAM_SIM_OUTPUT_DIR"

SHARED_DDC_ARGS=()
if [[ -n "${BEDLAM_SHARED_DDC_PATH:-}" ]]; then
    mkdir -p "$BEDLAM_SHARED_DDC_PATH"
    SHARED_DDC_ARGS+=("-SharedDataCachePath=$BEDLAM_SHARED_DDC_PATH")
fi

FIXED_STEP_ARGS=()
if [[ "$BEDLAM_SIM_FIXED_STEP_FPS" != "0" ]]; then
    FIXED_STEP_ARGS+=("-UseFixedTimeStep" "-FPS=$BEDLAM_SIM_FIXED_STEP_FPS")
fi

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
echo "Objects:    ${BEDLAM_SIM_NUM_THROW_OBJECTS_RANGE:-$BEDLAM_SIM_NUM_THROW_OBJECTS}"
echo "Seed:       $BEDLAM_SIM_SEED"
echo "Fixed step: $BEDLAM_SIM_FIXED_STEP_FPS (0 means disabled)"
echo "Pre-init:   $BEDLAM_SIM_PREINITIALIZE_SEQUENCE_PLAYER"
echo "Speed retry: $BEDLAM_SIM_RERUN_ON_BAD_SPEED"
echo "User dir:   $UE_USER_DIR"
echo "XDG config: $XDG_CONFIG_HOME"
echo "Shared DDC: ${BEDLAM_SHARED_DDC_PATH:-disabled}"

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
    "${SHARED_DDC_ARGS[@]}" \
    "${FIXED_STEP_ARGS[@]}" \
    "-UserDir=$UE_USER_DIR" \
    -stdout \
    -FullStdOutLogOutput

echo "Simulation process exited. Status: $BEDLAM_SIM_OUTPUT_DIR/linux_simulation_status.json"
