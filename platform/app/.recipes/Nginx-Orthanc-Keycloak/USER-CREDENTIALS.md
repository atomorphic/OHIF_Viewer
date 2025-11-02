# User Credentials Reference

## Active User Accounts (Auth Service)

These are the **actual working credentials** for the current system:

| Username     | Password     | Groups       | Description                          |
|--------------|--------------|--------------|--------------------------------------|
| `userA`      | `passwordA`  | `annotatorA` | Annotator A - sees own studies/SRs   |
| `userB`      | `passwordB`  | `annotatorB` | Annotator B - sees own studies/SRs   |
| `supervisor` | `supervisor` | `pacsadmin`  | Supervisor - sees all studies/SRs    |

**Location**: Defined in `auth-service/auth_service.py` in the `USERS` dictionary

## Login Instructions

1. Navigate to: **http://localhost/login**
2. Enter username and password from table above
3. Click "Login"
4. You'll be redirected to OHIF Viewer at http://localhost/

## What Each User Can See

### userA (passwordA)
- ✅ Studies labeled with `userA-study`
- ✅ SR reports created by userA (labeled `userA-sr`)
- ❌ Cannot see userB's studies or SRs

### userB (passwordB)
- ✅ Studies labeled with `userB-study`
- ✅ SR reports created by userB (labeled `userB-sr`)
- ❌ Cannot see userA's studies or SRs

### supervisor (supervisor)
- ✅ ALL studies (regardless of labels)
- ✅ ALL SR reports from all users
- ✅ Access to Orthanc admin UI at http://localhost/pacs-admin/

## Testing Access

```bash
# Test userA login
curl -c /tmp/cookies_userA.txt -b /tmp/cookies_userA.txt \
  -d "username=userA&password=passwordA" http://localhost/login

curl -b /tmp/cookies_userA.txt http://localhost/api/dicom-web/studies

# Test userB login
curl -c /tmp/cookies_userB.txt -b /tmp/cookies_userB.txt \
  -d "username=userB&password=passwordB" http://localhost/login

curl -b /tmp/cookies_userB.txt http://localhost/api/dicom-web/studies

# Test supervisor login
curl -c /tmp/cookies_supervisor.txt -b /tmp/cookies_supervisor.txt \
  -d "username=supervisor&password=supervisor" http://localhost/login

curl -b /tmp/cookies_supervisor.txt http://localhost/api/dicom-web/studies
```

## Adding New Users

To add a new user, edit `auth-service/auth_service.py`:

```python
USERS = {
    "userA": {"password": "passwordA", "groups": ["annotatorA"]},
    "userB": {"password": "passwordB", "groups": ["annotatorB"]},
    "userC": {"password": "passwordC", "groups": ["annotatorC"]},  # NEW USER
    "supervisor": {"password": "supervisor", "groups": ["pacsadmin"]}
}
```

Then rebuild and restart:
```bash
docker build -t ohif/auth-service:latest -f auth-service/Dockerfile auth-service
docker stop ohif_auth_service_kc && docker rm ohif_auth_service_kc
docker compose up -d auth_service
```

## Keycloak Users (Not Currently Used)

The Keycloak realm configuration (`config/ohif-keycloak-realm.json`) contains these users, but they are **NOT** currently active in the authentication flow:

- annotatorA / annotatorA
- annotatorB / annotatorB
- annotatorC / annotatorC
- senior / senior
- pacsadmin / pacsadmin
- viewer / viewer

These could be activated if you switch from the simple auth service to full Keycloak OAuth2/OIDC authentication.

## Username vs Group Names

**Important distinction**:
- **Usernames** are what you type in the login form: `userA`, `userB`, `supervisor`
- **Group names** are used for authorization: `annotatorA`, `annotatorB`, `pacsadmin`
- **Labels** are applied to DICOM resources: `userA-sr`, `userB-sr`, `admin-sr`

Example:
- Username: `userA`
- Group: `annotatorA`
- Creates SRs labeled: `userA-sr`
- Can see SRs labeled: `userA-sr` only

## Security Notes

⚠️ **These are test credentials for development only!**

For production:
1. Change all passwords to strong, unique values
2. Store credentials in environment variables, not code
3. Use password hashing (bcrypt, argon2)
4. Implement proper OAuth2/OIDC with Keycloak
5. Enable HTTPS and set secure cookie flags
6. Add session management and logout functionality

---

**Last Updated**: October 28, 2025
**System**: OHIF Viewer + Orthanc + Simple Auth Service
