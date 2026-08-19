#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/load_config.sh"
load_bedlam_config

require_bedlam_setting UE_ROOT
require_bedlam_setting SYN4D_RENDERER_ROOT

errors=0
check_file() {
    local path=$1
    if [[ -f "$path" ]]; then
        printf 'OK      %s\n' "$path"
    else
        printf 'MISSING %s\n' "$path" >&2
        errors=$((errors + 1))
    fi
}

check_executable() {
    local path=$1
    if [[ -x "$path" ]]; then
        printf 'OK      %s\n' "$path"
    else
        printf 'MISSING %s (not executable)\n' "$path" >&2
        errors=$((errors + 1))
    fi
}

check_directory() {
    local path=$1
    if [[ -d "$path" ]]; then
        printf 'OK      %s/\n' "$path"
    else
        printf 'MISSING %s/\n' "$path" >&2
        errors=$((errors + 1))
    fi
}

note_optional_path() {
    local path=$1
    if [[ -e "$path" ]]; then
        printf 'OK      %s\n' "$path"
    else
        printf 'OPTIONAL not present: %s\n' "$path"
    fi
}

echo "Checking Unreal Engine"
check_executable "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"

echo "Checking BEDLAM and Bridge plugins"
check_file "$UE_ROOT/Engine/Plugins/BEDLAM/BEDLAM.uplugin"
check_file "$UE_ROOT/Engine/Plugins/BEDLAM/Binaries/Linux/libUnrealEditor-BEDLAM.so"
check_file "$UE_ROOT/Engine/Plugins/Bridge/Bridge.uplugin"
check_file "$UE_ROOT/Engine/Plugins/Bridge/Binaries/Linux/UnrealEditor.modules"

echo "Checking modified Movie Render Pipeline"
check_file "$UE_ROOT/Engine/Plugins/MovieScene/MovieRenderPipeline/MovieRenderPipeline.uplugin"
check_file "$UE_ROOT/Engine/Plugins/MovieScene/MovieRenderPipeline/Binaries/Linux/libUnrealEditor-MovieRenderPipelineCore.so"
check_file "$UE_ROOT/Engine/Plugins/MovieScene/MovieRenderPipeline/Binaries/Linux/libUnrealEditor-MovieRenderPipelineRenderPasses.so"

BEDLAM_CONTENT="$UE_ROOT/Engine/Content/PS/Bedlam"
echo "Checking BEDLAM Core content and Engine Python tools"
check_file "$BEDLAM_CONTENT/Core/BE_CineCameraActor_Blueprint.uasset"
check_file "$BEDLAM_CONTENT/Core/BE_CameraOperator.uasset"
check_file "$BEDLAM_CONTENT/Core/EditorScripting/BEDLAM2.uasset"
check_file "$BEDLAM_CONTENT/Core/Python/create_level_sequences_csv.py"
check_file "$BEDLAM_CONTENT/Core/Python/create_movie_render_queue.py"

echo "Checking BEDLAM asset libraries"
for directory in Clothing HDRI Hair SMPLX_LH SMPLX_LH_animations Shoes; do
    check_directory "$BEDLAM_CONTENT/$directory"
done

echo "Checking object libraries"
check_directory "$UE_ROOT/Engine/Content/PS/obj"

echo "Checking Syn4D renderer tools"
check_file "$SYN4D_RENDERER_ROOT/unreal/render/Core/Python/tools/sim_throw_csv_objects_batch.py"
check_file "$SYN4D_RENDERER_ROOT/unreal/render/Core/Python/tools/camera_sampling/generate_validated_orbit_camera_animations.py"
BEDLAM_CAMERA_ABLATION_SCRIPT="${BEDLAM_CAMERA_ABLATION_SCRIPT:-$SYN4D_RENDERER_ROOT/unreal/render/Core/Python/tools/camera_sampling/generate_validated_orbit_camera_animations_ablation.py}"
note_optional_path "$BEDLAM_CAMERA_ABLATION_SCRIPT"

for variable in BEDLAM_PROJECT_ROOT BEDLAM_DATASET_ROOT BEDLAM_OUTPUT_ROOT BEDLAM_LOG_ROOT; do
    if [[ -n "${!variable:-}" ]]; then
        note_optional_path "${!variable}"
    else
        printf 'OPTIONAL %s is not configured\n' "$variable"
    fi
done

if [[ "$errors" -ne 0 ]]; then
    echo "ERROR: installation verification found $errors missing requirement(s)" >&2
    exit 1
fi

echo "BEDLAM Linux installation verification passed."
