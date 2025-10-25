#!/bin/bash
#
# Interactive Study Labeling Tool
# Makes it easy to label studies in Orthanc
#

set -e

ORTHANC_URL="http://localhost/pacs-admin"
AUTH="pacsadmin:pacsadmin"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "   Orthanc Study Labeling Tool"
echo "========================================="
echo ""

# Function to list all studies
list_studies() {
    echo -e "${BLUE}Fetching studies from Orthanc...${NC}"
    STUDIES=$(curl -s -u "$AUTH" "$ORTHANC_URL/studies")

    if [ -z "$STUDIES" ] || [ "$STUDIES" == "[]" ]; then
        echo -e "${RED}No studies found in Orthanc${NC}"
        exit 1
    fi

    STUDY_IDS=($(echo "$STUDIES" | jq -r '.[]'))

    echo -e "${GREEN}Found ${#STUDY_IDS[@]} studies:${NC}"
    echo ""

    for i in "${!STUDY_IDS[@]}"; do
        STUDY_ID="${STUDY_IDS[$i]}"
        STUDY_INFO=$(curl -s -u "$AUTH" "$ORTHANC_URL/studies/$STUDY_ID/simplified-tags")
        PATIENT_NAME=$(echo "$STUDY_INFO" | jq -r '.PatientName // "Unknown"')
        STUDY_DESC=$(echo "$STUDY_INFO" | jq -r '.StudyDescription // "Unknown"')
        STUDY_DATE=$(echo "$STUDY_INFO" | jq -r '.StudyDate // "Unknown"')

        # Get existing labels
        LABELS=$(curl -s -u "$AUTH" "$ORTHANC_URL/studies/$STUDY_ID/labels")
        LABELS_STR=$(echo "$LABELS" | jq -r 'join(", ")')

        echo -e "${YELLOW}[$i]${NC} Patient: $PATIENT_NAME | Study: $STUDY_DESC | Date: $STUDY_DATE"
        echo "    ID: $STUDY_ID"
        if [ -n "$LABELS_STR" ] && [ "$LABELS_STR" != "" ]; then
            echo -e "    Labels: ${GREEN}$LABELS_STR${NC}"
        else
            echo "    Labels: (none)"
        fi
        echo ""
    done
}

# Function to label a specific study
label_study() {
    local study_index=$1
    local label=$2

    if [ -z "$study_index" ] || [ -z "$label" ]; then
        echo -e "${RED}Usage: label_study <study_index> <label>${NC}"
        return 1
    fi

    STUDY_ID="${STUDY_IDS[$study_index]}"

    echo -e "${BLUE}Adding label '$label' to study $study_index...${NC}"

    RESPONSE=$(curl -s -w "%{http_code}" -u "$AUTH" -X PUT "$ORTHANC_URL/studies/$STUDY_ID/labels/$label")
    HTTP_CODE="${RESPONSE: -3}"

    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ] || [ "$HTTP_CODE" == "204" ]; then
        echo -e "${GREEN}✓ Label '$label' added successfully!${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to add label (HTTP $HTTP_CODE)${NC}"
        return 1
    fi
}

# Function to remove a label
remove_label() {
    local study_index=$1
    local label=$2

    STUDY_ID="${STUDY_IDS[$study_index]}"

    echo -e "${BLUE}Removing label '$label' from study $study_index...${NC}"

    RESPONSE=$(curl -s -w "%{http_code}" -u "$AUTH" -X DELETE "$ORTHANC_URL/studies/$STUDY_ID/labels/$label")
    HTTP_CODE="${RESPONSE: -3}"

    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "204" ]; then
        echo -e "${GREEN}✓ Label '$label' removed successfully!${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to remove label (HTTP $HTTP_CODE)${NC}"
        return 1
    fi
}

# Function to bulk label studies
bulk_label() {
    local label=$1

    echo -e "${YELLOW}Enter study indices to label (space-separated, or 'all'):${NC} "
    read -r indices

    if [ "$indices" == "all" ]; then
        indices=$(seq 0 $((${#STUDY_IDS[@]}-1)))
    fi

    for idx in $indices; do
        label_study "$idx" "$label"
    done

    echo -e "${GREEN}Bulk labeling complete!${NC}"
}

# Main menu
list_studies

echo "========================================="
echo "What would you like to do?"
echo "========================================="
echo "1) Label a single study"
echo "2) Label multiple studies (bulk)"
echo "3) Remove a label from a study"
echo "4) Refresh study list"
echo "5) Exit"
echo ""
echo -n "Enter choice [1-5]: "
read -r choice

case $choice in
    1)
        echo -n "Enter study index: "
        read -r study_idx
        echo -n "Enter label name (e.g., proj-cardiac, proj-teamA): "
        read -r label_name
        label_study "$study_idx" "$label_name"
        ;;
    2)
        echo -n "Enter label name: "
        read -r label_name
        bulk_label "$label_name"
        ;;
    3)
        echo -n "Enter study index: "
        read -r study_idx
        echo -n "Enter label to remove: "
        read -r label_name
        remove_label "$study_idx" "$label_name"
        ;;
    4)
        exec "$0"
        ;;
    5)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Done! Run this script again to label more studies.${NC}"
