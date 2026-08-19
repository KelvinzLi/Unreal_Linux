#!/usr/bin/env bash

# Reproduce the tested BEDLAM post-processing environments without modifying
# the original BEDLAM environment. Paths may come from config/local.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/load_config.sh"
load_bedlam_config

require_bedlam_setting CONDA_ROOT
require_bedlam_setting BEDLAM_PYTHON_ENV
require_bedlam_setting OIIO_ENV
require_bedlam_setting SYN4D_RENDERER_ROOT

CONDA="$CONDA_ROOT/bin/conda"
REQUIREMENTS="$SYN4D_RENDERER_ROOT/requirements.txt"
test -x "$CONDA"
test -f "$REQUIREMENTS"

if [[ -e "$BEDLAM_PYTHON_ENV" ]]; then
    echo "ERROR: repaired environment already exists: $BEDLAM_PYTHON_ENV" >&2
    echo "Move or remove it explicitly before requesting a clean rebuild." >&2
    exit 1
fi

if [[ -n "${ORIGINAL_BEDLAM_ENV:-}" && -d "$ORIGINAL_BEDLAM_ENV" ]]; then
    echo "Cloning existing BEDLAM environment: $ORIGINAL_BEDLAM_ENV"
    "$CONDA" create --clone "$ORIGINAL_BEDLAM_ENV" -p "$BEDLAM_PYTHON_ENV" -y

    # The clone may contain overlapping Conda and pip copies of these packages.
    # Modify only the new clone, then reinstall the renderer requirements.
    remove_packages=()
    package_list_json="$("$CONDA" list -p "$BEDLAM_PYTHON_ENV" --json)"
    for package in openimageio openexr numpy; do
        if jq -e --arg name "$package" \
            'any(.[]; .name == $name)' <<<"$package_list_json" >/dev/null; then
            remove_packages+=("$package")
        fi
    done
    if (( ${#remove_packages[@]} )); then
        "$CONDA" remove -p "$BEDLAM_PYTHON_ENV" \
            "${remove_packages[@]}" --force-remove -y
    fi
else
    echo "No original BEDLAM environment found; creating a clean Python 3.10 environment."
    "$CONDA" create -p "$BEDLAM_PYTHON_ENV" python=3.10 pip -y
fi

"$BEDLAM_PYTHON_ENV/bin/python" -m pip install \
    --no-cache-dir -r "$REQUIREMENTS"

if [[ ! -e "$OIIO_ENV" ]]; then
    "$CONDA" create -p "$OIIO_ENV" -c conda-forge openimageio-tools -y
fi

"$BEDLAM_PYTHON_ENV/bin/python" - <<'PY'
import cv2
import kaolin
import numpy
import OpenEXR
import scipy
import sklearn
import torch
from scipy.spatial import cKDTree

print("numpy", numpy.__version__, numpy.__file__)
print("scipy", scipy.__version__, scipy.__file__)
print("sklearn", sklearn.__version__, sklearn.__file__)
print("OpenEXR", OpenEXR.__version__, OpenEXR.__file__)
print("cv2", cv2.__version__, cv2.__file__)
print("torch", torch.__version__)
print("kaolin", kaolin.__version__)
print("cKDTree import: OK")
PY

test -x "$OIIO_ENV/bin/oiiotool"
test -x "$OIIO_ENV/bin/exrheader"

echo "Repaired Python environment: $BEDLAM_PYTHON_ENV"
echo "OpenImageIO tool environment: $OIIO_ENV"
