# Double-Blind Annotation Authorization System

## Overview

This setup implements a **double-blind annotation access control system** for OHIF + Orthanc secured by Keycloak. The system ensures that:

1. **AnnotatorA** can only see:
   - Studies assigned to them (labeled with project labels like `proj-x`)
   - Their own annotations (labeled with `ann-teamA`)

2. **AnnotatorB** can only see:
   - Studies assigned to them (labeled with project labels like `proj-x`)
   - Their own annotations (labeled with `ann-teamB`)

3. **Senior reviewers** can see:
   - All studies
   - All annotations from both teams

4. **Annotations are automatically labeled** when uploaded based on the uploader's group membership

## Architecture

```
┌─────────┐     ┌───────┐     ┌────────────┐     ┌─────────┐     ┌─────────────┐
│ Browser │────▶│ Nginx │────▶│ oauth2proxy│────▶│ Orthanc │────▶│ Auth Service│
└─────────┘     └───────┘     └────────────┘     └─────────┘     └─────────────┘
                     │              │                   │
                     │              │                   └─▶ Authorization Plugin
                     │              │
                     │              └─▶ X-Remote-User: annotatorA
                     │                  X-Forwarded-Groups: annotatorA
                     │
                     └─▶ Keycloak (Identity)
```

### Components

1. **Keycloak**: Identity provider with groups (`annotatorA`, `annotatorB`, `senior`)
2. **oauth2-proxy**: Authenticates users and adds identity headers
3. **Nginx**: Forwards identity headers to Orthanc
4. **Orthanc Authorization Plugin**: Intercepts requests and calls auth service
5. **Auth Service**: Makes authorization decisions based on labels and groups
6. **Python Plugin**: Auto-labels annotations on upload

## User Accounts

| Username    | Password    | Groups      | Access                                    |
|-------------|-------------|-------------|-------------------------------------------|
| annotatorA  | annotatorA  | annotatorA  | Assigned studies + own annotations        |
| annotatorB  | annotatorB  | annotatorB  | Assigned studies + own annotations        |
| annotatorC  | annotatorC  | annotatorC  | Assigned studies + own annotations        |
| senior      | senior      | senior      | All studies + all annotations             |
| pacsadmin   | pacsadmin   | pacsadmin   | Full admin access (Orthanc UI)            |
| viewer      | viewer      | (none)      | Basic read access                         |

## Label System

### Study Labels (Project Assignment)
- `proj-x`, `proj-y`, etc.: Assigned to studies to indicate which project they belong to
- Annotators can access studies labeled with their assigned projects

### Annotation Labels (Team Segregation)
- `ann-teamA`: Annotations created by AnnotatorA (automatically applied)
- `ann-teamB`: Annotations created by AnnotatorB (automatically applied)
- `ann-teamC`: Annotations created by AnnotatorC (automatically applied)
- `senior-annotation`: Annotations created by senior reviewers (visible to all)

### SOPClassUIDs Considered Annotations
- **Segmentation**: `1.2.840.10008.5.1.4.1.1.66.4`
- **Structured Reports (SR)**: Multiple UIDs including Basic Text SR, Enhanced SR, Comprehensive SR, etc.

## Setup and Deployment

### 1. Start the System

```bash
cd /path/to/OHIF_Viewer/platform/app/.recipes/Nginx-Orthanc-Keycloak

# Build and start all services
docker-compose down && docker-compose up --build -d

# Check all services are healthy
docker-compose ps
```

### 2. Verify Services

```bash
# Check Keycloak is running
curl http://localhost/keycloak/

# Check Orthanc is running
docker logs ohif_orthanc_kc | tail -20

# Check auth service is running
docker logs ohif_auth_service_kc | tail -20
```

### 3. Access the System

- **OHIF Viewer**: http://localhost/ or https://localhost/
- **Keycloak Admin**: http://localhost/keycloak/ (admin/admin)
- **Orthanc Admin**: http://localhost/pacs-admin/ (pacsadmin only)

## Usage Workflow

### Step 1: Upload Studies (As Admin)

1. Login as `pacsadmin`
2. Upload DICOM studies to Orthanc via:
   - Orthanc Admin UI: http://localhost/pacs-admin/
   - DICOM C-STORE
   - DICOMweb STOW-RS

3. Label studies with project assignments:

```bash
# Assign study to both teams (using Orthanc REST API)
STUDY_ID="orthanc-study-id"

curl -X PUT http://localhost/pacs-admin/studies/$STUDY_ID/labels/proj-x \
  -u pacsadmin:pacsadmin
```

### Step 2: Annotate Studies (As Annotator)

1. Login as `annotatorA` (password: `annotatorA`)
2. Browse OHIF Viewer: http://localhost/
3. Open an assigned study
4. Create annotations using OHIF tools (segmentation, measurements, etc.)
5. Save annotations
6. **Annotations are automatically labeled with `ann-teamA`**

### Step 3: Review Annotations (As Senior)

1. Login as `senior` (password: `senior`)
2. Browse OHIF Viewer
3. View ALL studies and ALL annotations from both teams
4. Compare annotations side-by-side

## Authorization Rules

### Implemented in `auth_service.py`

```python
# Senior and Admin: Full access
if 'senior' in groups or 'pacsadmin' in groups:
    return True

# Annotators: Limited access
if 'annotatorA' in groups:
    # Can read studies labeled with proj-x
    # Can read/write annotations labeled with ann-teamA
    # CANNOT see annotations labeled with ann-teamB

if 'annotatorB' in groups:
    # Can read studies labeled with proj-x
    # Can read/write annotations labeled with ann-teamB
    # CANNOT see annotations labeled with ann-teamA
```

## Manual Label Management

### View Labels on a Study

```bash
STUDY_ID="orthanc-study-id"
curl http://localhost/pacs-admin/studies/$STUDY_ID/labels
```

### Add Label to Study

```bash
STUDY_ID="orthanc-study-id"
curl -X PUT http://localhost/pacs-admin/studies/$STUDY_ID/labels/proj-x
```

### Remove Label from Study

```bash
STUDY_ID="orthanc-study-id"
curl -X DELETE http://localhost/pacs-admin/studies/$STUDY_ID/labels/proj-x
```

### Label a Series (For Annotations)

```bash
SERIES_ID="orthanc-series-id"
curl -X PUT http://localhost/pacs-admin/series/$SERIES_ID/labels/ann-teamA
```

## Troubleshooting

### Check Authorization Service Logs

```bash
docker logs -f ohif_auth_service_kc
```

You should see authorization requests like:
```
Authorization request: {'username': 'annotatorA', 'groups': ['annotatorA'], ...}
✓ Annotation access granted: ann-teamA in labels
```

### Check Orthanc Authorization Plugin

```bash
docker logs -f ohif_orthanc_kc | grep Authorization
```

### Check Python Plugin is Running

```bash
docker logs -f ohif_orthanc_kc | grep AnnotationLabeler
```

You should see:
```
[AnnotationLabeler] Annotation labeler plugin initialized
[AnnotationLabeler] Processing instance: xxx
[AnnotationLabeler] Detected annotation (SEG or SR)
```

### Test Authorization Manually

```bash
# Test as annotatorA
curl -H "X-Remote-User: annotatorA" \
     -H "X-Forwarded-Groups: annotatorA" \
     http://localhost/pacs/studies

# Should only see studies/annotations accessible to annotatorA
```

### Common Issues

**Issue**: Annotations not being auto-labeled

**Solution**:
1. Check Python plugin logs
2. Verify `/etc/orthanc/python/annotation_labeler.py` is mounted correctly
3. Check `PythonScript` is configured in orthanc.json

---

**Issue**: Authorization service returns "granted: false" for valid requests

**Solution**:
1. Check auth service logs for the exact reason
2. Verify labels are correctly applied to studies/series
3. Check that nginx is forwarding `X-Remote-User` and `X-Forwarded-Groups` headers

---

**Issue**: All requests return 403 Forbidden

**Solution**:
1. Verify auth service is running: `docker ps | grep auth_service`
2. Check orthanc can reach auth service: `docker exec ohif_orthanc_kc ping auth-service`
3. Check Authorization plugin configuration in orthanc.json

## Advanced: Customizing Authorization Rules

Edit `auth-service/auth_service.py`:

```python
def check_authorization(username, groups, method, level, orthanc_id, labels, uri):
    # Add custom rules here

    # Example: Allow annotatorA to see annotatorB's annotations on Fridays
    import datetime
    if datetime.datetime.now().weekday() == 4:  # Friday
        if 'annotatorA' in groups and 'ann-teamB' in labels:
            return True

    # ... rest of authorization logic
```

Rebuild and restart:
```bash
docker-compose build auth_service
docker-compose up -d auth_service
```

## Security Considerations

1. **Change Default Passwords**: All demo passwords should be changed in production
2. **HTTPS**: Enable HTTPS for production (already configured)
3. **Cookie Secrets**: Generate new oauth2-proxy cookie secret
4. **Keycloak Secrets**: Rotate client secrets regularly
5. **Audit Logs**: Enable Orthanc audit logs to track access

## Performance

- **Authorization Cache**: Decisions are cached for 10 minutes (`validity: 600`)
- **Label Queries**: Labels are indexed in Orthanc for fast lookups
- **Concurrent Requests**: Auth service runs with 2 Gunicorn workers

## Multi-Team Study Assignment

**NEW**: The system now supports unlimited teams with flexible study assignments!

See **[MULTI-TEAM-GUIDE.md](MULTI-TEAM-GUIDE.md)** for:
- ✅ How to assign different studies to different teams
- ✅ Scenarios: shared studies vs. separate studies
- ✅ Adding more teams (D, E, F, etc.)
- ✅ Dynamic project-based assignments
- ✅ Bulk labeling operations

### Quick Example: Team C with Different Studies

```bash
# Team A and B work on cardiac studies
curl -X PUT http://localhost/pacs-admin/studies/$CARDIAC_STUDY/labels/proj-cardiac

# Team C works on brain studies
curl -X PUT http://localhost/pacs-admin/studies/$BRAIN_STUDY/labels/proj-brain
```

Then customize `auth_service.py` to enforce team-to-project mappings.

## Next Steps

1. **Test the workflow end-to-end**
2. **Read MULTI-TEAM-GUIDE.md** for advanced configurations
3. **Adjust authorization rules** in `auth_service.py` as needed
4. **Create project labels** for study assignments
5. **Set up audit logging** for compliance
6. **Configure backup** for Orthanc database
