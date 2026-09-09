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

RUN_TAG="${SLURM_JOB_ID:-manual}_$$_$(date +%Y%m%d_%H%M%S)"
UE_USER_DIR="${BEDLAM_UE_USER_DIR:-/tmp/${USER}/unreal_user_5.3.2_${RUN_TAG}}"
export XDG_CONFIG_HOME="${BEDLAM_XDG_CONFIG_HOME:-$UE_USER_DIR/.config}"
export BEDLAM_RUNTIME_PROBE_DIR="${BEDLAM_RUNTIME_PROBE_DIR:-${BEDLAM_LOG_ROOT:-$PWD/unreal_logs}/bedlam_camera_runtime/${RUN_TAG}}"
export BEDLAM_RUNTIME_RENDER_DIR="${BEDLAM_RUNTIME_RENDER_DIR:-${BEDLAM_OUTPUT_ROOT:-$PWD/render_outputs}/${RUN_TAG}}"
export BEDLAM_RUNTIME_START_DELAY="${BEDLAM_RUNTIME_START_DELAY:-15}"
export BEDLAM_RUNTIME_READY_TIMEOUT="${BEDLAM_RUNTIME_READY_TIMEOUT:-300}"
export BEDLAM_RUNTIME_READY_PROBE_INTERVAL="${BEDLAM_RUNTIME_READY_PROBE_INTERVAL:-2}"
export BEDLAM_RUNTIME_READY_STABLE_PROBES="${BEDLAM_RUNTIME_READY_STABLE_PROBES:-3}"
export BEDLAM_RUNTIME_EXPECTED_MAP="${BEDLAM_RUNTIME_EXPECTED_MAP:-$MAP}"
export BEDLAM_RUNTIME_FORCE_LOOKAT="${BEDLAM_RUNTIME_FORCE_LOOKAT:-0}"
export BEDLAM_RUNTIME_TICK_GROUP_FIX="${BEDLAM_RUNTIME_TICK_GROUP_FIX:-0}"
export BEDLAM_RUNTIME_TICK_PREREQUISITE_FIX="${BEDLAM_RUNTIME_TICK_PREREQUISITE_FIX:-1}"
export BEDLAM_RUNTIME_RESTORE_UNBAKED="${BEDLAM_RUNTIME_RESTORE_UNBAKED:-0}"
export BEDLAM_RUNTIME_PRESERVE_BEDLAM_LAYOUT="${BEDLAM_RUNTIME_PRESERVE_BEDLAM_LAYOUT:-1}"
export BEDLAM_RUNTIME_IMAGE_SPATIAL_SAMPLES="${BEDLAM_RUNTIME_IMAGE_SPATIAL_SAMPLES:-0}"
export BEDLAM_RUNTIME_IMAGE_TEMPORAL_SAMPLES="${BEDLAM_RUNTIME_IMAGE_TEMPORAL_SAMPLES:-0}"
export BEDLAM_RUNTIME_WRITE_DONE_MARKERS="${BEDLAM_RUNTIME_WRITE_DONE_MARKERS:-1}"
export BEDLAM_RUNTIME_SKIP_DONE_SEQUENCES="${BEDLAM_RUNTIME_SKIP_DONE_SEQUENCES:-1}"
export BEDLAM_RUNTIME_JOB_NAME_FILTER="${BEDLAM_RUNTIME_JOB_NAME_FILTER:-}"
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
DDC_DIR="${UE_LocalDataCachePath:-/tmp/${USER}/unreal_ddc_5.3.2}"
# Installed engine cache graphs may ignore -LocalDataCachePath. Unix Unreal
# converts hyphens in environment-variable names to underscores.
export UE_LocalDataCachePath="$DDC_DIR"
mkdir -p "$ZEN_DIR" "$DDC_DIR" "$UE_USER_DIR" "$XDG_CONFIG_HOME" "$BEDLAM_RUNTIME_PROBE_DIR" "$BEDLAM_RUNTIME_RENDER_DIR"
RUNTIME_STATUS="$BEDLAM_RUNTIME_PROBE_DIR/runtime_render_status.json"
rm -f -- "$RUNTIME_STATUS"

test -x "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
test -f "$PROJECT"
test -f "$RENDER_SCRIPT"

TEXTURE_STREAMING_ARGS=()
if [[ "$BEDLAM_RUNTIME_NO_TEXTURE_STREAMING" == "1" ]]; then
    TEXTURE_STREAMING_ARGS+=(-NoTextureStreaming)
fi

RENDER_THREAD_ARGS=()
if [[ "${BEDLAM_UE_DISABLE_RENDER_THREAD:-0}" == "1" ]]; then
    RENDER_THREAD_ARGS+=(-norenderthread)
fi

SHARED_DDC_ARGS=()
if [[ -n "${BEDLAM_SHARED_DDC_PATH:-}" ]]; then
    mkdir -p "$BEDLAM_SHARED_DDC_PATH"
    SHARED_DDC_ARGS+=("-SharedDataCachePath=$BEDLAM_SHARED_DDC_PATH")
fi

echo "Runtime CSV directory: $BEDLAM_RUNTIME_PROBE_DIR"
echo "Rendered images:       $BEDLAM_RUNTIME_RENDER_DIR"
echo "Disable texture streaming: $BEDLAM_RUNTIME_NO_TEXTURE_STREAMING"
echo "Unreal user directory: $UE_USER_DIR"
echo "XDG config directory:  $XDG_CONFIG_HOME"
echo "Disable render thread: ${BEDLAM_UE_DISABLE_RENDER_THREAD:-0}"
echo "Shared DDC: ${BEDLAM_SHARED_DDC_PATH:-disabled}"
echo "Expected map: $BEDLAM_RUNTIME_EXPECTED_MAP"
echo "Skip completed sequences: $BEDLAM_RUNTIME_SKIP_DONE_SEQUENCES"
echo "Exact MRQ job filter: ${BEDLAM_RUNTIME_JOB_NAME_FILTER:-disabled}"

"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" \
    "$PROJECT" \
    "$MAP" \
    "-ExecCmds=$PYTHON_EXEC_CMD" \
    -RenderOffscreen \
    -vulkan \
    -unattended \
    -NoSplash \
    "${RENDER_THREAD_ARGS[@]}" \
    "${TEXTURE_STREAMING_ARGS[@]}" \
    -ResX=640 \
    -ResY=360 \
    "-ZenDataPath=$ZEN_DIR" \
    "-LocalDataCachePath=$DDC_DIR" \
    "${SHARED_DDC_ARGS[@]}" \
    "-UserDir=$UE_USER_DIR" \
    -stdout \
    -FullStdOutLogOutput

if ! python3 - "$RUNTIME_STATUS" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    status = json.load(handle)
assert status.get("status") == "complete", status
PY
then
    echo "ERROR: BEDLAM runtime renderer did not report successful completion: $RUNTIME_STATUS" >&2
    test ! -f "$RUNTIME_STATUS" || cat "$RUNTIME_STATUS" >&2
    exit 1
fi

echo "BEDLAM MRQ render completed."
