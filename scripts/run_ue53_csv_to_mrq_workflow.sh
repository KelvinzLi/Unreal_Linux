#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/generated_asset_store.sh"
source "$SCRIPT_DIR/lib/load_config.sh"
load_bedlam_config

usage() {
    cat >&2 <<EOF
Usage: $0 \\
  --engine UE_ROOT \\
  --project PROJECT.uproject \\
  --map /Game/Path/Map \\
  --map-file /absolute/path/Map.umap \\
  --csv /absolute/path/be_seq.csv \\
  --output /absolute/render/output \\
  [--asset-store /absolute/generated/assets] \\
  [--preset 1-1-1_EXR_PNG_DepthMask] \\
  [--resolution 1280x720] \\
  [--legacy-motion-blur true|false] \\
  [--mrq-only]
EOF
}

UE_ROOT="${UE_ROOT:-}"
PROJECT=""
MAP=""
MAP_FILE=""
CSV=""
OUTPUT_DIR=""
ASSET_STORE=""
MRQ_PRESET="1-1-1_EXR_PNG_DepthMask"
MRQ_RESOLUTION="1280x720"
LEGACY_MOTION_BLUR="false"
MRQ_ONLY=0

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --engine) UE_ROOT="${2:?Missing value for --engine}"; shift 2 ;;
        --project) PROJECT="${2:?Missing value for --project}"; shift 2 ;;
        --map) MAP="${2:?Missing value for --map}"; shift 2 ;;
        --map-file) MAP_FILE="${2:?Missing value for --map-file}"; shift 2 ;;
        --csv) CSV="${2:?Missing value for --csv}"; shift 2 ;;
        --output) OUTPUT_DIR="${2:?Missing value for --output}"; shift 2 ;;
        --asset-store) ASSET_STORE="${2:?Missing value for --asset-store}"; shift 2 ;;
        --preset) MRQ_PRESET="${2:?Missing value for --preset}"; shift 2 ;;
        --resolution) MRQ_RESOLUTION="${2:?Missing value for --resolution}"; shift 2 ;;
        --legacy-motion-blur) LEGACY_MOTION_BLUR="${2:?Missing value for --legacy-motion-blur}"; shift 2 ;;
        --mrq-only) MRQ_ONLY=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: Unknown argument: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ -z "$UE_ROOT" || -z "$PROJECT" || -z "$MAP" || -z "$MAP_FILE" || -z "$CSV" || -z "$OUTPUT_DIR" ]]; then
    echo "ERROR: --engine, --project, --map, --map-file, --csv, and --output are required" >&2
    usage
    exit 2
fi
if [[ "$LEGACY_MOTION_BLUR" != "true" && "$LEGACY_MOTION_BLUR" != "false" ]]; then
    echo "ERROR: --legacy-motion-blur must be true or false" >&2
    exit 2
fi

PROJECT_DIR="$(dirname "$PROJECT")"
DATASET_DIR="$(dirname "$CSV")"
ASSET_STORE="${ASSET_STORE:-$DATASET_DIR/unreal_assets}"
COMBINED_WRAPPER="$REPO_ROOT/python/run_create_level_sequences_and_mrq.py"
MRQ_WRAPPER="$REPO_ROOT/python/run_create_movie_render_queue.py"

export BEDLAM_COMBINED_LEVEL_WRAPPER="$REPO_ROOT/python/run_create_level_sequences_csv.py"
export BEDLAM_COMBINED_MRQ_WRAPPER="$REPO_ROOT/python/run_create_movie_render_queue.py"
export BEDLAM_LEVEL_SEQUENCE_SCRIPT="$UE_ROOT/Engine/Content/PS/Bedlam/Core/Python/create_level_sequences_csv.py"
export BEDLAM_LEVEL_SEQUENCE_CSV_PATH="$CSV"
export BEDLAM_LEVEL_SEQUENCE_STATUS_DIR="$DATASET_DIR"
export BEDLAM_LEVEL_SEQUENCE_CAMERA_TYPE="Default"
export BEDLAM_LEVEL_SEQUENCE_EXPECTED_MAP="$MAP"
export BEDLAM_LEVEL_SEQUENCE_START_DELAY="15"
export BEDLAM_LEVEL_SEQUENCE_START_TIMEOUT="180"
export BEDLAM_LEVEL_SEQUENCE_EXPORT_GEOMETRY_CACHE_OBJ="0"
export BEDLAM_LEVEL_SEQUENCE_STATUS_PATH="$ASSET_STORE/linux_level_sequence_status.json"
export BEDLAM_MRQ_GENERATOR_SCRIPT="$UE_ROOT/Engine/Content/PS/Bedlam/Core/Python/create_movie_render_queue.py"
export BEDLAM_MRQ_OUTPUT_DIR="$OUTPUT_DIR"
export BEDLAM_MRQ_PRESET="$MRQ_PRESET"
export BEDLAM_MRQ_RESOLUTION="$MRQ_RESOLUTION"
export BEDLAM_MRQ_LEGACY_MOTION_BLUR="$LEGACY_MOTION_BLUR"
export BEDLAM_MRQ_EXPECTED_MAP="$MAP"
export BEDLAM_MRQ_START_DELAY="1"
export BEDLAM_MRQ_START_TIMEOUT="180"
export BEDLAM_MRQ_LEVEL_SEQUENCE_STATUS="$BEDLAM_LEVEL_SEQUENCE_STATUS_PATH"
export BEDLAM_MRQ_STATUS_PATH="$ASSET_STORE/linux_mrq_generation_status.json"

ensure_generated_asset_link "$PROJECT_DIR/Content/Bedlam/LevelSequences" "$ASSET_STORE/LevelSequences"
ensure_generated_asset_link "$PROJECT_DIR/Content/Bedlam/MovieRenderQueue" "$ASSET_STORE/MovieRenderQueue"

test -x "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
test -f "$PROJECT"
test -f "$MAP_FILE"
test -f "$CSV"
test -f "$DATASET_DIR/be_camera_animations.json"
if [[ "$MRQ_ONLY" -eq 1 ]]; then
    test -f "$MRQ_WRAPPER"
    RUN_WRAPPER="$MRQ_WRAPPER"
else
    test -f "$COMBINED_WRAPPER"
    RUN_WRAPPER="$COMBINED_WRAPPER"
fi

EXPECTED_SEQUENCES=$(awk -F, 'NR > 1 && $2 == "Group" {count++} END {print count + 0}' "$CSV")
if [[ "$EXPECTED_SEQUENCES" -lt 1 ]]; then
    echo "ERROR: CSV contains no Group rows: $CSV" >&2
    exit 1
fi
IFS=_ read -r -a PRESET_PARTS <<< "$BEDLAM_MRQ_PRESET"
GENERATE_IMAGE=0
GENERATE_DEPTH=0
for part in "${PRESET_PARTS[@]}"; do
    [[ "$part" == "EXR" || "$part" == "PNG" ]] && GENERATE_IMAGE=1
    [[ "$part" == "DepthMask" || "$part" == "DepthMaskNormals" ]] && GENERATE_DEPTH=1
done
JOBS_PER_SEQUENCE=$((GENERATE_IMAGE + GENERATE_DEPTH))
if [[ "$JOBS_PER_SEQUENCE" -lt 1 ]]; then
    echo "ERROR: MRQ preset requests no supported render jobs: $BEDLAM_MRQ_PRESET" >&2
    exit 1
fi
EXPECTED_JOBS=$((EXPECTED_SEQUENCES * JOBS_PER_SEQUENCE))

mkdir -p "$OUTPUT_DIR" "$ASSET_STORE"
if [[ "$MRQ_ONLY" -eq 1 ]]; then
    jq -e --argjson expected "$EXPECTED_SEQUENCES" \
        '.status == "complete" and (.expected_sequences | length) == $expected' \
        "$BEDLAM_LEVEL_SEQUENCE_STATUS_PATH" >/dev/null
    rm -f -- "$BEDLAM_MRQ_STATUS_PATH"
else
    rm -f -- "$BEDLAM_LEVEL_SEQUENCE_STATUS_PATH" "$BEDLAM_MRQ_STATUS_PATH"
fi
RUN_TAG="${SLURM_JOB_ID:-manual}_$(date +%Y%m%d_%H%M%S)"
ZEN_DIR="/tmp/${USER}/unreal_zen_5.3.2_combined_${RUN_TAG}"
DDC_DIR="/tmp/${USER}/unreal_ddc_5.3.2"
mkdir -p "$ZEN_DIR" "$DDC_DIR"

echo "Project:    $PROJECT"
echo "Map:        $MAP"
echo "CSV:        $CSV"
echo "Assets:     $ASSET_STORE"
echo "Render out: $OUTPUT_DIR"
echo "MRQ preset: $BEDLAM_MRQ_PRESET ($BEDLAM_MRQ_RESOLUTION)"
echo "Legacy motion blur: $BEDLAM_MRQ_LEGACY_MOTION_BLUR"
echo "Expected:   $EXPECTED_SEQUENCES sequences, $EXPECTED_JOBS MRQ jobs"
echo "Mode:       $([[ "$MRQ_ONLY" -eq 1 ]] && echo MRQ-only || echo LevelSequence+MRQ)"

"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" \
    "$PROJECT" \
    "$MAP_FILE" \
    "-ExecCmds=py $RUN_WRAPPER" \
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

jq -e --argjson expected "$EXPECTED_SEQUENCES" \
    '.status == "complete" and (.expected_sequences | length) == $expected' \
    "$BEDLAM_LEVEL_SEQUENCE_STATUS_PATH" >/dev/null
jq -e --argjson expected "$EXPECTED_JOBS" \
    '.status == "complete" and .expected_jobs == $expected' \
    "$BEDLAM_MRQ_STATUS_PATH" >/dev/null
echo "CSV-to-MRQ workflow complete: $CSV"
