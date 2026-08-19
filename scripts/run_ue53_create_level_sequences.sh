#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/generated_asset_store.sh"
source "$SCRIPT_DIR/lib/load_config.sh"
load_bedlam_config

UE_ROOT="${UE_ROOT:-}"
PROJECT="${PROJECT:-}"
MAP="${MAP:-}"
MAP_FILE="${MAP_FILE:-}"
WRAPPER_SCRIPT="${WRAPPER_SCRIPT:-$REPO_ROOT/python/run_create_level_sequences_csv.py}"
require_bedlam_setting UE_ROOT
require_bedlam_setting PROJECT
require_bedlam_setting MAP
require_bedlam_setting MAP_FILE
require_bedlam_setting BEDLAM_LEVEL_SEQUENCE_CSV_PATH

export BEDLAM_LEVEL_SEQUENCE_SCRIPT="${BEDLAM_LEVEL_SEQUENCE_SCRIPT:-$UE_ROOT/Engine/Content/PS/Bedlam/Core/Python/create_level_sequences_csv.py}"
export BEDLAM_LEVEL_SEQUENCE_CSV_PATH
export BEDLAM_LEVEL_SEQUENCE_STATUS_DIR="${BEDLAM_LEVEL_SEQUENCE_STATUS_DIR:-$(dirname "$BEDLAM_LEVEL_SEQUENCE_CSV_PATH")}"
export BEDLAM_LEVEL_SEQUENCE_CAMERA_TYPE="${BEDLAM_LEVEL_SEQUENCE_CAMERA_TYPE:-Default}"
export BEDLAM_LEVEL_SEQUENCE_EXPECTED_MAP="${BEDLAM_LEVEL_SEQUENCE_EXPECTED_MAP:-$MAP}"
export BEDLAM_LEVEL_SEQUENCE_START_DELAY="${BEDLAM_LEVEL_SEQUENCE_START_DELAY:-15}"
export BEDLAM_LEVEL_SEQUENCE_START_TIMEOUT="${BEDLAM_LEVEL_SEQUENCE_START_TIMEOUT:-120}"
export BEDLAM_LEVEL_SEQUENCE_EXPORT_GEOMETRY_CACHE_OBJ="${BEDLAM_LEVEL_SEQUENCE_EXPORT_GEOMETRY_CACHE_OBJ:-0}"
export BEDLAM_GENERATED_ASSET_STORE="${BEDLAM_GENERATED_ASSET_STORE:-$BEDLAM_LEVEL_SEQUENCE_STATUS_DIR/unreal_assets}"
export BEDLAM_LEVEL_SEQUENCE_STATUS_PATH="${BEDLAM_LEVEL_SEQUENCE_STATUS_PATH:-$BEDLAM_GENERATED_ASSET_STORE/linux_level_sequence_status.json}"

PROJECT_DIR="$(dirname "$PROJECT")"
LEVEL_SEQUENCE_PROJECT_DIR="$PROJECT_DIR/Content/Bedlam/LevelSequences"
LEVEL_SEQUENCE_STORE_DIR="$BEDLAM_GENERATED_ASSET_STORE/LevelSequences"
ensure_generated_asset_link "$LEVEL_SEQUENCE_PROJECT_DIR" "$LEVEL_SEQUENCE_STORE_DIR"

RUN_TAG="${SLURM_JOB_ID:-manual}_$(date +%Y%m%d_%H%M%S)"
ZEN_DIR="/tmp/${USER}/unreal_zen_5.3.2_sequences_${RUN_TAG}"
DDC_DIR="/tmp/${USER}/unreal_ddc_5.3.2"
mkdir -p "$ZEN_DIR" "$DDC_DIR" "$BEDLAM_LEVEL_SEQUENCE_STATUS_DIR"
STATUS_PATH="$BEDLAM_LEVEL_SEQUENCE_STATUS_PATH"
mkdir -p "$(dirname "$STATUS_PATH")"
rm -f -- "$STATUS_PATH"

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
echo "Root:      /Game/Bedlam/LevelSequences"
echo "Assets:    $LEVEL_SEQUENCE_STORE_DIR"

"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" \
    "$PROJECT" \
    "$MAP_FILE" \
    "-ExecCmds=py $WRAPPER_SCRIPT" \
    -RenderOffscreen \
    -vulkan \
    -unattended \
    -NoSplash \
    -ResX=640 \
    -ResY=360 \
    "-ZenDataPath=$ZEN_DIR" \
    "-LocalDataCachePath=$DDC_DIR" \
    -stdout \
    -FullStdOutLogOutput

if ! grep -q '"status": "complete"' "$STATUS_PATH" 2>/dev/null; then
    echo "ERROR: Level Sequence generation did not complete successfully: $STATUS_PATH" >&2
    test ! -f "$STATUS_PATH" || cat "$STATUS_PATH" >&2
    exit 1
fi
echo "Level Sequence generation completed. Status: $STATUS_PATH"
