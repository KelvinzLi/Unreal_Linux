#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -lt 4 || "$#" -gt 5 ]]; then
    echo "Usage: $0 PROJECT MAP MAP_FILE BE_SEQ_BASE_CSV [GENERATED_ASSET_STORE]" >&2
    exit 2
fi

PROJECT="$1"
MAP="$2"
MAP_FILE="$3"
INPUT_CSV="$4"
DATASET_DIR="$(cd "$(dirname "$INPUT_CSV")" && pwd)"
ASSET_STORE="${5:-$DATASET_DIR/unreal_assets}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PROJECT MAP MAP_FILE
export BEDLAM_CAMERA_SAMPLING_PRESET="camera_placement_9"
export BEDLAM_CAMERA_SAMPLING_SCRIPT="/athenahomes/kelvin/projects/Syn4D/Syn4d_renderer/unreal/render/Core/Python/tools/camera_sampling/generate_validated_orbit_camera_animations_ablation.py"
export BEDLAM_CAMERA_SAMPLING_CSV_PATH="$INPUT_CSV"
export BEDLAM_CAMERA_SAMPLING_OUTPUT_CSV="$DATASET_DIR/be_seq_base_multicam.csv"
export BEDLAM_CAMERA_SAMPLING_OUTPUT_JSON="$DATASET_DIR/be_camera_animations.json"
export BEDLAM_CAMERA_SAMPLING_STATUS_DIR="$DATASET_DIR"
export BEDLAM_GENERATED_ASSET_STORE="$ASSET_STORE"
export BEDLAM_CAMERA_SAMPLING_TIMEOUT="${BEDLAM_CAMERA_SAMPLING_TIMEOUT:-43200}"

exec "$SCRIPT_DIR/run_ue53_camera_sampling.sh"
