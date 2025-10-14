# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The OHIF Medical Image Viewing Platform is a zero-footprint medical image viewer provided by the Open Health Imaging Foundation. It is a configurable and extensible progressive web application with out-of-the-box support for image archives which support DICOMweb.

## Common Development Commands

### Installation & Setup

```bash
# Enable Yarn Workspaces (required)
yarn config set workspaces-experimental true

# Install dependencies
yarn install
```

### Development

```bash
# Start development server (default viewer)
yarn dev

# Start development server with faster build times using rsbuild
yarn dev:fast

# Start development server with Orthanc (DICOMweb server)
yarn dev:orthanc

# Start development server with static data
yarn dev:static
```

### Building

```bash
# Build for production
yarn build

# Build for development
yarn build:dev

# Build for CI
yarn build:ci

# Build for QA
yarn build:qa

# Build demo version
yarn build:demo
```

### Testing

```bash
# Run all unit tests
yarn test:unit

# Run unit tests with coverage
yarn test:unit:ci

# Run end-to-end tests with Playwright
yarn test:e2e

# Run end-to-end tests with UI
yarn test:e2e:ui

# Run end-to-end tests with HTML reporter
yarn test:e2e:reporter

# Debug end-to-end tests
yarn test:e2e:debug
```

### Utility Commands

```bash
# Clean build artifacts
yarn clean

# Deep clean (includes node_modules)
yarn clean:deep

# Show all files that have changed
yarn see-changed

# Generate documentation preview
yarn docs:preview
```

## Code Architecture

The OHIF Viewer is built as a monorepo with several key components:

### Platform Core Components

1. **@ohif/app**: The core framework that controls extension registration, mode composition and routing.
2. **@ohif/core**: A library of useful and reusable medical imaging functionality for the web.
3. **@ohif/ui**: A library of reusable UI components with OHIF styling.
4. **@ohif/i18n**: Internationalization support library.

### Extensions System

Extensions are building blocks that provide specific functionalities such as:

- **cornerstone**: 2D/3D image rendering with Cornerstone3D
- **cornerstone-dicom-sr**: DICOM Structured Report rendering and export
- **cornerstone-dicom-seg**: DICOM Segmentation rendering and export
- **cornerstone-dicom-rt**: DICOM RTSTRUCT rendering
- **cornerstone-microscopy**: Whole Slide Microscopy rendering
- **default**: Basic viewer layout, study/series browser, and DICOMWeb datasource
- **measurement-tracking**: Tools for tracking measurements
- **dicom-pdf**: PDF rendering
- **dicom-video**: DICOM video support
- **tmtv**: Total Metabolic Tumor Volume calculation

Extensions expose components, commands, and other capabilities that modes can use to build specific workflows.

### Modes

Modes are configuration objects that compose extensions to create specific workflows. Modes can be registered with routes to create different viewer experiences. Common modes include:

- **longitudinal**: For longitudinal measurement tracking
- **basic-dev-mode**: Basic viewer with Cornerstone (developer focused)
- **tmtv**: Total Metabolic Tumor Volume calculation
- **microscopy**: Whole slide microscopy viewing

### Project Structure

```
.
├── extensions               # Extension packages
│   ├── default              # Default viewer functionalities
│   ├── cornerstone          # Image rendering with Cornerstone3D
│   └── ...                  # Other extensions
│
├── modes                    # Mode configurations
│   ├── longitudinal         # Longitudinal measurement tracking
│   ├── basic-dev-mode       # Basic development mode
│   └── ...                  # Other modes
│
├── platform                 # Core platform packages
│   ├── app                  # Main viewer application
│   ├── core                 # Business logic
│   ├── i18n                 # Internationalization
│   └── ui                   # UI component library
│
├── tests                    # E2E tests with Playwright
└── ...                      # Configuration files
```

### Testing Framework

- **Unit Tests**: Jest is used for unit tests, configured in `jest.config.js` files
- **E2E Tests**: Playwright is used for end-to-end testing, configured in `playwright.config.ts`

### TypeScript Support

The project uses TypeScript with path aliases configured in `tsconfig.json` to make imports cleaner across the monorepo.

## Branch Structure

- **master**: The latest development (beta) release
  - Contains the most recent changes and features
  - Packages are tagged with beta versions (e.g., `@ohif/ui@3.6.0-beta.1`)

- **release/***: The latest stable releases
  - Created from `master` after comprehensive code review and QA
  - Each release branch (e.g., `release/3.5`, `release/3.6`) corresponds to a specific version
  - Bug fixes result in minor version bumps (e.g., 3.5.1 in the `release/3.5` branch)

## System Requirements

- Node.js 18+
- Yarn 1.20.0+
- Yarn Workspaces enabled (`yarn config set workspaces-experimental true`)

## Working with the Codebase

When developing new features or fixing bugs:

1. Understand whether your changes should be in an extension or a mode
2. For new features, consider creating an extension that can be used by multiple modes
3. For UI changes, check if there are existing components in @ohif/ui to maintain consistency
4. Run tests to ensure your changes don't break existing functionality

## Nginx-Orthanc-Keycloak Setup

The OHIF Viewer can be deployed with Nginx, Orthanc PACS, and Keycloak for authentication. This setup provides a production-ready deployment with user access control.

### With Docker (Recommended)

#### Prerequisites
- Docker and Docker Compose installed
- Port 80, 443, and 8080 available

#### Setup Steps

1. Navigate to the recipe directory:
```bash
cd platform/app/.recipes/Nginx-Orthanc-Keycloak
```

2. Configure the deployment by editing the following files:

**docker-compose.yml:**
- Replace `YOUR_DOMAIN` with your domain or IP (use `127.0.0.1` for local testing)
- Update Keycloak URLs:
  ```yaml
  KC_HOSTNAME_ADMIN_URL: http://127.0.0.1/keycloak/
  KC_HOSTNAME_URL: http://127.0.0.1/keycloak/
  ```

**config/nginx.conf:**
- Replace `YOUR_DOMAIN` with your server name
- For local testing without SSL, merge the two server blocks into one HTTP-only server

**config/oauth2-proxy.cfg:**
- Update redirect and issuer URLs:
  ```
  redirect_url="http://127.0.0.1/oauth2/callback"
  oidc_issuer_url="http://127.0.0.1/keycloak/realms/ohif"
  ```

**platform/app/public/config/docker-nginx-orthanc-keycloak.js:**
- Update PACS endpoints:
  ```javascript
  wadoUriRoot: 'http://127.0.0.1/pacs',
  qidoRoot: 'http://127.0.0.1/pacs',
  wadoRoot: 'http://127.0.0.1/pacs',
  ```

3. Build and run the services:
```bash
# Build and start all services
docker-compose up --build

# For subsequent runs (no rebuild)
docker-compose up -d
```

4. Access the services:
- OHIF Viewer: `http://127.0.0.1/ohif-viewer`
- Orthanc Admin: `http://127.0.0.1/pacs-admin`
- Keycloak Admin: `http://127.0.0.1/keycloak` (admin/admin)

#### Default Credentials

**Keycloak Admin Console** (http://127.0.0.1:8080):
- Username: `admin`
- Password: `admin`

**Test Users for OHIF Viewer**:

Regular Viewer User:
- Username: `viewer`
- Password: `viewer`
- Email: `viewer@mail.com`
- Access: Standard viewing privileges

PACS Admin User:
- Username: `pacsadmin`
- Password: `pacsadmin`
- Email: `pacsadmin@mail.com`
- Access: Full access including Orthanc admin interface at `/pacs-admin`

### Without Docker (Manual Setup)

#### Prerequisites
- Node.js 18+ and Yarn installed
- Nginx installed and configured
- Orthanc PACS running
- Keycloak server running
- PostgreSQL for Keycloak
- OAuth2 Proxy installed

#### Setup Steps

1. Build the OHIF Viewer:
```bash
# Enable yarn workspaces
yarn config set workspaces-experimental true

# Install dependencies
yarn install

# Set configuration for Keycloak integration
export APP_CONFIG=config/docker-nginx-orthanc-keycloak.js

# Build the viewer
yarn build
```

2. Configure Nginx:
- Copy `platform/app/.recipes/Nginx-Orthanc-Keycloak/config/nginx.conf` to your Nginx configuration directory
- Update server_name and proxy_pass URLs to match your setup
- Copy built viewer files from `platform/app/dist` to Nginx's web root (typically `/var/www/html`)

3. Configure OAuth2 Proxy:
- Install OAuth2 Proxy: https://oauth2-proxy.github.io/oauth2-proxy/
- Use configuration from `platform/app/.recipes/Nginx-Orthanc-Keycloak/config/oauth2-proxy.cfg`
- Update URLs and client credentials to match your Keycloak setup

4. Configure Keycloak:
- Import realm configuration from `platform/app/.recipes/Nginx-Orthanc-Keycloak/config/ohif-keycloak-realm.json`
- Update redirect URIs to match your domain
- Configure client credentials for OAuth2 Proxy

5. Configure Orthanc:
- Use configuration from `platform/app/.recipes/Nginx-Orthanc-Keycloak/config/orthanc.json`
- Ensure DICOM Web plugin is enabled
- Configure CORS settings to allow requests from your domain

6. Start all services:
```bash
# Start Nginx
sudo systemctl start nginx

# Start OAuth2 Proxy
oauth2-proxy --config=/path/to/oauth2-proxy.cfg

# Start Orthanc
Orthanc /path/to/orthanc.json

# Start Keycloak (adjust based on your installation)
/opt/keycloak/bin/kc.sh start
```

### Architecture Overview

The setup creates an authenticating reverse proxy:
- **Nginx**: Reverse proxy handling all incoming requests
- **OAuth2 Proxy**: Authenticates users via OAuth2/OIDC with Keycloak
- **Keycloak**: Identity and access management
- **Orthanc**: PACS server for medical imaging data
- **OHIF Viewer**: Medical image viewer application

Routes:
- `/ohif-viewer`: OHIF Viewer application
- `/pacs`: Orthanc DICOM Web endpoints
- `/pacs-admin`: Orthanc administrative interface
- `/keycloak`: Keycloak admin console
- `/oauth2`: OAuth2 Proxy endpoints

### SSL/HTTPS Configuration

For production deployments with SSL:

1. Obtain SSL certificates (e.g., using Let's Encrypt)
2. Update nginx.conf to include SSL configuration
3. Update all URLs from http:// to https://
4. Configure Keycloak for HTTPS
5. Update OAuth2 Proxy configuration for secure cookies

### Troubleshooting

- **Port conflicts**: Ensure ports 80, 443, 8080 are available
- **Keycloak not starting**: Check PostgreSQL connection and health check configuration
- **Authentication loops**: Verify OAuth2 Proxy and Keycloak redirect URLs match
- **CORS errors**: Check Orthanc and Nginx CORS configuration
- **Studies not loading**: Verify PACS endpoints in viewer configuration

### Security Notes

This setup provides basic authentication but should be further hardened for production:
- Use HTTPS/SSL in production
- Configure proper CORS policies
- Set secure cookie flags
- Implement rate limiting
- Regular security updates for all components
- Audit user access logs

## Role-Based Access Control with Label-Based Study Assignment

The Nginx-Orthanc-Keycloak setup includes a sophisticated role-based access control system that uses Orthanc labels to control which studies users can access and whose annotations they can view.

### Architecture Overview

The access control system consists of:
1. **Keycloak Roles**: Define user permissions (annotator, reviewer, admin)
2. **Keycloak Groups**: Map to Orthanc labels for study access
3. **Orthanc Labels**: Tags on studies that determine access
4. **OHIF userAssignments**: Controls annotation visibility based on roles
5. **Lua Script**: Filters study access based on user groups and labels

### Roles and Permissions

| Role | Study Access | Annotation Visibility | Label Management |
|------|--------------|----------------------|------------------|
| **annotator** | Only labeled studies in their groups | Own annotations only | No |
| **reviewer** | Only labeled studies in their groups | All annotations on accessible studies | No |
| **admin** | All studies | All annotations | Yes (via pacsadmin group) |

### Pre-configured Test Users

| Username | Password | Role | Group(s) | Description |
|----------|----------|------|----------|-------------|
| admin | admin | admin | pacsadmin | Full system access |
| pacsadmin | pacsadmin | admin | pacsadmin | PACS administrator with label management |
| annotator-cardio | annotator | annotator | label-cardiology | Cardiology annotator |
| annotator-neuro | annotator | annotator | label-neurology | Neurology annotator |
| reviewer-cardio | reviewer | reviewer | label-cardiology | Cardiology reviewer |
| reviewer-multi | reviewer | reviewer | label-cardiology, label-neurology | Multi-department reviewer |

### How It Works

1. **Study Assignment via Labels**:
   - Admin users apply labels to studies in Orthanc (e.g., "cardiology", "neurology")
   - Users in corresponding groups (e.g., "label-cardiology") can access those studies
   - Only pacsadmin users can add/remove labels

2. **Annotation Visibility**:
   - Controlled by OHIF's userAssignments configuration
   - Annotators see only their own annotations
   - Reviewers see all annotations on their accessible studies
   - Admins see all annotations

3. **Access Flow**:
   ```
   User Login → Keycloak Authentication → OAuth2 Proxy →
   Nginx (passes groups/roles) → Orthanc (Lua script filters) →
   OHIF Viewer (applies annotation visibility rules)
   ```

### Setup Instructions

#### 1. Deploy with Docker

```bash
cd platform/app/.recipes/Nginx-Orthanc-Keycloak
docker-compose down
docker-compose up -d
```

#### 2. Access and Login

**Service URLs**:
- OHIF Viewer: `http://127.0.0.1/ohif-viewer`
- Orthanc Admin: `http://127.0.0.1/pacs-admin` (requires pacsadmin group)
- Keycloak Admin: `http://127.0.0.1/keycloak` or `http://127.0.0.1:8080`

**Login Process**:
1. Navigate to `http://127.0.0.1/ohif-viewer`
2. You'll be redirected to Keycloak login page
3. Enter username and password from the table below
4. After successful login, you'll be redirected back to OHIF Viewer

**Important**: After restarting containers with `docker-compose down -v && docker-compose up -d`, wait about 60 seconds for Keycloak to fully initialize before attempting to login.

**Keycloak Admin Console**:
- URL: `http://127.0.0.1:8080`
- Username: `admin`
- Password: `admin`

**Test User Credentials**:

| Username | Password | Access Level |
|----------|----------|--------------|
| `admin` | `admin` | Full access to all studies and annotations |
| `pacsadmin` | `pacsadmin` | Full access + can manage labels in Orthanc |
| `annotator-cardio` | `annotator` | Cardiology studies only, sees own annotations |
| `annotator-neuro` | `annotator` | Neurology studies only, sees own annotations |
| `reviewer-cardio` | `reviewer` | Cardiology studies, sees all annotations |
| `reviewer-multi` | `reviewer` | Multiple departments, sees all annotations |

#### 3. Assign Labels to Studies

1. Login as `pacsadmin` at `http://127.0.0.1/ohif-viewer`
2. Navigate to `http://127.0.0.1/pacs-admin`
3. Find your studies and add labels:
   - Click on a study
   - Add labels like "cardiology", "neurology", "oncology", or "emergency"
   - These labels determine which users can access the study

#### 3. Test Access Control

1. **Test as Annotator**:
   - Login as `annotator-cardio`
   - You'll only see studies labeled "cardiology"
   - Create annotations - you'll only see your own

2. **Test as Reviewer**:
   - Login as `reviewer-cardio`
   - You'll see studies labeled "cardiology"
   - You can view ALL annotations on these studies

3. **Test as Admin**:
   - Login as `admin` or `pacsadmin`
   - You'll see all studies regardless of labels
   - You can view all annotations

### Adding New Users and Groups

#### Create a New Department Group

1. Edit `ohif-keycloak-realm.json` to add a new group:
```json
{
  "id": "label-radiology-id",
  "name": "label-radiology",
  "path": "/label-radiology",
  "attributes": {
    "orthanc_labels": ["radiology"],
    "description": ["Users who can access studies labeled 'radiology'"]
  }
}
```

2. Add corresponding users with appropriate roles:
```json
{
  "username": "annotator-radiology",
  "email": "annotator-radiology@mail.com",
  "credentials": [{"type": "password", "value": "password"}],
  "realmRoles": ["annotator"],
  "groups": ["label-radiology"]
}
```

3. Update OHIF configuration in `docker-nginx-orthanc-keycloak.js`:
```javascript
userAssignments: {
  groups: {
    'radiology-team': ['annotator-radiology', 'reviewer-radiology']
  },
  users: {
    'annotator-radiology': {
      allowAnnotationsFrom: ['self']
    }
  }
}
```

### Implementation Details

#### Components Modified

1. **Keycloak Configuration** (`ohif-keycloak-realm.json`):
   - Added roles: annotator, reviewer, admin
   - Created label-based groups matching Orthanc labels
   - Configured test users with appropriate role/group assignments

2. **OAuth2 Proxy** (`oauth2-proxy.cfg`):
   - Extended scope to include groups and roles
   - Configured to pass group information in headers

3. **Nginx Configuration** (`nginx.conf`):
   - Added headers to pass user groups and roles to Orthanc
   - Configured authentication flow for all endpoints

4. **Orthanc Lua Script** (`label-filter.lua`):
   - Filters study access based on user groups and study labels
   - Restricts label management to admin users only
   - Implements REST API access control

5. **OHIF Configuration** (`docker-nginx-orthanc-keycloak.js`):
   - Configured userAssignments for annotation visibility
   - Defined groups and per-user rules
   - Set up role-based annotation access

#### Technical Flow

1. **Authentication**:
   - User authenticates with Keycloak
   - Keycloak returns JWT with roles and groups
   - OAuth2 Proxy validates and extracts claims

2. **Authorization**:
   - Nginx passes group information via headers
   - Orthanc Lua script checks if user's groups match study labels
   - Access granted only if there's a match (or user is admin)

3. **Annotation Filtering**:
   - OHIF reads user information from authentication service
   - Applies userAssignments rules based on user ID and role
   - Filters annotations based on configured visibility rules

### Scaling Considerations

For production environments with many studies:

1. **Dynamic Label Assignment**:
   - Build an admin UI for label management
   - Use DICOM tags for automatic labeling
   - Implement bulk labeling operations

2. **Group Management**:
   - Integrate with existing LDAP/AD groups
   - Create hierarchical group structures
   - Implement group inheritance

3. **Performance**:
   - Cache group memberships
   - Optimize Lua script for large datasets
   - Consider database-backed access control

### Current Limitations & Workarounds

#### Study Filtering Limitation
**Issue**: Orthanc's DICOM Web plugin doesn't natively support filtering studies based on labels in the query response. This means all users currently see all studies in the study list, regardless of their group assignments.

**Workarounds**:

1. **Manual Enforcement** (Current):
   - Admin assigns labels to studies in Orthanc
   - Users are instructed to only access studies matching their department
   - Access logs can be audited for compliance

2. **Client-Side Filtering** (Recommended for small datasets):
   - Implement JavaScript filtering in OHIF to hide studies without matching labels
   - Requires custom OHIF extension development
   - Not secure (client-side only) but improves UX

3. **Proxy-Based Filtering** (Recommended for production):
   - Deploy a filtering proxy between OHIF and Orthanc
   - Proxy queries Orthanc for labels and filters the response
   - More complex but provides true server-side filtering

4. **Alternative Solutions**:
   - Use separate Orthanc instances per department
   - Implement custom Orthanc plugin in C++
   - Use a different PACS that supports native label-based filtering

#### What IS Working
- ✅ User authentication via Keycloak
- ✅ Role-based access (annotator, reviewer, admin)
- ✅ Annotation visibility control based on roles
- ✅ Label management restricted to admins
- ✅ Access to pacs-admin interface for pacsadmin group

### Troubleshooting

- **Studies visible to all users**: This is a known limitation. See "Study Filtering Limitation" above
- **Users can't see any studies**: Check if Orthanc has studies loaded
- **Annotations not visible**: Verify userAssignments configuration in OHIF
- **Can't manage labels**: Ensure user is in pacsadmin group
- **Authentication errors**: Check OAuth2 Proxy logs and Keycloak configuration
- **403 Forbidden on pacs-admin**: User must be in pacsadmin group