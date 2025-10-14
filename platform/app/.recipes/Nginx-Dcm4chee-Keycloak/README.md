# Nginx + Dcm4chee + Keycloak (localhost)

This recipe spins up an OHIF viewer secured by Keycloak in front of a Dcm4chee archive. The configuration in this folder is wired for a single-machine setup served from `https://localhost` using a self-signed certificate.

## Prerequisites

- Docker Desktop (or Docker Engine) with Docker Compose v2
- Ports `80`, `11112`, `2762`, `2575`, `12575`, `389`, `443`, `5432`, `8080`, `8081`, and `8443` free on the host
- `~/dcm4chee-arc` directory available for archive persistence

## One-time host preparation

1. Create the persistent storage folders (run on the host shell):
   ```bash
   mkdir -p ~/dcm4chee-arc/{ldap,slapd.d,wildfly,storage,db}
   ```
2. (Optional) If you prefer your own TLS material, drop `fullchain.pem` and `privkey.pem` under `config/letsencrypt/live/localhost/`. The repo already contains a self-signed pair generated for local development; browsers will prompt you to trust it.

## Bring the stack up

From the repository root, run:

```bash
cd platform/app/.recipes/Nginx-Dcm4chee-Keycloak
docker compose build ohif_viewer
docker compose up -d
```

- `ohif_viewer` builds the latest sources (uses `APP_CONFIG=config/docker-nginx-dcm4chee-keycloak.js`).
- The other services reuse the published Dcm4chee, Postgres, LDAP, and Keycloak images.

> **Tip:** The first build can take several minutes because it compiles the viewer. Subsequent `docker compose up` runs reuse the cache.

## Access points

- OHIF viewer: `https://localhost/ohif-viewer/`
- Dcm4chee UI: `https://localhost/dcm4chee-arc/ui2/`
- PACS REST: `https://localhost/pacs`
- Keycloak admin: `https://localhost/keycloak/`

Because the TLS certificate is self-signed, you must explicitly trust it in your browser the first time you hit `https://localhost`.

## Credentials

| Component  | Username    | Password   |
|------------|-------------|------------|
| Keycloak Admin Console | `admin` | `admin` |
| Viewer login | `viewer` | `viewer` |
| PACS admin (Keycloak group `pacsadmin`) | `pacsadmin` | `pacsadmin` |

## Tear down and cleanup

```bash
cd platform/app/.recipes/Nginx-Dcm4chee-Keycloak
docker compose down
```

Add `-v` to `docker compose down` if you want to wipe the named `postgres_data` volume (Keycloak DB). Remove `~/dcm4chee-arc` folders to reset the archive.

## Troubleshooting

- Check container logs: `docker compose logs -f <service>`
- If the viewer cannot load studies, ensure the browser trusts `https://localhost` and that the Dcm4chee services (`ldap`, `db`, `arc`) are healthy.
- If Keycloak returns redirect URI errors, confirm the certificates and that you are browsing via `https://localhost`.
