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
WRAPPER="${WRAPPER:-$REPO_ROOT/python/run_camera_sampling.py}"
require_bedlam_setting UE_ROOT
require_bedlam_setting PROJECT
require_bedlam_setting MAP
require_bedlam_setting MAP_FILE
require_bedlam_setting SYN4D_RENDERER_ROOT
require_bedlam_setting BEDLAM_CAMERA_SAMPLING_CSV_PATH

export BEDLAM_CAMERA_SAMPLING_SCRIPT="${BEDLAM_CAMERA_SAMPLING_SCRIPT:-$SYN4D_RENDERER_ROOT/unreal/render/Core/Python/tools/camera_sampling/generate_validated_orbit_camera_animations.py}"
export BEDLAM_CAMERA_SAMPLING_CSV_PATH
export BEDLAM_CAMERA_SAMPLING_OUTPUT_CSV="${BEDLAM_CAMERA_SAMPLING_OUTPUT_CSV:-$(dirname "$BEDLAM_CAMERA_SAMPLING_CSV_PATH")/be_seq_multicam.csv}"
export BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON="${BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON:-$(dirname "$BEDLAM_CAMERA_SAMPLING_CSV_PATH")/be_camera_animations.json}"
export BEDLAM_CAMERA_SAMPLING_SEQUENCE_ROOT="${BEDLAM_CAMERA_SAMPLING_SEQUENCE_ROOT:-/Game/Bedlam/LevelSequences}"
export BEDLAM_CAMERA_SAMPLING_SEED="${BEDLAM_CAMERA_SAMPLING_SEED:-}"
export BEDLAM_CAMERA_SAMPLING_EXPECTED_MAP="${BEDLAM_CAMERA_SAMPLING_EXPECTED_MAP:-$MAP}"
export BEDLAM_CAMERA_SAMPLING_START_DELAY="${BEDLAM_CAMERA_SAMPLING_START_DELAY:-15}"
export BEDLAM_CAMERA_SAMPLING_START_TIMEOUT="${BEDLAM_CAMERA_SAMPLING_START_TIMEOUT:-180}"
export BEDLAM_CAMERA_SAMPLING_STATUS_DIR="${BEDLAM_CAMERA_SAMPLING_STATUS_DIR:-$(dirname "$BEDLAM_CAMERA_SAMPLING_CSV_PATH")}"
export BEDLAM_GENERATED_ASSET_STORE="${BEDLAM_GENERATED_ASSET_STORE:-$BEDLAM_CAMERA_SAMPLING_STATUS_DIR/unreal_assets}"
export BEDLAM_CAMERA_SAMPLING_LEVEL_SEQUENCE_STATUS="${BEDLAM_CAMERA_SAMPLING_LEVEL_SEQUENCE_STATUS:-$BEDLAM_GENERATED_ASSET_STORE/linux_level_sequence_status.json}"
export BEDLAM_CAMERA_SAMPLING_STATUS_PATH="${BEDLAM_CAMERA_SAMPLING_STATUS_PATH:-$BEDLAM_GENERATED_ASSET_STORE/linux_camera_sampling_status.json}"

PROJECT_DIR="$(dirname "$PROJECT")"
LEVEL_SEQUENCE_PROJECT_DIR="$PROJECT_DIR/Content/Bedlam/LevelSequences"
LEVEL_SEQUENCE_STORE_DIR="$BEDLAM_GENERATED_ASSET_STORE/LevelSequences"
ensure_generated_asset_link "$LEVEL_SEQUENCE_PROJECT_DIR" "$LEVEL_SEQUENCE_STORE_DIR"

RUN_TAG="${SLURM_JOB_ID:-manual}_$(date +%Y%m%d_%H%M%S)"
ZEN_DIR="/tmp/${USER}/unreal_zen_5.3.2_camera_${RUN_TAG}"
DDC_DIR="/tmp/${USER}/unreal_ddc_5.3.2"
mkdir -p \
    "$ZEN_DIR" \
    "$DDC_DIR" \
    "$BEDLAM_CAMERA_SAMPLING_STATUS_DIR" \
    "$(dirname "$BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON")" \
    "$(dirname "$BEDLAM_CAMERA_SAMPLING_STATUS_PATH")"

test -x "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
test -f "$PROJECT"
test -f "$MAP_FILE"
test -f "$WRAPPER"
test -f "$BEDLAM_CAMERA_SAMPLING_SCRIPT"
test -f "$BEDLAM_CAMERA_SAMPLING_CSV_PATH"

if ! jq -e '.status == "complete"' \
    "$BEDLAM_CAMERA_SAMPLING_LEVEL_SEQUENCE_STATUS" >/dev/null 2>&1; then
    echo "ERROR: Level Sequence generation is not complete: $BEDLAM_CAMERA_SAMPLING_LEVEL_SEQUENCE_STATUS" >&2
    test ! -f "$BEDLAM_CAMERA_SAMPLING_LEVEL_SEQUENCE_STATUS" || \
        cat "$BEDLAM_CAMERA_SAMPLING_LEVEL_SEQUENCE_STATUS" >&2
    exit 1
fi

expected_sequences=$(jq -r '.expected_sequences | length' "$BEDLAM_CAMERA_SAMPLING_LEVEL_SEQUENCE_STATUS")
if [[ "$expected_sequences" -lt 1 ]]; then
    echo "ERROR: Level Sequence manifest contains no expected sequences" >&2
    exit 1
fi

missing_sequences=0
while IFS= read -r sequence_name; do
    if [[ ! -f "$LEVEL_SEQUENCE_STORE_DIR/$sequence_name.uasset" ]]; then
        echo "ERROR: Missing generated Level Sequence: $LEVEL_SEQUENCE_STORE_DIR/$sequence_name.uasset" >&2
        missing_sequences=$((missing_sequences + 1))
    fi
done < <(jq -r '.expected_sequences[]' "$BEDLAM_CAMERA_SAMPLING_LEVEL_SEQUENCE_STATUS")
if [[ "$missing_sequences" -ne 0 ]]; then
    exit 1
fi

if [[ "$BEDLAM_CAMERA_SAMPLING_CSV_PATH" == "$BEDLAM_CAMERA_SAMPLING_OUTPUT_CSV" ]]; then
    echo "ERROR: Input and output camera CSV paths must be different" >&2
    exit 1
fi

rm -f -- \
    "$BEDLAM_CAMERA_SAMPLING_STATUS_PATH" \
    "$BEDLAM_CAMERA_SAMPLING_OUTPUT_CSV" \
    "$BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON"

echo "Project:         $PROJECT"
echo "Map:             $BEDLAM_CAMERA_SAMPLING_EXPECTED_MAP"
echo "Input CSV:       $BEDLAM_CAMERA_SAMPLING_CSV_PATH"
echo "Sequence assets: $LEVEL_SEQUENCE_STORE_DIR ($expected_sequences expected)"
echo "Output CSV:      $BEDLAM_CAMERA_SAMPLING_OUTPUT_CSV"
echo "Output JSON:     $BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON"
echo "Status:          $BEDLAM_CAMERA_SAMPLING_STATUS_PATH"

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

if ! jq -e '.status == "complete"' \
    "$BEDLAM_CAMERA_SAMPLING_STATUS_PATH" >/dev/null 2>&1; then
    echo "ERROR: Camera sampling did not complete successfully: $BEDLAM_CAMERA_SAMPLING_STATUS_PATH" >&2
    test ! -f "$BEDLAM_CAMERA_SAMPLING_STATUS_PATH" || \
        cat "$BEDLAM_CAMERA_SAMPLING_STATUS_PATH" >&2
    exit 1
fi

echo "Camera sampling completed. Status: $BEDLAM_CAMERA_SAMPLING_STATUS_PATH"
