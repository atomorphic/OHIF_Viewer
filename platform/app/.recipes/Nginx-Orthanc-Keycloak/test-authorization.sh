#!/bin/bash
#
# Test script for double-blind annotation authorization
#

set -e

echo "========================================="
echo "Testing Double-Blind Authorization Setup"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost"

# Test functions
test_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
}

test_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    exit 1
}

test_info() {
    echo -e "${YELLOW}ℹ INFO:${NC} $1"
}

echo "1. Testing Service Health..."
echo "----------------------------"

# Check auth service
if curl -s -f "$BASE_URL:8000/health" > /dev/null 2>&1; then
    test_pass "Auth service is healthy"
else
    test_fail "Auth service is not responding"
fi

# Check Orthanc
if curl -s -f "$BASE_URL/pacs/" > /dev/null 2>&1 || curl -s "$BASE_URL/pacs/" | grep -q "401"; then
    test_pass "Orthanc is responding"
else
    test_fail "Orthanc is not responding"
fi

# Check Keycloak
if curl -s -f "$BASE_URL/keycloak/" > /dev/null 2>&1; then
    test_pass "Keycloak is responding"
else
    test_fail "Keycloak is not responding"
fi

echo ""
echo "2. Testing User Authentication..."
echo "----------------------------"

# Test annotatorA login
test_info "Testing annotatorA can access OHIF..."
if curl -s -u annotatorA:annotatorA "$BASE_URL/ohif-viewer/" | grep -q "OHIF"; then
    test_pass "AnnotatorA can authenticate"
else
    test_info "AnnotatorA authentication requires browser session (oauth2-proxy)"
fi

echo ""
echo "3. Checking Docker Services..."
echo "----------------------------"

services=("ohif_webapp_orthanc_kc" "ohif_orthanc_kc" "ohif_keycloak_kc" "ohif_auth_service_kc" "ohif_postgres_kc")

for service in "${services[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
        test_pass "Service $service is running"
    else
        test_fail "Service $service is not running"
    fi
done

echo ""
echo "4. Checking Orthanc Configuration..."
echo "----------------------------"

# Check if Authorization plugin is loaded
if docker logs ohif_orthanc_kc 2>&1 | grep -q "Authorization"; then
    test_pass "Orthanc Authorization plugin is loaded"
else
    test_info "Authorization plugin may not be loaded (check docker logs ohif_orthanc_kc)"
fi

# Check if Python plugin is loaded
if docker logs ohif_orthanc_kc 2>&1 | grep -q "Python"; then
    test_pass "Orthanc Python plugin is loaded"
else
    test_info "Python plugin may not be loaded (check docker logs ohif_orthanc_kc)"
fi

echo ""
echo "5. Checking Keycloak Groups..."
echo "----------------------------"

test_info "To verify groups, login to Keycloak admin console:"
test_info "  URL: $BASE_URL/keycloak/"
test_info "  User: admin / Password: admin"
test_info "  Go to: ohif realm -> Groups"
test_info "  Expected groups: annotatorA, annotatorB, senior, pacsadmin"

echo ""
echo "6. Manual Testing Instructions..."
echo "----------------------------"
echo ""
echo "To fully test the authorization system:"
echo ""
echo "A. Upload a test study:"
echo "   1. Login as pacsadmin (http://localhost/pacs-admin/)"
echo "   2. Upload DICOM files"
echo "   3. Note the Study ID"
echo ""
echo "B. Label the study:"
echo "   STUDY_ID=<your-study-id>"
echo "   curl -X PUT http://localhost/pacs-admin/studies/\$STUDY_ID/labels/proj-x"
echo ""
echo "C. Test as AnnotatorA:"
echo "   1. Login as annotatorA (http://localhost/)"
echo "   2. Verify you can see the study"
echo "   3. Create an annotation (segmentation)"
echo "   4. Check it's labeled: docker logs ohif_orthanc_kc | grep 'ann-teamA'"
echo ""
echo "D. Test as AnnotatorB:"
echo "   1. Login as annotatorB"
echo "   2. Verify you can see the study"
echo "   3. Verify you CANNOT see AnnotatorA's annotations"
echo "   4. Create your own annotation"
echo ""
echo "E. Test as Senior:"
echo "   1. Login as senior"
echo "   2. Verify you can see BOTH annotations from teamA and teamB"
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "${GREEN}Basic health checks passed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review logs: docker-compose logs -f"
echo "  2. Follow manual testing instructions above"
echo "  3. Check AUTHORIZATION.md for detailed documentation"
echo ""
