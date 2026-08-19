#!/usr/bin/env bash
#SBATCH --job-name=bedlam-render
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
# Configure Slurm output with sbatch --output; paths in #SBATCH directives
# cannot be read from config/local.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/load_config.sh"
load_bedlam_config

UE_ROOT="${UE_ROOT:-}"
PROJECT="${PROJECT:-}"
MAP="${MAP:-}"
RENDER_SCRIPT="${RENDER_SCRIPT:-$REPO_ROOT/python/render_bedlam_mrq.py}"
require_bedlam_setting UE_ROOT
require_bedlam_setting PROJECT
require_bedlam_setting MAP

RUN_TAG="${SLURM_JOB_ID:-manual}_$(date +%Y%m%d_%H%M%S)"
export BEDLAM_RUNTIME_PROBE_DIR="${BEDLAM_RUNTIME_PROBE_DIR:-${BEDLAM_LOG_ROOT:-$PWD/unreal_logs}/bedlam_camera_runtime/${RUN_TAG}}"
export BEDLAM_RUNTIME_RENDER_DIR="${BEDLAM_RUNTIME_RENDER_DIR:-${BEDLAM_OUTPUT_ROOT:-$PWD/render_outputs}/${RUN_TAG}}"
export BEDLAM_RUNTIME_START_DELAY="${BEDLAM_RUNTIME_START_DELAY:-15}"
export BEDLAM_RUNTIME_FORCE_LOOKAT="${BEDLAM_RUNTIME_FORCE_LOOKAT:-0}"
export BEDLAM_RUNTIME_TICK_GROUP_FIX="${BEDLAM_RUNTIME_TICK_GROUP_FIX:-0}"
export BEDLAM_RUNTIME_TICK_PREREQUISITE_FIX="${BEDLAM_RUNTIME_TICK_PREREQUISITE_FIX:-1}"
export BEDLAM_RUNTIME_RESTORE_UNBAKED="${BEDLAM_RUNTIME_RESTORE_UNBAKED:-0}"
export BEDLAM_RUNTIME_PRESERVE_BEDLAM_LAYOUT="${BEDLAM_RUNTIME_PRESERVE_BEDLAM_LAYOUT:-1}"
export BEDLAM_RUNTIME_IMAGE_SPATIAL_SAMPLES="${BEDLAM_RUNTIME_IMAGE_SPATIAL_SAMPLES:-0}"
export BEDLAM_RUNTIME_IMAGE_TEMPORAL_SAMPLES="${BEDLAM_RUNTIME_IMAGE_TEMPORAL_SAMPLES:-0}"
export BEDLAM_RUNTIME_WRITE_DONE_MARKERS="${BEDLAM_RUNTIME_WRITE_DONE_MARKERS:-1}"
export BEDLAM_RUNTIME_NO_TEXTURE_STREAMING="${BEDLAM_RUNTIME_NO_TEXTURE_STREAMING:-1}"

if [[ -n "${BEDLAM_RUNTIME_START_FRAME:-}" || -n "${BEDLAM_RUNTIME_END_FRAME:-}" ]]; then
    # A partial diagnostic render must never be advertised as post-process ready.
    export BEDLAM_RUNTIME_WRITE_DONE_MARKERS=0
fi

EXTRA_EXEC_CMDS="${BEDLAM_RUNTIME_EXEC_CMDS:-}"
if [[ -n "$EXTRA_EXEC_CMDS" ]]; then
    PYTHON_EXEC_CMD="${EXTRA_EXEC_CMDS},py ${RENDER_SCRIPT}"
else
    PYTHON_EXEC_CMD="py ${RENDER_SCRIPT}"
fi

ZEN_DIR="/tmp/${USER}/unreal_zen_5.3.2_${RUN_TAG}"
DDC_DIR="/tmp/${USER}/unreal_ddc_5.3.2"
mkdir -p "$ZEN_DIR" "$DDC_DIR" "$BEDLAM_RUNTIME_PROBE_DIR" "$BEDLAM_RUNTIME_RENDER_DIR"

test -x "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
test -f "$PROJECT"
test -f "$RENDER_SCRIPT"

TEXTURE_STREAMING_ARGS=()
if [[ "$BEDLAM_RUNTIME_NO_TEXTURE_STREAMING" == "1" ]]; then
    TEXTURE_STREAMING_ARGS+=(-NoTextureStreaming)
fi

echo "Runtime CSV directory: $BEDLAM_RUNTIME_PROBE_DIR"
echo "Rendered images:       $BEDLAM_RUNTIME_RENDER_DIR"
echo "Disable texture streaming: $BEDLAM_RUNTIME_NO_TEXTURE_STREAMING"

"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" \
    "$PROJECT" \
    "$MAP" \
    "-ExecCmds=$PYTHON_EXEC_CMD" \
    -RenderOffscreen \
    -vulkan \
    -unattended \
    -NoSplash \
    "${TEXTURE_STREAMING_ARGS[@]}" \
    -ResX=640 \
    -ResY=360 \
    "-ZenDataPath=$ZEN_DIR" \
    "-LocalDataCachePath=$DDC_DIR" \
    -stdout \
    -FullStdOutLogOutput

echo "BEDLAM MRQ render completed."
