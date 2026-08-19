#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/generated_asset_store.sh"
source "$SCRIPT_DIR/lib/load_config.sh"
load_bedlam_config

usage() {
    cat >&2 <<'EOF'
Usage: run_ue53_camera_placement_to_mrq_workflow.sh \
  --project PROJECT.uproject \
  --map /Game/Path/Map \
  --map-file /absolute/path/Map.umap \
  --base-csv /absolute/path/be_seq_base.csv \
  [--engine UE_ROOT] \
  [--output /absolute/render/output] \
  [--asset-store /absolute/generated/assets] \
  [--expanded-csv /absolute/path/be_seq_base_multicam.csv] \
  [--final-csv /absolute/path/be_seq.csv] \
  [--camera-preset camera_placement_9] \
  [--camera-count 9] \
  [--mrq-preset 1-1-1_EXR_PNG_DepthMask] \
  [--resolution 1280x720]
EOF
}

UE_ROOT="${UE_ROOT:-}"
PROJECT=""
MAP=""
MAP_FILE=""
BASE_CSV=""
OUTPUT_DIR=""
ASSET_STORE=""
EXPANDED_CSV=""
FINAL_CSV=""
CAMERA_PRESET="camera_placement_9"
CAMERA_COUNT=9
MRQ_PRESET="1-1-1_EXR_PNG_DepthMask"
RESOLUTION="1280x720"

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --engine) UE_ROOT="${2:?Missing value for --engine}"; shift 2 ;;
        --project) PROJECT="${2:?Missing value for --project}"; shift 2 ;;
        --map) MAP="${2:?Missing value for --map}"; shift 2 ;;
        --map-file) MAP_FILE="${2:?Missing value for --map-file}"; shift 2 ;;
        --base-csv) BASE_CSV="${2:?Missing value for --base-csv}"; shift 2 ;;
        --output) OUTPUT_DIR="${2:?Missing value for --output}"; shift 2 ;;
        --asset-store) ASSET_STORE="${2:?Missing value for --asset-store}"; shift 2 ;;
        --expanded-csv) EXPANDED_CSV="${2:?Missing value for --expanded-csv}"; shift 2 ;;
        --final-csv) FINAL_CSV="${2:?Missing value for --final-csv}"; shift 2 ;;
        --camera-preset) CAMERA_PRESET="${2:?Missing value for --camera-preset}"; shift 2 ;;
        --camera-count) CAMERA_COUNT="${2:?Missing value for --camera-count}"; shift 2 ;;
        --mrq-preset) MRQ_PRESET="${2:?Missing value for --mrq-preset}"; shift 2 ;;
        --resolution) RESOLUTION="${2:?Missing value for --resolution}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: Unknown argument: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ -z "$PROJECT" || -z "$MAP" || -z "$MAP_FILE" || -z "$BASE_CSV" ]]; then
    echo "ERROR: --project, --map, --map-file, and --base-csv are required" >&2
    usage
    exit 2
fi
require_bedlam_setting UE_ROOT
if [[ ! "$CAMERA_COUNT" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: --camera-count must be a positive integer" >&2
    exit 2
fi
case "$CAMERA_PRESET" in
    camera_placement_9)
        EXPECTED_CAMERA_COUNT=9
        ;;
    random_pair)
        EXPECTED_CAMERA_COUNT=2
        ;;
    *)
        echo "ERROR: Unsupported camera preset: $CAMERA_PRESET" >&2
        exit 2
        ;;
esac
if [[ "$CAMERA_COUNT" -ne "$EXPECTED_CAMERA_COUNT" ]]; then
    echo "ERROR: $CAMERA_PRESET generates $EXPECTED_CAMERA_COUNT cameras, not $CAMERA_COUNT" >&2
    exit 2
fi

PROJECT_DIR="$(cd "$(dirname "$PROJECT")" && pwd)"
DATASET_DIR="$(cd "$(dirname "$BASE_CSV")" && pwd)"
ASSET_STORE="${ASSET_STORE:-$DATASET_DIR/unreal_assets}"
OUTPUT_DIR="${OUTPUT_DIR:-$DATASET_DIR}"
EXPANDED_CSV="${EXPANDED_CSV:-$DATASET_DIR/be_seq_base_multicam.csv}"
FINAL_CSV="${FINAL_CSV:-$DATASET_DIR/be_seq.csv}"
WORKFLOW_WRAPPER="$REPO_ROOT/python/run_camera_placement_to_mrq.py"

for path in "$PROJECT" "$MAP_FILE" "$BASE_CSV" "$WORKFLOW_WRAPPER"; do
    test -f "$path"
done
test -x "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
if [[ "$BASE_CSV" == "$EXPANDED_CSV" || "$BASE_CSV" == "$FINAL_CSV" || "$EXPANDED_CSV" == "$FINAL_CSV" ]]; then
    echo "ERROR: Base, expanded, and final CSV paths must be distinct" >&2
    exit 2
fi

EXPECTED_BASE=$(awk -F, 'NR > 1 && $2 == "Group" {count++} END {print count + 0}' "$BASE_CSV")
if [[ "$EXPECTED_BASE" -lt 1 ]]; then
    echo "ERROR: Base CSV contains no Group rows: $BASE_CSV" >&2
    exit 1
fi
EXPECTED_FINAL=$((EXPECTED_BASE * CAMERA_COUNT))
IFS=_ read -r -a PRESET_PARTS <<< "$MRQ_PRESET"
GENERATE_IMAGE=0
GENERATE_DEPTH=0
for part in "${PRESET_PARTS[@]}"; do
    [[ "$part" == "EXR" || "$part" == "PNG" ]] && GENERATE_IMAGE=1
    [[ "$part" == "DepthMask" || "$part" == "DepthMaskNormals" ]] && GENERATE_DEPTH=1
done
JOBS_PER_SEQUENCE=$((GENERATE_IMAGE + GENERATE_DEPTH))
if [[ "$JOBS_PER_SEQUENCE" -lt 1 ]]; then
    echo "ERROR: MRQ preset requests no supported jobs: $MRQ_PRESET" >&2
    exit 1
fi
EXPECTED_JOBS=$((EXPECTED_FINAL * JOBS_PER_SEQUENCE))

ensure_generated_asset_link "$PROJECT_DIR/Content/Bedlam/LevelSequences" "$ASSET_STORE/LevelSequences"
ensure_generated_asset_link "$PROJECT_DIR/Content/Bedlam/MovieRenderQueue" "$ASSET_STORE/MovieRenderQueue"
mkdir -p "$ASSET_STORE" "$OUTPUT_DIR" "$(dirname "$EXPANDED_CSV")" "$(dirname "$FINAL_CSV")"

export BEDLAM_WORKFLOW_LEVEL_WRAPPER="$REPO_ROOT/python/run_create_level_sequences_csv.py"
export BEDLAM_WORKFLOW_CAMERA_WRAPPER="$REPO_ROOT/python/run_camera_sampling.py"
export BEDLAM_WORKFLOW_MRQ_WRAPPER="$REPO_ROOT/python/run_create_movie_render_queue.py"
export BEDLAM_WORKFLOW_BASE_CSV="$BASE_CSV"
export BEDLAM_WORKFLOW_EXPANDED_CSV="$EXPANDED_CSV"
export BEDLAM_WORKFLOW_FINAL_CSV="$FINAL_CSV"
export BEDLAM_WORKFLOW_EXPECTED_MAP="$MAP"
export BEDLAM_WORKFLOW_EXPECTED_BASE_SEQUENCES="$EXPECTED_BASE"
export BEDLAM_WORKFLOW_EXPECTED_FINAL_SEQUENCES="$EXPECTED_FINAL"
export BEDLAM_WORKFLOW_EXPECTED_MRQ_JOBS="$EXPECTED_JOBS"
export BEDLAM_WORKFLOW_INITIAL_LEVEL_STATUS="$ASSET_STORE/linux_initial_level_sequence_status.json"
export BEDLAM_WORKFLOW_FINAL_LEVEL_STATUS="$ASSET_STORE/linux_level_sequence_status.json"
export BEDLAM_WORKFLOW_STATUS_PATH="$ASSET_STORE/linux_camera_to_mrq_workflow_status.json"
export BEDLAM_WORKFLOW_START_TIMEOUT="180"

export BEDLAM_LEVEL_SEQUENCE_SCRIPT="$UE_ROOT/Engine/Content/PS/Bedlam/Core/Python/create_level_sequences_csv.py"
export BEDLAM_LEVEL_SEQUENCE_STATUS_DIR="$DATASET_DIR"
export BEDLAM_LEVEL_SEQUENCE_CAMERA_TYPE="Default"
export BEDLAM_LEVEL_SEQUENCE_EXPECTED_MAP="$MAP"
export BEDLAM_LEVEL_SEQUENCE_START_DELAY="0"
export BEDLAM_LEVEL_SEQUENCE_START_TIMEOUT="180"
export BEDLAM_LEVEL_SEQUENCE_EXPORT_GEOMETRY_CACHE_OBJ="0"
export BEDLAM_LEVEL_SEQUENCE_STATUS_PATH="$BEDLAM_WORKFLOW_INITIAL_LEVEL_STATUS"

# TODO: Port the generic sampler's newer Linux stability options
# (reuse_sequence_for_camera_pair and sequence_warmup_ticks) into the ablation
# sampler before relying on paired-camera sequence reuse in ablation workflows.
require_bedlam_setting SYN4D_RENDERER_ROOT
BEDLAM_CAMERA_ABLATION_SCRIPT="${BEDLAM_CAMERA_ABLATION_SCRIPT:-$SYN4D_RENDERER_ROOT/unreal/render/Core/Python/tools/camera_sampling/generate_validated_orbit_camera_animations_ablation.py}"
test -f "$BEDLAM_CAMERA_ABLATION_SCRIPT"
export BEDLAM_CAMERA_SAMPLING_SCRIPT="$BEDLAM_CAMERA_ABLATION_SCRIPT"
export BEDLAM_CAMERA_SAMPLING_CSV_PATH="$BASE_CSV"
export BEDLAM_CAMERA_SAMPLING_OUTPUT_CSV="$EXPANDED_CSV"
export BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON="$DATASET_DIR/be_camera_animations.json"
export BEDLAM_CAMERA_SAMPLING_SEQUENCE_ROOT="/Game/Bedlam/LevelSequences"
export BEDLAM_CAMERA_SAMPLING_EXPECTED_MAP="$MAP"
export BEDLAM_CAMERA_SAMPLING_START_DELAY="0"
export BEDLAM_CAMERA_SAMPLING_START_TIMEOUT="180"
export BEDLAM_CAMERA_SAMPLING_TIMEOUT="43200"
export BEDLAM_CAMERA_SAMPLING_PRESET="$CAMERA_PRESET"
export BEDLAM_CAMERA_SAMPLING_SEED="${BEDLAM_CAMERA_SAMPLING_SEED:-}"
export BEDLAM_CAMERA_SAMPLING_STATUS_PATH="$ASSET_STORE/linux_camera_sampling_status.json"

export BEDLAM_MRQ_GENERATOR_SCRIPT="$UE_ROOT/Engine/Content/PS/Bedlam/Core/Python/create_movie_render_queue.py"
export BEDLAM_MRQ_OUTPUT_DIR="$OUTPUT_DIR"
export BEDLAM_MRQ_PRESET="$MRQ_PRESET"
export BEDLAM_MRQ_RESOLUTION="$RESOLUTION"
export BEDLAM_MRQ_EXPECTED_MAP="$MAP"
export BEDLAM_MRQ_START_DELAY="0"
export BEDLAM_MRQ_START_TIMEOUT="180"
export BEDLAM_MRQ_LEVEL_SEQUENCE_STATUS="$BEDLAM_WORKFLOW_FINAL_LEVEL_STATUS"
export BEDLAM_MRQ_STATUS_PATH="$ASSET_STORE/linux_mrq_generation_status.json"

rm -f -- \
    "$BEDLAM_WORKFLOW_INITIAL_LEVEL_STATUS" \
    "$BEDLAM_WORKFLOW_FINAL_LEVEL_STATUS" \
    "$BEDLAM_CAMERA_SAMPLING_STATUS_PATH" \
    "$BEDLAM_MRQ_STATUS_PATH" \
    "$BEDLAM_WORKFLOW_STATUS_PATH"

RUN_TAG="${SLURM_JOB_ID:-manual}_$(date +%Y%m%d_%H%M%S)"
ZEN_DIR="/tmp/${USER}/unreal_zen_5.3.2_camera_to_mrq_${RUN_TAG}"
DDC_DIR="/tmp/${USER}/unreal_ddc_5.3.2"
mkdir -p "$ZEN_DIR" "$DDC_DIR"

echo "Project:          $PROJECT"
echo "Map:              $MAP"
echo "Base CSV:         $BASE_CSV ($EXPECTED_BASE sequences)"
echo "Expanded CSV:     $EXPANDED_CSV ($EXPECTED_FINAL expected)"
echo "Final CSV:        $FINAL_CSV"
echo "Generated assets: $ASSET_STORE"
echo "Render output:    $OUTPUT_DIR"
echo "MRQ:              $MRQ_PRESET $RESOLUTION ($EXPECTED_JOBS jobs)"
echo "WARNING: Existing generated Level Sequence and MRQ assets in this dedicated asset store"
echo "         will be removed after Unreal validates the requested map."

"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" \
    "$PROJECT" \
    "$MAP_FILE" \
    "-ExecCmds=tick.AllowAsyncTickDispatch 0,tick.AllowConcurrentTickQueue 0,py $WORKFLOW_WRAPPER" \
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

jq -e --argjson expected "$EXPECTED_FINAL" \
    '.status == "complete" and .final_sequences == $expected' \
    "$BEDLAM_WORKFLOW_STATUS_PATH" >/dev/null
jq -e --argjson expected "$EXPECTED_JOBS" \
    '.status == "complete" and .expected_jobs == $expected' \
    "$BEDLAM_MRQ_STATUS_PATH" >/dev/null
echo "Camera-placement-to-MRQ workflow complete: $FINAL_CSV"
