# Changelog - OHIF Viewer Authorization System

All notable changes to this OHIF + Orthanc + Keycloak authentication/authorization system.

---

## [2025-10-28] - SR Series Filtering & UI Improvements

### Fixed
- **SR Visibility Issue**: Users can now see their own SR reports when returning to a study
  - Previously: SRs were created and labeled correctly but not visible in the UI
  - Root cause: Series endpoint was not filtered, showing all SR series including unauthorized ones
  - Solution: Added series-level filtering endpoint

### Added
- **Series Filtering Endpoint** in auth service ([auth_service.py:780-917](auth-service/auth_service.py#L780-L917))
  - Filters SR series based on user group and instance labels
  - Admin/senior users see all series
  - Regular users only see their own SR series
  - Logic: Checks SOPClassUID to identify SR series, then validates labels

- **Nginx Series Routing**
  - Added location blocks for `/api/dicom-web/studies/{studyUID}/series` endpoint
  - Routes through auth service filter
  - Passes user groups from JWT validation

### Changed
- **OHIF Configuration** - Disabled investigational use dialog
  - File: `platform/app/public/config/docker-nginx-orthanc-keycloak.js`
  - Added `investigationalUseDialog: { option: 'never' }`
  - Removes startup dialog prompt

### Architecture Improvements
- **Three-Layer Filtering System**:
  1. Study level - Shows only authorized studies
  2. **Series level** (NEW) - Hides unauthorized SR series
  3. Metadata level - Filters individual SR instances

### User Experience
- ✅ userA creates SR → sees it when returning to study
- ✅ userB creates SR → sees it when returning to study
- ❌ userA cannot see userB's SR on same study
- ❌ userB cannot see userA's SR on same study
- ✅ supervisor sees all SRs from all users

### Files Modified
```
auth-service/auth_service.py          # Added /filter/series endpoint
config/nginx.conf                      # Added series filtering routes
platform/app/public/config/docker-nginx-orthanc-keycloak.js  # Disabled dialog
```

### Deployment
```bash
# Rebuild auth service
docker build -t ohif/auth-service:latest -f auth-service/Dockerfile auth-service

# Restart services
docker stop ohif_auth_service_kc ohif_webapp_orthanc_kc
docker rm ohif_auth_service_kc ohif_webapp_orthanc_kc
docker compose up -d
```

### Testing
```bash
# Monitor logs
docker logs -f ohif_auth_service_kc

# Expected output when viewing study:
# INFO:auth_service:Filter series request for groups: ['annotatorb'], path: studies/.../series
# INFO:auth_service:Processing series: ...
# INFO:auth_service:  This is an SR series, checking labels
# INFO:auth_service:  SR series has labels: ['userB-sr']
# INFO:auth_service:  ✓ SR series authorized for ['annotatorb']
```

---

## [2025-10-26] - Initial Authorization System

### Added
- JWT-based authentication system with Flask auth service
- User-based study filtering using Orthanc labels
- Nginx auth_request integration
- Login page with credential validation
- Study filtering endpoint
- Metadata filtering for SR instances
- SR upload proxy with automatic labeling

### Components
- Auth Service (Flask + PyJWT)
- Nginx reverse proxy with auth gateway
- Keycloak identity provider
- Orthanc PACS with label-based authorization
- OHIF Viewer frontend

### Features
- User groups: annotatorA, annotatorB, annotatorC, senior, pacsadmin
- Study-level access control via labels
- Annotation segregation (double-blind)
- Automatic SR labeling on upload
- Multi-team support

### User Accounts (Auth Service)
| Username   | Password   | Groups       | Access                     |
|------------|------------|--------------|----------------------------|
| userA      | passwordA  | annotatorA   | Own studies + annotations  |
| userB      | passwordB  | annotatorB   | Own studies + annotations  |
| supervisor | supervisor | pacsadmin    | Full admin access          |

**Note**: Keycloak has additional users (annotatorA, annotatorB, annotatorC, senior) but the current system uses the simpler auth service login above.

### Documentation
- [AUTHORIZATION.md](AUTHORIZATION.md) - System overview and setup
- [MULTI-TEAM-GUIDE.md](MULTI-TEAM-GUIDE.md) - Multi-team configurations
- [claude.md](claude.md) - Technical implementation details

---

## Legend

- **Added** - New features
- **Changed** - Changes to existing functionality
- **Fixed** - Bug fixes
- **Removed** - Removed features
- **Security** - Security improvements
- **Deprecated** - Soon-to-be removed features

---

## Roadmap

### Planned Features
- [ ] Segmentation (SEG) filtering (same as SR filtering)
- [ ] Audit logging for access tracking
- [ ] Admin dashboard for user/study management
- [ ] Database backend for users and sessions
- [ ] Enhanced error handling and user feedback
- [ ] Performance optimization (caching, batch queries)
- [ ] Backup and restore procedures
- [ ] Production security hardening

### Known Issues
- Investigational use dialog removal requires webapp rebuild (not just config change)
- No session management UI (logout must clear cookies manually)
- Study label management requires curl commands (no UI)

---

**Maintained by**: Claude (Anthropic)
**Repository**: OHIF_Viewer/.recipes/Nginx-Orthanc-Keycloak
**Last Updated**: October 28, 2025
