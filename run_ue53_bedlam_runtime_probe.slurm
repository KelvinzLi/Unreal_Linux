#!/usr/bin/env bash
#SBATCH --job-name=bedlam-rt-probe
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=02:00:00
#SBATCH --output=/work/kelvin/unreal_logs/bedlam_runtime_probe_%j.out

set -euo pipefail

UE_ROOT=/scratch/shared/beegfs/kelvin/apps/Linux_Unreal_Engine_5.3.2
PROJECT=/scratch/shared/beegfs/kelvin/apps/UnrealProjects/UE_5.3.2/SciFiModularOutpost/SciFiModularOutpost.uproject
MAP=/Game/SciFiModularOutpost/Maps/ShowCase
PROBE_SCRIPT=/athenahomes/kelvin/projects/Syn4D/unreal_linux/python/diagnostic/probe_mrq_runtime_camera.py

RUN_TAG="${SLURM_JOB_ID:-manual}_$(date +%Y%m%d_%H%M%S)"
export BEDLAM_RUNTIME_PROBE_DIR="${BEDLAM_RUNTIME_PROBE_DIR:-/work/kelvin/unreal_logs/bedlam_camera_runtime/${RUN_TAG}}"
export BEDLAM_RUNTIME_RENDER_DIR="${BEDLAM_RUNTIME_RENDER_DIR:-/work/kelvin/bedlam2/images/kaggle_eval/sim/outpost_ue53_runtime_probe/${RUN_TAG}}"
export BEDLAM_RUNTIME_START_DELAY="${BEDLAM_RUNTIME_START_DELAY:-15}"
export BEDLAM_RUNTIME_FORCE_LOOKAT="${BEDLAM_RUNTIME_FORCE_LOOKAT:-0}"
export BEDLAM_RUNTIME_TICK_GROUP_FIX="${BEDLAM_RUNTIME_TICK_GROUP_FIX:-0}"
export BEDLAM_RUNTIME_TICK_PREREQUISITE_FIX="${BEDLAM_RUNTIME_TICK_PREREQUISITE_FIX:-1}"
export BEDLAM_RUNTIME_RESTORE_UNBAKED="${BEDLAM_RUNTIME_RESTORE_UNBAKED:-0}"
export BEDLAM_RUNTIME_PRESERVE_BEDLAM_LAYOUT="${BEDLAM_RUNTIME_PRESERVE_BEDLAM_LAYOUT:-1}"
export BEDLAM_RUNTIME_IMAGE_TEMPORAL_SAMPLES="${BEDLAM_RUNTIME_IMAGE_TEMPORAL_SAMPLES:-7}"
export BEDLAM_RUNTIME_WRITE_DONE_MARKERS="${BEDLAM_RUNTIME_WRITE_DONE_MARKERS:-1}"

if [[ -n "${BEDLAM_RUNTIME_START_FRAME:-}" || -n "${BEDLAM_RUNTIME_END_FRAME:-}" ]]; then
    # A partial diagnostic render must never be advertised as post-process ready.
    export BEDLAM_RUNTIME_WRITE_DONE_MARKERS=0
fi

EXTRA_EXEC_CMDS="${BEDLAM_RUNTIME_EXEC_CMDS:-}"
if [[ -n "$EXTRA_EXEC_CMDS" ]]; then
    PYTHON_EXEC_CMD="${EXTRA_EXEC_CMDS},py ${PROBE_SCRIPT}"
else
    PYTHON_EXEC_CMD="py ${PROBE_SCRIPT}"
fi

ZEN_DIR="/tmp/${USER}/unreal_zen_5.3.2_${RUN_TAG}"
DDC_DIR="/tmp/${USER}/unreal_ddc_5.3.2"
mkdir -p "$ZEN_DIR" "$DDC_DIR" "$BEDLAM_RUNTIME_PROBE_DIR" "$BEDLAM_RUNTIME_RENDER_DIR"

test -x "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
test -f "$PROJECT"
test -f "$PROBE_SCRIPT"

echo "Runtime CSV directory: $BEDLAM_RUNTIME_PROBE_DIR"
echo "Rendered images:       $BEDLAM_RUNTIME_RENDER_DIR"

"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" \
    "$PROJECT" \
    "$MAP" \
    "-ExecCmds=$PYTHON_EXEC_CMD" \
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

echo "Runtime probe completed."
