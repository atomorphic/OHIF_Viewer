# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the **Nginx-Orthanc-Keycloak** recipe for OHIF Viewer. It provides a production-ready deployment configuration with:
- **OHIF Viewer**: Medical imaging web application
- **Orthanc**: DICOM PACS server for storing/retrieving medical images
- **Keycloak**: OpenID Connect authentication and authorization
- **OAuth2 Proxy**: Authentication middleware
- **Nginx**: Reverse proxy and web server

## Quick Start

### Build and Run

```bash
# From this directory: platform/app/.recipes/Nginx-Orthanc-Keycloak/
docker-compose up --build
```

This starts all services:
- OHIF Viewer: http://localhost/ (redirects to /ohif-viewer/)
- Keycloak Admin: http://localhost/keycloak/
- Orthanc Admin UI: http://localhost/pacs-admin/ (requires pacsadmin group)
- PACS DICOMweb API: http://localhost/pacs/ (authenticated)
- Orthanc Direct Access: http://localhost:8042 (accessible from host only)

### Current Configuration

**Status**: This recipe is currently configured for localhost development.

All configuration files are set to use `http://localhost`:
- **docker-compose.yml**: Keycloak hostname URLs configured for localhost
- **config/nginx.conf**: Server name set to `localhost`, HTTP-only (port 80)
- **config/oauth2-proxy.cfg**: OIDC issuer and redirect URLs use localhost
- **config/ohif-keycloak-realm.json**: Client redirect URIs and web origins set to localhost

### For Production Deployment

To deploy to a production domain:

1. Replace `localhost` with your domain name in:
   - `docker-compose.yml`: `KC_HOSTNAME_ADMIN_URL`, `KC_HOSTNAME_URL`
   - `config/nginx.conf`: `server_name` directive
   - `config/oauth2-proxy.cfg`: `redirect_url`, `oidc_issuer_url`
   - `config/ohif-keycloak-realm.json`: `rootUrl`, `redirectUris`, `webOrigins`

2. Configure SSL certificates:
   - Place certificates in `config/letsencrypt/live/YOUR_DOMAIN/`
   - Or use the included Let's Encrypt certbot service
   - Update `config/nginx.conf` to enable HTTPS server block

### Default Users

Two users are pre-configured in Keycloak (defined in `config/ohif-keycloak-realm.json`):

1. **viewer** (standard user)
   - Username: `viewer`
   - Password: `viewer`
   - Email: viewer@mail.com
   - Access: Can view DICOM images via OHIF Viewer and PACS API

2. **pacsadmin** (admin user)
   - Username: `pacsadmin`
   - Password: `pacsadmin`
   - Email: pacsadmin@mail.com
   - Group: `pacsadmin`
   - Access: Full Orthanc admin UI access + all viewer permissions

## Architecture

### Authentication Flow

1. User accesses http://localhost/ → redirects to /ohif-viewer/
2. Nginx intercepts request → auth_request to OAuth2 Proxy at /oauth2/auth
3. If not authenticated, OAuth2 Proxy redirects to Keycloak login
4. User logs in via Keycloak (http://localhost/keycloak/)
5. Keycloak redirects back to OAuth2 Proxy callback (/oauth2/callback)
6. OAuth2 Proxy sets authentication cookie and redirects to original URL
7. Subsequent requests include auth cookie, validated by OAuth2 Proxy

### Request Routing (Nginx)

```
/                       → Redirects to /ohif-viewer/
/ohif-viewer/           → OHIF Viewer static files (auth required)
/pacs/                  → Orthanc DICOMweb API (auth required, any authenticated user)
/pacs-admin/            → Orthanc Admin UI (auth required, pacsadmin group only)
/keycloak/              → Keycloak server (proxied to keycloak:8080)
/oauth2/                → OAuth2 Proxy endpoints (callback, sign_in, sign_out)
```

### Group-Based Authorization

- **General users**: Can access OHIF Viewer and PACS DICOMweb API
- **pacsadmin group**: Additionally access Orthanc admin UI at /pacs-admin/
- Authorization is enforced via OAuth2 Proxy with `allowed_groups=pacsadmin` parameter

### Key Files

- **docker-compose.yml**: Service definitions and networking
- **dockerfile**: Multi-stage build (Node.js build → Nginx + OAuth2 Proxy)
- **config/nginx.conf**: Reverse proxy config with auth_request directives
- **config/oauth2-proxy.cfg**: OAuth2 Proxy configuration (OIDC client)
- **config/ohif-keycloak-realm.json**: Keycloak realm import (users, groups, clients)
- **config/orthanc.json**: Orthanc PACS server configuration
- **config/entrypoint.sh**: Container startup script (starts OAuth2 Proxy + Nginx)

### Data Persistence

- **postgres_data_orthanc_kc**: Keycloak database
- **./volumes/orthanc-db/**: Orthanc DICOM storage (on host filesystem)

## User Management

### Creating New Users

1. Access Keycloak Admin Console: http://localhost/keycloak/
2. Login with admin credentials (see docker-compose.yml: KEYCLOAK_ADMIN/KEYCLOAK_ADMIN_PASSWORD)
3. Select the `ohif` realm
4. Navigate to Users → Add User
5. Set username, email, first/last name
6. Go to Credentials tab → Set password (disable temporary if needed)
7. Enable the user account

### Granting PACS Admin Permissions

To allow a user to access Orthanc admin UI (/pacs-admin/):

1. In Keycloak Admin Console, go to Users → Select user
2. Navigate to Groups tab
3. Click "Join Group" and select `pacsadmin`
4. The user can now access /pacs-admin/ after re-login

### Creating Custom Groups

1. In Keycloak Admin Console, navigate to Groups
2. Create new group (e.g., `radiologist`, `technician`)
3. Assign users to groups
4. To enforce group-based access in Nginx:
   - Edit `config/nginx.conf`
   - Modify `auth_request` line to include: `?allowed_groups=yourgroup`
   - Example: `auth_request /oauth2/auth?allowed_groups=radiologist;`

## DICOM Image Permissions

**Current Setup**: All authenticated users can view all DICOM images stored in Orthanc. There is no per-study or per-patient access control.

**To Implement Fine-Grained Permissions**:

1. **Option A: Orthanc Authorization Plugin**
   - Requires Orthanc Authorization plugin
   - Configure `config/orthanc.json` to enable authorization
   - Implement custom authorization logic (Lua scripts or Python plugin)

2. **Option B: Reverse Proxy Filtering**
   - Parse StudyInstanceUID from WADO/QIDO requests in Nginx
   - Use Lua/OpenResty to query external authorization service
   - Block unauthorized requests at proxy level

3. **Option C: Keycloak User Attributes**
   - Store permitted StudyInstanceUIDs in Keycloak user attributes
   - Pass attributes via OAuth2 token to backend
   - Implement filtering in a middleware layer

## Development Workflow

### Local Development (without Docker)

From the repository root:

```bash
# Install dependencies
yarn install

# Start dev server with Orthanc proxy
cd platform/app
yarn dev:orthanc

# Or for general development
yarn dev
```

The dev server runs at http://localhost:3000 with hot-reload enabled.

### Build for Production

```bash
# From repository root
yarn build

# Or from platform/app/
yarn build:viewer
```

Built files are output to `platform/app/dist/` and are copied to the Docker image during build.

### Rebuilding Docker Image

```bash
# From platform/app/.recipes/Nginx-Orthanc-Keycloak/
docker-compose build ohif_viewer
docker-compose up -d
```

## Configuration Details

### OHIF Viewer Config

- **Config file**: `platform/app/public/config/docker-nginx-orthanc-keycloak.js`
- **Used during build**: Set via `APP_CONFIG` environment variable in dockerfile (line 27)
- **Key settings**:
  - `routerBasename: '/ohif-viewer'` - matches Nginx location
  - `wadoRoot`, `qidoRoot`, `wadoUriRoot`: `http://127.0.0.1/pacs` - proxied by Nginx to Orthanc

### OAuth2 Proxy

- **Version**: v7.4.0 (specified in dockerfile)
- **Port**: 4180 (internal)
- **Client ID**: `ohif_viewer`
- **Client Secret**: `2Xtlde7aozdkzzYHdIxQNfPDr0wNPTgg` (match in oauth2-proxy.cfg and Keycloak)
- **Cookie expiry**: 9m30s (with 5m refresh)
- **Important**: Cookie secret must be 32 bytes base64-encoded

### Keycloak Realm

- **Realm name**: `ohif`
- **Client**: `ohif_viewer` (confidential client with secret)
- **Groups**: `pacsadmin` (for Orthanc admin access)
- **Token lifespan**: 5 minutes (300s) - see ohif-keycloak-realm.json line 8
- **SSO session idle**: 30 minutes (1800s)

### Orthanc

- **Port**: 8042 (internal, not exposed to host)
- **DICOMweb root**: `/dicom-web/`
- **Auth**: Disabled in Orthanc itself (authentication handled by Nginx + OAuth2 Proxy)
- **Storage**: `/var/lib/orthanc/db` (persisted in `./volumes/orthanc-db/`)

## Troubleshooting

### "401 Unauthorized" on /pacs/ or /ohif-viewer/

- Check OAuth2 Proxy logs: `docker logs ohif_webapp_orthanc_kc`
- Verify Keycloak is accessible from OHIF container
- Ensure `KC_HOSTNAME_URL` matches the URL users access
- Check browser cookies (should have `_oauth2_proxy` cookie)

### "403 Forbidden" on /pacs-admin/

- User must be in `pacsadmin` group
- Check OAuth2 Proxy config: `allowed_groups=pacsadmin` in nginx.conf line 89
- Verify group membership in Keycloak Admin Console

### Keycloak redirect loops

- Ensure `redirect_url` in oauth2-proxy.cfg matches Keycloak client redirect URIs
- Check that `KC_HOSTNAME_URL` and `oidc_issuer_url` use same domain/protocol
- For localhost: Use `http://localhost` consistently (not `http://127.0.0.1`)

### SSL certificate errors

- For localhost testing, accept self-signed certificate warnings in browser
- Or configure nginx.conf to only use HTTP (port 80)
- For production, use Let's Encrypt certbot service (already configured in docker-compose.yml)

### DICOM images not loading

- Check Orthanc is running: `docker logs ohif_orthanc_kc`
- Verify Orthanc has DICOM files: http://localhost:8042 (accessible from host)
- Check OHIF config points to correct PACS endpoint: `/pacs`
- Verify Nginx proxy_pass to `http://orthanc:8042/dicom-web/`

## Related Commands

```bash
# View logs
docker-compose logs -f ohif_viewer
docker-compose logs -f keycloak
docker-compose logs -f orthanc

# Restart services
docker-compose restart ohif_viewer

# Stop and remove all containers
docker-compose down

# Remove volumes (WARNING: deletes Keycloak DB and DICOM images)
docker-compose down -v

# Execute shell in OHIF container
docker exec -it ohif_webapp_orthanc_kc sh

# Access Keycloak CLI
docker exec -it ohif_keycloak_kc /opt/keycloak/bin/kcadm.sh
```

## Security Notes

- Change default passwords (pacsadmin, viewer, Keycloak admin) before production
- Generate new OAuth2 Proxy cookie secret: `openssl rand -base64 32`
- Generate new Keycloak client secret in Admin Console
- Update `oauth2-proxy.cfg` and `ohif-keycloak-realm.json` with new secrets
- Use HTTPS in production (configure SSL certificates properly)
- Restrict Keycloak admin console access (currently exposed at /keycloak/)
