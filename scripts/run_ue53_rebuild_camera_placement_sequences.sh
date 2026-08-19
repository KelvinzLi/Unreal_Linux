#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -ne 1 ]]; then
    echo "Usage: $0 {antiquity|gothic|outpost|space|spaceship|street|train|warehouse}" >&2
    exit 2
fi

SCENE="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/load_config.sh"
load_bedlam_config
PROJECT_ROOT="${BEDLAM_PROJECT_ROOT:-}"
DATASET_ROOT="${BEDLAM_DATASET_ROOT:-}"
require_bedlam_setting PROJECT_ROOT
require_bedlam_setting DATASET_ROOT
require_bedlam_setting UE_ROOT

case "$SCENE" in
    antiquity) PROJECT_NAME="Antiquity3D"; UPROJECT="Antiquity3D"; MAP="/Game/Antiquity3D/Maps/Antiquity3D_City_Day_Dynamic"; MAP_REL="Antiquity3D/Maps/Antiquity3D_City_Day_Dynamic.umap" ;;
    gothic) PROJECT_NAME="BE_IBL"; UPROJECT="BE_IBL"; MAP="/Game/ModularGothicFantasyEnvironment/Maps/DemoMapDay"; MAP_REL="ModularGothicFantasyEnvironment/Maps/DemoMapDay.umap" ;;
    outpost) PROJECT_NAME="SciFiModularOutpost"; UPROJECT="SciFiModularOutpost"; MAP="/Game/SciFiModularOutpost/Maps/ShowCase"; MAP_REL="SciFiModularOutpost/Maps/ShowCase.umap" ;;
    space) PROJECT_NAME="BE_IBL_2"; UPROJECT="BE_IBL_2"; MAP="/Game/SpaceColonies/Maps/OtherPlanetsDemoMap"; MAP_REL="SpaceColonies/Maps/OtherPlanetsDemoMap.umap" ;;
    spaceship) PROJECT_NAME="SYN4D_BigOffice"; UPROJECT="BigOffice"; MAP="/Game/SpaceshipInterior/Maps/Demonstration"; MAP_REL="SpaceshipInterior/Maps/Demonstration.umap" ;;
    street) PROJECT_NAME="VictorianStreet"; UPROJECT="VictorianStreet"; MAP="/Game/VictorianStreet/Maps/Showcase"; MAP_REL="VictorianStreet/Maps/Showcase.umap" ;;
    train) PROJECT_NAME="BE_IBL_3"; UPROJECT="BE_IBL_3"; MAP="/Game/TrainStation/Maps/Demonstration"; MAP_REL="TrainStation/Maps/Demonstration.umap" ;;
    warehouse) PROJECT_NAME="BE_IBL_3"; UPROJECT="BE_IBL_3"; MAP="/Game/WareHouse/Maps/Demo"; MAP_REL="WareHouse/Maps/Demo.umap" ;;
    *) echo "ERROR: Unknown scene: $SCENE" >&2; exit 2 ;;
esac

PROJECT_DIR="$PROJECT_ROOT/$PROJECT_NAME"
PROJECT="$PROJECT_DIR/$UPROJECT.uproject"
MAP_FILE="$PROJECT_DIR/Content/$MAP_REL"
DATASET_DIR="$DATASET_ROOT/$SCENE"
CSV="$DATASET_DIR/be_seq.csv"
CAMERAS="$DATASET_DIR/be_camera_animations.json"
ASSET_STORE="$DATASET_DIR/unreal_assets"

test -f "$PROJECT"
test -f "$MAP_FILE"
test -f "$CSV"
test -f "$CAMERAS"

PROJECT="$PROJECT" \
MAP="$MAP" \
MAP_FILE="$MAP_FILE" \
BEDLAM_LEVEL_SEQUENCE_CSV_PATH="$CSV" \
BEDLAM_LEVEL_SEQUENCE_STATUS_DIR="$DATASET_DIR" \
BEDLAM_LEVEL_SEQUENCE_CAMERA_TYPE="Default" \
BEDLAM_LEVEL_SEQUENCE_EXPORT_GEOMETRY_CACHE_OBJ="0" \
BEDLAM_GENERATED_ASSET_STORE="$ASSET_STORE" \
"$SCRIPT_DIR/run_ue53_create_level_sequences.sh"
