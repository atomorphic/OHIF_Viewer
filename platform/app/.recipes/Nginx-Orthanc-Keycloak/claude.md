# OHIF Viewer Authentication & Authorization System

## Overview

This document describes the authentication and authorization system implemented for OHIF Viewer with Orthanc PACS. The system provides user-based access control where different users can view different DICOM studies based on their assigned groups.

## Architecture

```
Browser
   |
   v
Login Page (Flask Auth Service)
   |
   v
Nginx (Reverse Proxy + Auth Gateway)
   |
   +-- /login --> Auth Service (JWT cookie)
   +-- /auth/validate --> Auth Service (validates JWT)
   +-- /api/dicom-web/studies --> Auth Service (filters by user group)
   +-- /api/dicom-web/* --> Orthanc (other DICOMweb operations)
   |
   v
OHIF Viewer (React App)
   |
   v
Orthanc PACS (2 studies with labels)
```

## Key Components

### 1. Auth Service (Flask Python)
- **Location**: `auth-service/auth_service.py`
- **Purpose**: Handles authentication and study filtering
- **Key Endpoints**:
  - `GET/POST /login` - Login page and credential validation
  - `GET /auth/validate` - JWT cookie validation (called by nginx auth_request)
  - `GET /filter/studies` - Returns filtered studies based on user's group

### 2. Nginx Configuration
- **Location**: `config/nginx.conf`
- **Key Features**:
  - DNS resolver for Docker hostnames
  - Auth request subrequest pattern
  - Dynamic routing based on authenticated user groups
  - CORS headers for DICOMweb API

### 3. OHIF Configuration
- **Location**: `platform/app/public/config/docker-nginx-orthanc-keycloak.js`
- **Key Change**: Data source URL changed from `/pacs` to `/api/dicom-web`

### 4. Orthanc Study Labels
- **Study 1** (LIDC-IDRI-0001): Labeled `userA-study`
- **Study 2** (LIDC-IDRI-0004): Labeled `userB-study`

## How It Works

### Authentication Flow

1. **User visits `http://localhost/`**
   - Nginx checks for valid JWT cookie via auth_request to `/auth/validate`
   - If no valid cookie → redirect to `/login`

2. **User logs in at `/login`**
   - Auth service validates credentials against user database
   - On success: creates JWT token with username and groups
   - Sets httponly cookie (8 hour expiration)
   - Redirects to OHIF viewer

3. **User accesses OHIF**
   - Nginx validates JWT cookie on every request
   - Allows access to OHIF frontend

### Authorization Flow

1. **OHIF requests studies: `GET /api/dicom-web/studies`**
   - Nginx auth_request validates JWT cookie
   - Extracts user's groups from JWT
   - Forwards to auth service `/filter/studies` with `X-Forwarded-Groups` header

2. **Auth service filters studies**
   - Gets all studies from Orthanc
   - For each study:
     - Looks up Orthanc internal ID from StudyInstanceUID
     - Retrieves study labels
     - Checks if user's group matches study label
   - Returns only authorized studies

3. **OHIF displays filtered studies**
   - UserA sees only studies labeled `userA-study`
   - UserB sees only studies labeled `userB-study`
   - Admin sees all studies

## User Accounts

Configured in `auth-service/auth_service.py`:

```python
USERS = {
    "userA": {"password": "passwordA", "groups": ["annotatorA"]},
    "userB": {"password": "passwordB", "groups": ["annotatorB"]},
    "supervisor": {"password": "supervisor", "groups": ["pacsadmin"]}
}
```

| Username   | Password   | Groups       | Access                          |
|------------|------------|--------------|----------------------------------|
| userA      | passwordA  | annotatorA   | Study 1 (LIDC-IDRI-0001) only   |
| userB      | passwordB  | annotatorB   | Study 2 (LIDC-IDRI-0004) only   |
| supervisor | supervisor | pacsadmin    | All studies                      |

## Testing

### Command Line Testing

```bash
# Test userA
curl -s -c /tmp/cookies_userA.txt -b /tmp/cookies_userA.txt \
  -d "username=userA&password=passwordA" http://localhost/login

curl -s -b /tmp/cookies_userA.txt http://localhost/api/dicom-web/studies \
  | python3 -c "import sys, json; data = json.load(sys.stdin); print(f'UserA sees {len(data)} studies')"
# Output: UserA sees 1 studies

# Test userB
curl -s -c /tmp/cookies_userB.txt -b /tmp/cookies_userB.txt \
  -d "username=userB&password=passwordB" http://localhost/login

curl -s -b /tmp/cookies_userB.txt http://localhost/api/dicom-web/studies \
  | python3 -c "import sys, json; data = json.load(sys.stdin); print(f'UserB sees {len(data)} studies')"
# Output: UserB sees 1 studies

# Test supervisor
curl -s -c /tmp/cookies_supervisor.txt -b /tmp/cookies_supervisor.txt \
  -d "username=supervisor&password=supervisor" http://localhost/login

curl -s -b /tmp/cookies_supervisor.txt http://localhost/api/dicom-web/studies \
  | python3 -c "import sys, json; data = json.load(sys.stdin); print(f'Supervisor sees {len(data)} studies')"
# Output: Supervisor sees 2 studies
```

### Browser Testing

1. **Open `http://localhost/login` in incognito/private window**
2. **Login as userA** (passwordA)
3. **Verify**: Should see only 1 study (LIDC-IDRI-0001)
4. **Logout or open new incognito window**
5. **Login as userB** (passwordB)
6. **Verify**: Should see only 1 study (LIDC-IDRI-0004)

**Important**: Hard refresh (Ctrl+Shift+R / Cmd+Shift+R) after logging in to clear cached configs.

## Key Files Modified

### 1. Auth Service
- **File**: `auth-service/auth_service.py`
- **Changes**:
  - Added JWT-based login system
  - Added `/login` endpoint with HTML form
  - Added `/auth/validate` for nginx auth_request
  - Fixed study lookup to use `/tools/find` instead of `/tools/lookup`
  - Added detailed logging for debugging

- **File**: `auth-service/requirements.txt`
- **Added**: `PyJWT==2.8.0`

### 2. Nginx Configuration
- **File**: `config/nginx.conf`
- **Changes**:
  - Added Docker DNS resolver (`resolver 127.0.0.11`)
  - Added `/login` route (no auth required)
  - Added `/auth/validate` internal endpoint
  - Added `/api/dicom-web/studies` with auth_request
  - Added `/api/dicom-web/*` with auth_request
  - Added `@login_redirect` named location
  - Protected OHIF viewer routes with authentication

### 3. OHIF Configuration
- **File**: `platform/app/public/config/docker-nginx-orthanc-keycloak.js`
- **Changes**:
  - Changed `wadoUriRoot` from `/pacs` to `/api/dicom-web`
  - Changed `qidoRoot` from `/pacs` to `/api/dicom-web`
  - Changed `wadoRoot` from `/pacs` to `/api/dicom-web`

### 4. Orthanc Configuration
- **File**: `config/orthanc.json`
- **Changes**:
  - Disabled Authorization plugin (wasn't working correctly)
  - Studies labeled via Orthanc REST API

## Study Labeling

Studies were labeled using Orthanc's REST API:

```bash
# Label Study 1 for userA
curl -X PUT http://localhost:8042/studies/3d03892c-fe16a397-b54727fd-34224e15-421e37a7/labels/userA-study

# Label Study 2 for userB
curl -X PUT http://localhost:8042/studies/4f713b53-de937555-b96e8126-004e2afd-36a5095c/labels/userB-study
```

To verify labels:
```bash
curl http://localhost:8042/studies/3d03892c-fe16a397-b54727fd-34224e15-421e37a7/labels
# Output: [ "userA-study" ]

curl http://localhost:8042/studies/4f713b53-de937555-b96e8126-004e2afd-36a5095c/labels
# Output: [ "userB-study" ]
```

## Security Considerations

### Current Implementation
- **JWT Secret**: Hardcoded in `auth_service.py` (should be environment variable)
- **Passwords**: Stored in plaintext in code (should use password hashing)
- **Cookie**: httponly flag set (good for XSS protection)
- **HTTPS**: SSL certificates generated but not enforced
- **Session Duration**: 8 hours (configurable)

### Production Recommendations
1. **Use environment variables** for JWT secret and user credentials
2. **Hash passwords** with bcrypt or argon2
3. **Integrate with Keycloak** for real OAuth2/OIDC authentication
4. **Enforce HTTPS** and set `secure` flag on cookies
5. **Implement refresh tokens** for longer sessions
6. **Add rate limiting** on login endpoint
7. **Add logout functionality** to invalidate sessions
8. **Use PostgreSQL** to store user sessions for distributed deployments

## Adding New Users

### Method 1: Modify Code (Current)
Edit `auth-service/auth_service.py`:

```python
USERS = {
    "userA": {"password": "passwordA", "groups": ["annotatorA"]},
    "userB": {"password": "passwordB", "groups": ["annotatorB"]},
    "userC": {"password": "passwordC", "groups": ["annotatorC"]},  # New user
    "supervisor": {"password": "supervisor", "groups": ["pacsadmin"]}
}
```

Update filtering logic in `filter_studies()`:
```python
if group == 'annotatora' and 'userA-study' in labels:
    authorized = True
elif group == 'annotatorb' and 'userB-study' in labels:
    authorized = True
elif group == 'annotatorc' and 'userC-study' in labels:  # New group
    authorized = True
```

Rebuild and restart:
```bash
docker build -t ohif/auth-service:latest -f auth-service/Dockerfile auth-service
docker stop ohif_auth_service_kc && docker rm ohif_auth_service_kc
docker compose up -d auth_service
```

### Method 2: Database (Recommended for Production)
1. Create PostgreSQL table for users
2. Update auth service to query database
3. Create admin UI for user management
4. Store password hashes, not plaintext

## Adding New Studies

1. **Upload DICOM to Orthanc** (via OHIF upload or StoreSCU)

2. **Find study ID**:
   ```bash
   curl http://localhost:8042/studies
   ```

3. **Label the study**:
   ```bash
   # For userA access
   curl -X PUT http://localhost:8042/studies/{STUDY_ID}/labels/userA-study

   # For userB access
   curl -X PUT http://localhost:8042/studies/{STUDY_ID}/labels/userB-study

   # For multiple users (add multiple labels)
   curl -X PUT http://localhost:8042/studies/{STUDY_ID}/labels/userA-study
   curl -X PUT http://localhost:8042/studies/{STUDY_ID}/labels/userB-study
   ```

4. **Verify**:
   ```bash
   curl http://localhost:8042/studies/{STUDY_ID}/labels
   ```

## Troubleshooting

### Users See All Studies Instead of Filtered
**Cause**: OHIF config not updated or browser cache
**Fix**:
1. Verify config: `docker exec ohif_webapp_orthanc_kc cat /var/www/html/app-config.js | grep qidoRoot`
2. Should show: `qidoRoot:"/api/dicom-web"`
3. Hard refresh browser (Ctrl+Shift+R)
4. Or use incognito mode

### Login Redirects but Shows No Studies
**Cause**: Study labels not set or filtering logic issue
**Fix**:
1. Check labels: `curl http://localhost:8042/studies/{STUDY_ID}/labels`
2. Check auth service logs: `docker logs ohif_auth_service_kc`
3. Look for filtering logic in logs

### Container Restart Loop
**Cause**: Nginx can't resolve hostnames or config error
**Fix**:
1. Check all services running: `docker ps`
2. Start all services: `docker compose up -d`
3. Check nginx logs: `docker logs ohif_webapp_orthanc_kc`

### 502 Bad Gateway
**Cause**: DNS resolver not configured or service not reachable
**Fix**:
1. Verify `resolver 127.0.0.11` in nginx.conf
2. Check services are on same Docker network
3. Test connectivity: `docker exec ohif_webapp_orthanc_kc ping auth-service`

## Deployment

### Build and Start
```bash
cd /home/yicun/dev/OHIF_Viewer/platform/app/.recipes/Nginx-Orthanc-Keycloak

# Build auth service
docker build -t ohif/auth-service:latest -f auth-service/Dockerfile auth-service

# Build OHIF viewer
docker compose build ohif_viewer

# Start all services
docker compose up -d

# Check status
docker ps
```

### Restart Individual Services
```bash
# Restart auth service
docker stop ohif_auth_service_kc && docker rm ohif_auth_service_kc
docker compose up -d auth_service

# Restart OHIF/nginx
docker stop ohif_webapp_orthanc_kc && docker rm ohif_webapp_orthanc_kc
docker compose up -d ohif_viewer

# Restart Orthanc
docker stop ohif_orthanc_kc && docker rm ohif_orthanc_kc
docker compose up -d orthanc
```

## Legacy Endpoints (Backward Compatibility)

These endpoints still exist but are not used by the main flow:

- `/pacs-userA/studies` - Direct filtered access for userA
- `/pacs-userB/studies` - Direct filtered access for userB
- `/pacs/studies` - Unfiltered admin access
- `/oauth2/*` - OAuth2-proxy endpoints (not used in current flow)

These can be removed or kept for testing purposes.

## Future Enhancements

1. **Keycloak Integration**: Replace simple JWT with real OAuth2/OIDC
2. **Role-Based Access Control (RBAC)**: More granular permissions
3. **Study Sharing**: Allow users to share studies with each other
4. **Annotation Visibility**: Control who can see whose annotations
5. **Audit Logging**: Track who accessed which studies
6. **Multi-factor Authentication (MFA)**: Additional security layer
7. **Session Management**: Active session tracking and revocation
8. **API Rate Limiting**: Prevent abuse
9. **Admin Dashboard**: UI for user and study management
10. **Database Backend**: PostgreSQL for user and session management

## Performance Considerations

### Current Bottlenecks
- **Study filtering**: O(n) where n = total studies in Orthanc
- **Label lookup**: Individual API call per study

### Optimization Strategies
1. **Cache study labels** in Redis/memory
2. **Batch label queries** if Orthanc supports it
3. **Database indexing** on study labels
4. **Pagination** for large study lists
5. **Response caching** with appropriate TTL

## Conclusion

This authentication and authorization system provides:
- ✅ Single collaborative OHIF URL for all users
- ✅ User-specific study filtering
- ✅ JWT-based stateless authentication
- ✅ Orthanc label-based authorization
- ✅ Easy to add new users and studies
- ✅ Foundation for advanced collaboration features

The system successfully demonstrated that userA and userB can access the same OHIF instance but see different studies based on their assigned groups.

---

## SR (Structured Report) Authorization - October 28, 2025

### Problem

When users created SR (Structured Report) annotations and returned to the study, they could not see their own SR reports. The issue was that:

1. SR creation and labeling worked correctly (verified in logs)
2. Metadata filtering endpoint worked correctly
3. **BUT**: OHIF requests `/api/dicom-web/studies/{studyUID}/series` to get the series list
4. This endpoint was NOT filtered, so it showed ALL series including SRs from other users
5. When OHIF tried to load metadata for those series, the metadata filter correctly blocked them
6. Result: Users saw partial/broken SR series in the UI

### Solution: Series Filtering Endpoint

Added a new filtering layer at the series level to hide unauthorized SR series before OHIF even tries to load them.

#### Implementation

**1. Auth Service - Series Filter Endpoint** ([auth_service.py:780-917](auth-service/auth_service.py#L780-L917))

```python
@app.route('/filter/series/<path:path>', methods=['GET'])
def filter_series(path):
    """
    Filter series to hide SR series that don't belong to the user
    Path format: studies/{studyUID}/series
    """
    # Get user's groups from header
    groups_header = request.headers.get('X-Forwarded-Groups', '')
    groups = [g.strip().lower() for g in groups_header.split(',') if g.strip()]

    # Admin sees everything
    if 'pacsadmin' in groups or 'senior' in groups:
        return all_series

    # For each series:
    # 1. Check if it contains SR instances (via SOPClassUID)
    # 2. If SR: check instance labels
    # 3. Filter out SRs that don't belong to user's group
    # 4. Include all non-SR series
```

**Logic Flow:**
- Retrieves series list from Orthanc
- For each series:
  - Finds series in Orthanc by SeriesInstanceUID
  - Gets first instance in series
  - Checks SOPClassUID to identify if it's an SR series (`1.2.840.10008.5.1.4.1.1.88`)
  - If SR: checks instance labels (userA-sr, userB-sr, admin-sr)
  - Only includes SR series if user is authorized
  - Always includes non-SR series (images)

**2. Nginx Configuration Updates**

Added routing for series endpoint in both HTTP (line 189-203) and HTTPS (line 538-552) server blocks:

```nginx
# Series endpoints - filter to hide unauthorized SR series
location ~ ^/api/dicom-web/studies/([^/]+)/series$ {
    error_page 401 = @login_redirect;
    auth_request /auth/validate;
    auth_request_set $user_groups $upstream_http_x_user_groups;

    proxy_set_header X-Forwarded-Groups $user_groups;
    proxy_http_version 1.1;
    proxy_set_header Host $host;

    add_header 'Access-Control-Allow-Origin' '*' always;

    proxy_pass http://auth-service:8000/filter/series/studies/$1/series$is_args$args;
}
```

### Result

Now the authorization system has **three layers of filtering**:

1. **Study Level** (`/api/dicom-web/studies`) - Shows only studies with authorized labels
2. **Series Level** (`/api/dicom-web/studies/{uid}/series`) - **NEW** - Hides unauthorized SR series
3. **Metadata Level** (`/api/dicom-web/studies/{uid}/metadata`) - Filters individual SR instances

#### User Experience

- ✅ userA creates SR → labeled `userA-sr`
- ✅ userA returns to study → sees their own SR
- ✅ userB creates SR on same study → labeled `userB-sr`
- ✅ userB returns to study → sees only their SR
- ❌ userA cannot see userB's SR
- ❌ userB cannot see userA's SR
- ✅ supervisor sees all SRs from both users

### Deployment

```bash
# Rebuild auth service with new endpoint
docker build -t ohif/auth-service:latest -f auth-service/Dockerfile auth-service

# Restart services
docker stop ohif_auth_service_kc ohif_webapp_orthanc_kc
docker rm ohif_auth_service_kc ohif_webapp_orthanc_kc
docker compose up -d
```

### Logs Verification

```bash
docker logs -f ohif_auth_service_kc
```

Expected log output when viewing a study:
```
INFO:auth_service:Filter series request for groups: ['annotatorb'], path: studies/1.2.3.../series
INFO:auth_service:Processing series: 1.2.840...
INFO:auth_service:  This is an SR series, checking labels
INFO:auth_service:  SR series has labels: ['userB-sr']
INFO:auth_service:  ✓ SR series authorized for ['annotatorb']
INFO:auth_service:Returning 2 of 3 series
```

---

## UI Customization - October 28, 2025

### Disabling Investigational Use Dialog

**Problem**: Every login showed "OHIF Viewer is for investigational use only" dialog

**Solution**: Added configuration to disable the dialog

**File Modified**: `platform/app/public/config/docker-nginx-orthanc-keycloak.js`

```javascript
window.config = {
  routerBasename: '/ohif-viewer',
  // ... other config

  // Disable investigational use dialog
  investigationalUseDialog: {
    option: 'never',  // Options: 'never', 'always', 'configure'
  },

  // ... rest of config
};
```

**Dialog Options:**
- `'never'` - Never show the dialog
- `'always'` - Show every session (user must click "Confirm and hide")
- `'configure'` - Show once, then hide for N days (requires `days` parameter)

**Note**: This change requires rebuilding the OHIF viewer container since the config is embedded during build:

```bash
docker compose build ohif_viewer
docker compose up -d ohif_viewer
```

---

## Complete SR Authorization Architecture

### Full Request Flow

```
User opens study
    |
    v
OHIF: GET /api/dicom-web/studies/{studyUID}/series
    |
    v
Nginx: Validates JWT → Extracts groups → Routes to auth service
    |
    v
Auth Service: /filter/series/studies/{studyUID}/series
    |
    ├─> Fetch all series from Orthanc
    ├─> For each series:
    │   ├─> Is it an SR? (check SOPClassUID)
    │   ├─> If SR: Get instance labels
    │   ├─> Check if user group matches label
    │   └─> Include/exclude series
    └─> Return filtered series list
    |
    v
OHIF: Receives filtered list, displays only authorized series
```

### SR Labeling Flow (Upload)

```
User creates SR annotation
    |
    v
OHIF: POST /api/dicom-web/studies (STOW-RS)
    |
    v
Nginx: Routes to auth service upload proxy
    |
    v
Auth Service: /upload/studies
    |
    ├─> Extracts user group from JWT
    ├─> Determines label (userA-sr, userB-sr, admin-sr)
    ├─> Forwards STOW-RS to Orthanc
    ├─> Parses response to get created instance UIDs
    ├─> For each instance:
    │   ├─> Find Orthanc internal ID
    │   └─> PUT label via Orthanc API
    └─> Returns STOW-RS response to OHIF
```

### Key Files Summary

| File | Purpose | Key Changes |
|------|---------|-------------|
| `auth_service.py` | Authorization logic | Added `/filter/series/<path>` endpoint |
| `nginx.conf` | Request routing | Added series filtering location blocks |
| `docker-nginx-orthanc-keycloak.js` | OHIF config | Disabled investigational use dialog |

---

**Created**: October 26, 2025
**Last Updated**: October 28, 2025 (SR series filtering, UI customization)
**Author**: Claude (Anthropic)
**Tested**: WSL2 Ubuntu, Docker Compose
