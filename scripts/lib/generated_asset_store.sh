#!/usr/bin/env bash

# Make a generated Unreal asset directory visible beneath a project's /Game
# mount without storing the generated .uasset files in the project copy.
ensure_generated_asset_link() {
    local project_path=$1
    local store_path=$2
    local current_target
    local resolved_store

    mkdir -p "$(dirname "$project_path")" "$store_path"
    resolved_store="$(readlink -f "$store_path")"

    if [[ -L "$project_path" ]]; then
        # readlink -f fails for a dangling link. This commonly occurs when an
        # archived generated-asset root is renamed; treat it as a stale target
        # and repoint it instead of aborting a set -e caller.
        current_target="$(readlink -f "$project_path" 2>/dev/null || true)"
        if [[ "$current_target" != "$resolved_store" ]]; then
            ln -sfn "$resolved_store" "$project_path"
        fi
        return
    fi

    if [[ -e "$project_path" ]]; then
        echo "ERROR: Generated asset path is a real project directory: $project_path" >&2
        echo "Move it to $resolved_store, then replace it with a symlink." >&2
        return 1
    fi

    ln -s "$resolved_store" "$project_path"
}
