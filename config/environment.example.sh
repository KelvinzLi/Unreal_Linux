#!/usr/bin/env bash

# Copy this file to config/local.sh and edit the absolute paths. The launchers
# load config/local.sh automatically. Existing environment variables take
# precedence, so one-off overrides such as UE_ROOT=/other/engine still work.

: "${UE_ROOT:=/absolute/path/to/Linux_Unreal_Engine_5.3.2}"
: "${BEDLAM_PROJECT_ROOT:=/absolute/path/to/UnrealProjects}"
: "${BEDLAM_DATASET_ROOT:=/absolute/path/to/datasets}"
: "${SYN4D_RENDERER_ROOT:=/absolute/path/to/Syn4d_renderer}"
: "${BEDLAM_CAMERA_ABLATION_SCRIPT:=$SYN4D_RENDERER_ROOT/unreal/render/Core/Python/tools/camera_sampling/generate_validated_orbit_camera_animations_ablation.py}"
: "${BEDLAM_OUTPUT_ROOT:=/absolute/path/to/render_outputs}"
: "${BEDLAM_LOG_ROOT:=/absolute/path/to/unreal_logs}"

# Optional paths used by installation, post-processing, and historical
# troubleshooting examples in LINUX_PIPELINE_RUNBOOK.md.
: "${CONDA_ROOT:=/absolute/path/to/miniconda3}"
: "${BEDLAM_PYTHON_ENV:=$CONDA_ROOT/envs/bedlam2-repaired}"
: "${ORIGINAL_BEDLAM_ENV:=$CONDA_ROOT/envs/bedlam2}"
: "${OIIO_ENV:=$CONDA_ROOT/envs/bedlam-oiio-tools}"
: "${PLUGIN_DOWNLOAD_ROOT:=/absolute/path/to/plugin_downloads}"
: "${PLUGIN_BACKUP_ROOT:=/absolute/path/to/plugin_backups}"
: "${BEDLAM_PLUGIN_SOURCE:=/absolute/path/to/compiled/BEDLAM}"
: "${SIMULATION_TEST_ROOT:=/absolute/path/to/simulation_tests}"
: "${METADATA_ROOT:=/absolute/path/to/metadata}"

# Optional defaults for scripts/run_ue53_bedlam_render.sh. These may instead
# be supplied for each invocation as PROJECT=..., MAP=..., and
# BEDLAM_RUNTIME_RENDER_DIR=....
: "${PROJECT:=}"
: "${MAP:=}"
: "${MAP_FILE:=}"

export UE_ROOT BEDLAM_PROJECT_ROOT BEDLAM_DATASET_ROOT SYN4D_RENDERER_ROOT
export BEDLAM_OUTPUT_ROOT BEDLAM_LOG_ROOT PROJECT MAP MAP_FILE
export BEDLAM_CAMERA_ABLATION_SCRIPT
export CONDA_ROOT BEDLAM_PYTHON_ENV ORIGINAL_BEDLAM_ENV OIIO_ENV
export PLUGIN_DOWNLOAD_ROOT PLUGIN_BACKUP_ROOT BEDLAM_PLUGIN_SOURCE
export SIMULATION_TEST_ROOT METADATA_ROOT
