#!/usr/bin/env bash

# Source this file after defining REPO_ROOT. BEDLAM_CONFIG can select any
# configuration file; otherwise config/local.sh is loaded when it exists.
load_bedlam_config() {
    local config_path="${BEDLAM_CONFIG:-$REPO_ROOT/config/local.sh}"

    if [[ -n "${BEDLAM_CONFIG:-}" && ! -f "$config_path" ]]; then
        echo "ERROR: BEDLAM_CONFIG does not exist: $config_path" >&2
        return 1
    fi
    if [[ -f "$config_path" ]]; then
        # shellcheck source=/dev/null
        source "$config_path"
    fi
}

require_bedlam_setting() {
    local name=$1
    local value=${!name:-}
    if [[ -z "$value" ]]; then
        echo "ERROR: $name is required. Set it in config/local.sh, export it," >&2
        echo "       or provide the corresponding command-line option." >&2
        return 2
    fi
}
