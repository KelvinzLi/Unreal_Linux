#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -ne 1 ]]; then
    echo "Usage: $0 {antiquity|gothic|outpost|space|spaceship|street|train|warehouse}" >&2
    exit 2
fi

SCENE="$1"
PROJECT_ROOT="/scratch/shared/beegfs/kelvin/apps/UnrealProjects"
DATASET_ROOT="/scratch/shared/beegfs/kelvin/Syn4D/subsets/ablations/camera_placement/mixed_no_sim_no_motion"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$SCENE" in
    antiquity)
        PROJECT="$PROJECT_ROOT/Antiquity3D/Antiquity3D.uproject"
        MAP="/Game/Antiquity3D/Maps/Antiquity3D_City_Day_Dynamic"
        MAP_FILE="$PROJECT_ROOT/Antiquity3D/Content/Antiquity3D/Maps/Antiquity3D_City_Day_Dynamic.umap"
        ;;
    gothic)
        PROJECT="$PROJECT_ROOT/BE_IBL/BE_IBL.uproject"
        MAP="/Game/ModularGothicFantasyEnvironment/Maps/DemoMapDay"
        MAP_FILE="$PROJECT_ROOT/BE_IBL/Content/ModularGothicFantasyEnvironment/Maps/DemoMapDay.umap"
        ;;
    outpost)
        PROJECT="$PROJECT_ROOT/SciFiModularOutpost/SciFiModularOutpost.uproject"
        MAP="/Game/SciFiModularOutpost/Maps/ShowCase"
        MAP_FILE="$PROJECT_ROOT/SciFiModularOutpost/Content/SciFiModularOutpost/Maps/ShowCase.umap"
        ;;
    space)
        PROJECT="$PROJECT_ROOT/Antiquity3D/Antiquity3D.uproject"
        MAP="/Game/SpaceColonies/Maps/OtherPlanetsDemoMap"
        MAP_FILE="$PROJECT_ROOT/Antiquity3D/Content/SpaceColonies/Maps/OtherPlanetsDemoMap.umap"
        ;;
    spaceship)
        PROJECT="$PROJECT_ROOT/SYN4D_BigOffice/BigOffice.uproject"
        MAP="/Game/SpaceshipInterior/Maps/Demonstration"
        MAP_FILE="$PROJECT_ROOT/SYN4D_BigOffice/Content/SpaceshipInterior/Maps/Demonstration.umap"
        ;;
    street)
        PROJECT="$PROJECT_ROOT/VictorianStreet/VictorianStreet.uproject"
        MAP="/Game/VictorianStreet/Maps/Showcase"
        MAP_FILE="$PROJECT_ROOT/VictorianStreet/Content/VictorianStreet/Maps/Showcase.umap"
        ;;
    train)
        PROJECT="$PROJECT_ROOT/BE_IBL_3/BE_IBL_3.uproject"
        MAP="/Game/TrainStation/Maps/Demonstration"
        MAP_FILE="$PROJECT_ROOT/BE_IBL_3/Content/TrainStation/Maps/Demonstration.umap"
        ;;
    warehouse)
        PROJECT="$PROJECT_ROOT/BE_IBL_3/BE_IBL_3.uproject"
        MAP="/Game/WareHouse/Maps/Demo"
        MAP_FILE="$PROJECT_ROOT/BE_IBL_3/Content/WareHouse/Maps/Demo.umap"
        ;;
    *)
        echo "ERROR: Unknown scene: $SCENE" >&2
        exit 2
        ;;
esac

DATASET_DIR="$DATASET_ROOT/$SCENE"
INPUT_CSV="$DATASET_DIR/be_seq_base.csv"
ASSET_STORE="$DATASET_DIR/unreal_assets"

test -f "$PROJECT"
test -f "$MAP_FILE"
test -f "$INPUT_CSV"

echo "Running single-session base-CSV-to-MRQ workflow for $SCENE"
"$SCRIPT_DIR/run_ue53_camera_placement_to_mrq_workflow.sh" \
    --project "$PROJECT" \
    --map "$MAP" \
    --map-file "$MAP_FILE" \
    --base-csv "$INPUT_CSV" \
    --output "$DATASET_DIR" \
    --asset-store "$ASSET_STORE"

echo "Camera-placement MRQ preparation complete for $SCENE"
echo "Final CSV:    $DATASET_DIR/be_seq.csv"
echo "Camera JSON:  $DATASET_DIR/be_camera_animations.json"
echo "Asset store:  $ASSET_STORE"
