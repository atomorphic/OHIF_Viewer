# Multi-Team Study Assignment Guide

## Overview

This guide explains how to assign different studies to different annotator teams using the label-based authorization system.

## Concept: Labels for Access Control

The system uses **two types of labels**:

1. **Project Labels** (Study Assignment)
   - Applied to studies to indicate which teams can access them
   - Examples: `proj-x`, `proj-y`, `proj-z`, `study-cohort-1`, etc.
   - **Teams share access to studies with these labels**

2. **Annotation Labels** (Team Segregation)
   - Automatically applied to annotations (SEG/SR) based on uploader's team
   - `ann-teamA` - AnnotatorA's annotations
   - `ann-teamB` - AnnotatorB's annotations
   - `ann-teamC` - AnnotatorC's annotations
   - **Teams CANNOT see each other's annotations**

## User Accounts

| Username    | Password    | Groups      | Can See Studies Labeled With | Can See Annotations |
|-------------|-------------|-------------|------------------------------|---------------------|
| annotatorA  | annotatorA  | annotatorA  | Any project label            | Only ann-teamA      |
| annotatorB  | annotatorB  | annotatorB  | Any project label            | Only ann-teamB      |
| annotatorC  | annotatorC  | annotatorC  | Any project label            | Only ann-teamC      |
| senior      | senior      | senior      | All studies                  | All annotations     |
| pacsadmin   | pacsadmin   | pacsadmin   | All studies                  | All annotations     |

## Scenario 1: All Teams Working on Same Studies

**Use Case**: You want all three teams (A, B, C) to annotate the same studies independently (true double/triple-blind).

### Setup

1. Upload studies as `pacsadmin`
2. Label all studies with a common project label:

```bash
# Label Study 1
curl -X PUT http://localhost/pacs-admin/studies/STUDY_ID_1/labels/proj-common

# Label Study 2
curl -X PUT http://localhost/pacs-admin/studies/STUDY_ID_2/labels/proj-common
```

### Result

- ✅ All three teams can see ALL studies
- ✅ Team A creates annotations → auto-labeled with `ann-teamA`
- ✅ Team B creates annotations → auto-labeled with `ann-teamB`
- ✅ Team C creates annotations → auto-labeled with `ann-teamC`
- ❌ Teams CANNOT see each other's annotations
- ✅ Senior can see all annotations for comparison

## Scenario 2: Different Teams Working on Different Studies

**Use Case**: Team A works on cardiac studies, Team B on lung studies, Team C on brain studies.

### Setup

1. Upload studies as `pacsadmin`
2. Label studies based on team assignment:

```bash
# Cardiac studies for Team A
curl -X PUT http://localhost/pacs-admin/studies/CARDIAC_STUDY_1/labels/proj-cardiac
curl -X PUT http://localhost/pacs-admin/studies/CARDIAC_STUDY_2/labels/proj-cardiac

# Lung studies for Team B
curl -X PUT http://localhost/pacs-admin/studies/LUNG_STUDY_1/labels/proj-lung
curl -X PUT http://localhost/pacs-admin/studies/LUNG_STUDY_2/labels/proj-lung

# Brain studies for Team C
curl -X PUT http://localhost/pacs-admin/studies/BRAIN_STUDY_1/labels/proj-brain
curl -X PUT http://localhost/pacs-admin/studies/BRAIN_STUDY_2/labels/proj-brain
```

3. **Update Authorization Service** to enforce project-based access:

Edit `auth-service/auth_service.py` in the `check_authorization` function:

```python
def check_authorization(username, groups, method, level, orthanc_id, labels, uri):
    # ... existing admin/senior checks ...

    # Define team-to-project mapping
    team_projects = {
        'annotatorA': ['proj-cardiac'],
        'annotatorB': ['proj-lung'],
        'annotatorC': ['proj-brain']
    }

    # Determine which team this user belongs to
    team_label = None
    allowed_projects = []
    if 'annotatorA' in groups:
        team_label = 'ann-teamA'
        allowed_projects = team_projects['annotatorA']
    elif 'annotatorB' in groups:
        team_label = 'ann-teamB'
        allowed_projects = team_projects['annotatorB']
    elif 'annotatorC' in groups:
        team_label = 'ann-teamC'
        allowed_projects = team_projects['annotatorC']

    # For DICOM instances (studies/series/instances)
    if level in ['study', 'series', 'instance']:
        # Check if this is an annotation
        if 'ann-teamA' in labels or 'ann-teamB' in labels or 'ann-teamC' in labels:
            if team_label in labels:
                return True
            else:
                return False

        # Check if study is assigned to this team
        for project in allowed_projects:
            if project in labels:
                logger.info(f"✓ Study access granted: {project} in labels")
                return True

        logger.info(f"✗ Study not assigned to team: {allowed_projects} not in {labels}")
        return False

    # Default deny
    return False
```

### Result

- ✅ Team A can ONLY see cardiac studies
- ✅ Team B can ONLY see lung studies
- ✅ Team C can ONLY see brain studies
- ❌ Teams CANNOT see each other's studies OR annotations
- ✅ Senior can see ALL studies and annotations

## Scenario 3: Overlapping Study Access with Blind Annotations

**Use Case**: Teams A and B both annotate cardiac studies, Team C works on brain studies.

### Setup

```bash
# Cardiac studies - accessible by Team A and B
curl -X PUT http://localhost/pacs-admin/studies/CARDIAC_1/labels/proj-cardiac

# Brain studies - accessible by Team C only
curl -X PUT http://localhost/pacs-admin/studies/BRAIN_1/labels/proj-brain
```

Update authorization service:

```python
team_projects = {
    'annotatorA': ['proj-cardiac'],       # A sees cardiac
    'annotatorB': ['proj-cardiac'],       # B sees cardiac
    'annotatorC': ['proj-brain']          # C sees brain
}
```

### Result

- ✅ Team A and B can BOTH see cardiac studies
- ✅ Team A creates annotations → labeled `ann-teamA`
- ✅ Team B creates annotations → labeled `ann-teamB`
- ❌ Team A CANNOT see Team B's annotations on same study
- ❌ Team B CANNOT see Team A's annotations on same study
- ✅ Team C can ONLY see brain studies
- ✅ Senior sees everything

## Scenario 4: Dynamic Project-Based Assignment

**Use Case**: Projects are assigned dynamically by study metadata (e.g., based on study description or custom tags).

### Advanced Setup

You can modify the authorization service to check study metadata:

```python
def check_authorization(username, groups, method, level, orthanc_id, labels, uri):
    # Get study metadata
    try:
        study_info = requests.get(f"http://orthanc:8042/studies/{orthanc_id}/simplified-tags").json()
        study_description = study_info.get('StudyDescription', '')

        # Dynamic assignment based on study description
        if 'annotatorA' in groups and 'CARDIAC' in study_description.upper():
            return True
        if 'annotatorB' in groups and 'LUNG' in study_description.upper():
            return True
        if 'annotatorC' in groups and 'BRAIN' in study_description.upper():
            return True
    except:
        pass

    # Fall back to label-based checks
    # ... rest of authorization logic
```

## Managing Labels

### List All Labels in Orthanc

```bash
# Get all labels across the system
curl http://localhost/pacs-admin/tools/labels
```

### View Labels on Specific Study

```bash
STUDY_ID="orthanc-study-id"
curl http://localhost/pacs-admin/studies/$STUDY_ID/labels
```

### Add Label to Study

```bash
curl -X PUT http://localhost/pacs-admin/studies/$STUDY_ID/labels/proj-newproject
```

### Remove Label from Study

```bash
curl -X DELETE http://localhost/pacs-admin/studies/$STUDY_ID/labels/proj-oldproject
```

### Bulk Label Studies

```bash
#!/bin/bash
# Label multiple studies at once

STUDIES=("study-id-1" "study-id-2" "study-id-3")
LABEL="proj-cardiac"

for study in "${STUDIES[@]}"; do
    echo "Labeling $study with $label..."
    curl -X PUT "http://localhost/pacs-admin/studies/$study/labels/$LABEL"
done
```

## Testing Different Configurations

### Test Script

```bash
#!/bin/bash
# test-team-access.sh

echo "Testing Team A access to cardiac study..."
curl -H "X-Remote-User: annotatorA" \
     -H "X-Forwarded-Groups: annotatorA" \
     http://localhost/pacs/studies/CARDIAC_STUDY_ID

echo "Testing Team B access to cardiac study (should work)..."
curl -H "X-Remote-User: annotatorB" \
     -H "X-Forwarded-Groups: annotatorB" \
     http://localhost/pacs/studies/CARDIAC_STUDY_ID

echo "Testing Team C access to cardiac study (should fail)..."
curl -H "X-Remote-User: annotatorC" \
     -H "X-Forwarded-Groups: annotatorC" \
     http://localhost/pacs/studies/CARDIAC_STUDY_ID
```

## Adding More Teams

To add a new team (e.g., AnnotatorD):

1. **Add group to Keycloak** (edit `config/ohif-keycloak-realm.json`):
```json
{
  "id": "unique-uuid",
  "name": "annotatorD",
  "path": "/annotatorD",
  "subGroups": [],
  "attributes": {},
  "realmRoles": [],
  "clientRoles": {}
}
```

2. **Add user account**:
```json
{
  "username": "annotatorD",
  "enabled": true,
  "emailVerified": true,
  "firstName": "Annotator",
  "lastName": "D",
  "email": "annotatorD@mail.com",
  "credentials": [{"type": "password", "value": "annotatorD"}],
  "groups": ["annotatorD"]
}
```

3. **Update authorization service** (`auth-service/auth_service.py`):
```python
# Add to team_label mapping
elif 'annotatorD' in groups:
    team_label = 'ann-teamD'

# Add to annotation check
if 'ann-teamA' in labels or 'ann-teamB' in labels or 'ann-teamC' in labels or 'ann-teamD' in labels:
```

4. **Update Python plugin** (`orthanc-python/annotation_labeler.py`):
```python
label_map = {
    'annotatorA': 'ann-teamA',
    'annotatorB': 'ann-teamB',
    'annotatorC': 'ann-teamC',
    'annotatorD': 'ann-teamD',  # Add this
    'senior': 'senior-annotation'
}
```

5. **Rebuild and restart**:
```bash
docker-compose down
docker-compose up --build -d
```

## Best Practices

1. **Consistent Naming**: Use a clear naming convention for project labels (e.g., `proj-cardiac`, `proj-lung`)
2. **Document Assignments**: Keep a spreadsheet mapping studies to projects/teams
3. **Test Before Production**: Always test authorization rules with curl before deploying
4. **Monitor Logs**: Check auth service logs to verify access patterns
5. **Backup Labels**: Export label assignments before major changes

## Troubleshooting

**Issue**: Team can't see assigned studies

**Solution**:
1. Verify study has correct project label: `curl http://localhost/pacs-admin/studies/$ID/labels`
2. Check authorization service logs: `docker logs ohif_auth_service_kc`
3. Verify user is in correct group in Keycloak

**Issue**: Team can see other team's annotations

**Solution**:
1. Check annotation labels: `curl http://localhost/pacs-admin/series/$SERIES_ID/labels`
2. Verify Python plugin is running: `docker logs ohif_orthanc_kc | grep AnnotationLabeler`
3. Check annotation SOPClassUID is recognized as SEG/SR

## Summary

The label-based system is **flexible and powerful**:

- ✅ Support unlimited number of teams
- ✅ Assign studies to single or multiple teams
- ✅ Automatically segregate annotations by team
- ✅ Senior reviewers see everything
- ✅ Easy to add new projects/teams
- ✅ No code changes needed for new study assignments (just add labels)

For questions or advanced configurations, see [AUTHORIZATION.md](AUTHORIZATION.md).
