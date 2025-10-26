#!/usr/bin/env python3
"""
Authorization service for Orthanc
Implements double-blind annotation access control based on labels and groups
"""

from flask import Flask, request, jsonify, Response, make_response, redirect
import json
import logging
import jwt
from datetime import datetime, timedelta
import hashlib

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Secret key for JWT signing (in production, use environment variable)
JWT_SECRET = "your-secret-key-change-in-production"

# Simple user database (in production, validate against Keycloak API)
USERS = {
    "userA": {"password": "passwordA", "groups": ["annotatorA"]},
    "userB": {"password": "passwordB", "groups": ["annotatorB"]},
    "admin": {"password": "admin123", "groups": ["pacsadmin"]}
}

# Add after_request handler to log all responses
@app.after_request
def log_response(response):
    if request.path.startswith('/auth/user/get-profile'):
        logger.info(f">>> RESPONSE START <<<")
        logger.info(f"Status: {response.status}")
        logger.info(f"Headers: {dict(response.headers)}")
        logger.info(f"Body (raw bytes): {response.get_data()}")
        logger.info(f"Body (text): {response.get_data(as_text=True)}")
        logger.info(f">>> RESPONSE END <<<")
    return response

@app.route('/auth', methods=['POST'])
def authorize():
    """
    Authorization endpoint called by Orthanc Authorization plugin

    Request format from Orthanc:
    {
        "dicom-uid": "1.2.3.4.5...",
        "level": "study" | "series" | "instance",
        "method": "get" | "post" | "put" | "delete",
        "orthanc-id": "orthanc-resource-id",
        "uri": "/studies/xxx",
        "groups": ["annotatorA", "senior"],  # From X-Forwarded-Groups header
        "username": "annotatorA"              # From X-Remote-User header
    }

    Response: {"granted": true/false, "validity": 600}
    """
    try:
        data = request.json
        logger.info(f"Authorization request: {data}")

        # Extract auth context
        username = data.get('username', '')
        groups = data.get('groups', [])
        if isinstance(groups, str):
            groups = [g.strip() for g in groups.split(',') if g.strip()]

        method = data.get('method', '').lower()
        level = data.get('level', '')
        orthanc_id = data.get('orthanc-id', '')
        uri = data.get('uri', '')

        # Get labels from Orthanc (passed by the plugin if available)
        labels = data.get('labels', [])

        logger.info(f"User: {username}, Groups: {groups}, Method: {method}, Level: {level}, Labels: {labels}")

        # Authorization logic
        granted = check_authorization(username, groups, method, level, orthanc_id, labels, uri)

        return jsonify({
            "granted": granted,
            "validity": 600  # Cache for 10 minutes
        })

    except Exception as e:
        logger.error(f"Authorization error: {e}", exc_info=True)
        return jsonify({"granted": False}), 500


def check_authorization(username, groups, method, level, orthanc_id, labels, uri):
    """
    Check if user is authorized for the requested resource

    Rules:
    1. Senior group: Full access to everything (wildcard)
    2. annotatorA: Access to studies labeled with "proj-x" and own annotations ("ann-teamA")
    3. annotatorB: Access to studies labeled with "proj-x" and own annotations ("ann-teamB")
    4. pacsadmin: Full access
    """

    # Admin and senior have full access
    if 'pacsadmin' in groups or 'senior' in groups:
        logger.info(f"✓ Admin/Senior access granted")
        return True

    # Determine which team this user belongs to
    team_label = None
    if 'annotatorA' in groups:
        team_label = 'ann-teamA'
    elif 'annotatorB' in groups:
        team_label = 'ann-teamB'
    elif 'annotatorC' in groups:
        team_label = 'ann-teamC'

    if not team_label:
        logger.info(f"✗ User not in any annotator group")
        return False

    # For DICOM instances (studies/series/instances)
    if level in ['study', 'series', 'instance']:

        # Check if this is an annotation (SEG/SR)
        if 'ann-teamA' in labels or 'ann-teamB' in labels or 'ann-teamC' in labels:
            # This is an annotation - check if it belongs to this team
            if team_label in labels:
                logger.info(f"✓ Annotation access granted: {team_label} in labels")
                return True
            else:
                logger.info(f"✗ Annotation blocked: {team_label} not in {labels}")
                return False

        # Check if study is assigned to this annotator
        # Studies should be labeled with project labels like "proj-x"
        # For simplicity, allow access to any study without team-specific annotation labels
        # (This means annotators can see raw studies, but not each other's annotations)
        if method == 'get':
            # Allow reading studies (but annotations are filtered above)
            logger.info(f"✓ Study read access granted")
            return True
        elif method == 'post' and uri.endswith('/instances'):
            # Allow uploading new instances (annotations will be auto-labeled by Python plugin)
            logger.info(f"✓ Instance upload access granted")
            return True

    # Default deny
    logger.info(f"✗ Access denied by default")
    return False


@app.route('/auth/user/get-profile', methods=['POST'])
def get_user_profile():
    """
    Return user profile with authorized labels

    Orthanc Authorization plugin sends tokens as array of objects:
    {
        "tokens": [
            {"token-key": "x-remote-user", "token-value": "pacsadmin"},
            {"token-key": "x-forwarded-groups", "token-value": "pacsadmin"}
        ]
    }

    Response:
    {
        "name": "pacsadmin",
        "authorized_labels": ["*"],
        "permissions": ["all"]
    }
    """
    try:
        # Log ALL request details
        logger.info(f"=== User Profile Request ===")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Method: {request.method}")
        data = request.json or {}
        logger.info(f"JSON Body: {data}")

        # Extract username and groups from tokens array (Orthanc format)
        username = ''
        groups = []

        # Handle array format (newer Orthanc versions)
        tokens = data.get('tokens', [])
        if tokens:
            for token in tokens:
                token_key = token.get('token-key', '').lower()
                token_value = token.get('token-value', '')

                if token_key == 'x-remote-user':
                    username = token_value
                elif token_key == 'x-forwarded-groups':
                    if isinstance(token_value, str):
                        groups = [g.strip() for g in token_value.split(',') if g.strip()]
                    elif isinstance(token_value, list):
                        groups = token_value

        # Handle old single-token format (current Orthanc version)
        if not username and 'token-key' in data:
            token_key = data.get('token-key', '').lower()
            token_value = data.get('token-value', '')

            # Skip empty token-key or empty token-value - return 404 so Orthanc knows we don't have this token
            if token_key == '' or token_value == '':
                logger.info(f"Skipping empty token-key or token-value")
                return Response('{}', status=404, mimetype='application/json')

            if token_key == 'x-remote-user':
                username = token_value
            elif token_key == 'x-forwarded-groups':
                if isinstance(token_value, str):
                    groups = [g.strip() for g in token_value.split(',') if g.strip()]
                elif isinstance(token_value, list):
                    groups = token_value

        # Fallback to direct format for testing
        if not username:
            username = data.get('username', '')
        if not groups:
            groups_data = data.get('groups', [])
            if isinstance(groups_data, str):
                groups = [g.strip() for g in groups_data.split(',') if g.strip()]
            else:
                groups = groups_data

        # If username is empty but we have groups, use the first group as username
        if not username and groups:
            username = groups[0]

        # If still no username or groups, return minimal profile
        # (Orthanc calls this endpoint multiple times with different tokens)
        if not username:
            logger.info(f"Empty token - returning minimal profile")
            # Manually construct JSON to ensure exact format
            response_data = '{"name":"guest","authorized_labels":["*"],"permissions":["view"]}'
            logger.info(f"Responding with: {response_data}")
            logger.info(f"Response length: {len(response_data)}")
            return Response(response_data, mimetype='application/json')

        logger.info(f"Extracted user: {username}, groups: {groups}")

        # Determine authorized labels based on groups
        authorized_labels = []

        # Convert groups to lowercase for case-insensitive comparison
        groups_lower = [g.lower() for g in groups]

        # Admin and senior have access to all labels (wildcard)
        if 'pacsadmin' in groups_lower or 'senior' in groups_lower:
            logger.info(f"Admin/Senior profile - full access")
            # Note: permissions must be explicit list, not ["all"]
            # IMPORTANT: Don't use jsonify() - it adds trailing newline which Orthanc rejects
            # Try hyphenated field name
            profile = {
                "name": username,
                "permissions": ["view", "download", "modify", "upload", "delete", "share"],
                "authorized-labels": ["*"]
            }
            logger.info(f"=== User Profile Response ===")
            logger.info(f"Profile dict: {profile}")
            # Use json.dumps() with Response to avoid trailing newline
            json_data = json.dumps(profile, separators=(',', ':'))
            return Response(json_data, mimetype='application/json', status=200)

        # Annotators have access to their study label
        if 'annotatora' in groups_lower:
            authorized_labels.append('userA-study')
        if 'annotatorb' in groups_lower:
            authorized_labels.append('userB-study')
        if 'annotatorc' in groups_lower:
            authorized_labels.append('userC-study')

        # Add project labels - all annotators can see studies with these labels
        # (but only their own annotations on those studies)
        authorized_labels.extend(['proj-x', 'proj-y', 'proj-z', 'proj-cardiac', 'proj-lung', 'proj-brain', 'proj-common'])

        logger.info(f"User {username} authorized labels: {authorized_labels}")

        profile = {
            "name": username,
            "authorized-labels": authorized_labels,
            "permissions": ["view"]
        }
        logger.info(f"Responding with profile: {profile}")
        # Use json.dumps() with Response to avoid trailing newline
        json_data = json.dumps(profile, separators=(',', ':'))
        return Response(json_data, mimetype='application/json', status=200)

    except Exception as e:
        logger.error(f"User profile error: {e}", exc_info=True)
        return jsonify({"name": "", "authorized_labels": [], "permissions": []}), 500


@app.route('/auth/tokens/decode', methods=['POST'])
def decode_token():
    """
    Decode a resource token
    This endpoint is called by Orthanc Authorization plugin to decode resource tokens.
    For our use case, we rely on user profiles and labels instead of resource tokens.
    """
    try:
        data = request.json or {}
        logger.info(f"Token decode request: {data}")

        # Return empty decoded token - authorization will use user profile instead
        return jsonify({
            "redirect-url": "",
            "token-type": "none"
        })
    except Exception as e:
        logger.error(f"Token decode error: {e}", exc_info=True)
        return jsonify({"redirect-url": "", "token-type": "none"}), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Simple login page and authentication
    GET: Returns login HTML page
    POST: Validates credentials and sets JWT cookie
    """
    if request.method == 'GET':
        # Return simple login page
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>OHIF Login</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: #f0f0f0;
                }
                .login-box {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    width: 300px;
                }
                h2 {
                    margin-top: 0;
                    color: #333;
                }
                input {
                    width: 100%;
                    padding: 10px;
                    margin: 10px 0;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    box-sizing: border-box;
                }
                button {
                    width: 100%;
                    padding: 10px;
                    background: #5755d9;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                }
                button:hover {
                    background: #4542c7;
                }
                .error {
                    color: red;
                    margin-top: 10px;
                }
                .info {
                    color: #666;
                    font-size: 12px;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="login-box">
                <h2>OHIF Viewer Login</h2>
                <form method="POST" action="/login">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Login</button>
                </form>
                <div class="info">
                    Test accounts:<br>
                    userA / passwordA<br>
                    userB / passwordB<br>
                    admin / admin123
                </div>
            </div>
        </body>
        </html>
        """
        return html

    # POST: Validate credentials
    try:
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        logger.info(f"Login attempt for user: {username}")

        # Validate credentials
        if username not in USERS or USERS[username]['password'] != password:
            logger.info(f"Login failed for user: {username}")
            return """
            <html>
            <body>
                <h2>Login Failed</h2>
                <p style="color: red;">Invalid username or password</p>
                <a href="/login">Try again</a>
            </body>
            </html>
            """, 401

        # Create JWT token
        user_data = USERS[username]
        token = jwt.encode({
            'username': username,
            'groups': user_data['groups'],
            'exp': datetime.utcnow() + timedelta(hours=8)
        }, JWT_SECRET, algorithm='HS256')

        logger.info(f"Login successful for user: {username}, groups: {user_data['groups']}")

        # Set cookie and redirect to OHIF
        response = make_response(redirect('/', 302))
        response.set_cookie('auth_token', token, httponly=True, max_age=28800)  # 8 hours
        return response

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return "Login error", 500


@app.route('/auth/validate', methods=['GET'])
def validate_session():
    """
    Validate JWT token from cookie
    Called by nginx auth_request
    Returns 200 with X-User-Groups header if valid, 401 if invalid
    """
    try:
        token = request.cookies.get('auth_token')

        if not token:
            logger.info("No auth token found in cookies")
            return Response('', status=401)

        # Decode and validate JWT
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            username = payload.get('username')
            groups = payload.get('groups', [])

            logger.info(f"Valid token for user: {username}, groups: {groups}")

            # Return success with groups in header
            response = Response('', status=200)
            response.headers['X-User-Groups'] = ','.join(groups)
            response.headers['X-User-Name'] = username
            return response

        except jwt.ExpiredSignatureError:
            logger.info("Token expired")
            return Response('', status=401)
        except jwt.InvalidTokenError as e:
            logger.info(f"Invalid token: {e}")
            return Response('', status=401)

    except Exception as e:
        logger.error(f"Session validation error: {e}", exc_info=True)
        return Response('', status=401)


@app.route('/filter/studies', methods=['GET'])
def filter_studies():
    """
    Filter studies based on user's authorized labels
    Returns only studies that the user is authorized to see
    """
    import requests

    try:
        # Get user's groups from header
        groups_header = request.headers.get('X-Forwarded-Groups', '')
        groups = [g.strip().lower() for g in groups_header.split(',') if g.strip()]

        logger.info(f"Filter studies request for groups: {groups}")

        # Admin/senior see all studies
        if 'pacsadmin' in groups or 'senior' in groups:
            logger.info("Admin/senior - returning all studies")
            response = requests.get('http://orthanc:8042/dicom-web/studies', params=request.args)
            return Response(response.content, status=response.status_code, content_type=response.headers.get('Content-Type'))

        # Get all studies from Orthanc
        studies_response = requests.get('http://orthanc:8042/dicom-web/studies', params=request.args)
        if studies_response.status_code != 200:
            return Response(studies_response.content, status=studies_response.status_code)

        studies = studies_response.json()
        filtered_studies = []

        # Filter based on labels
        for study in studies:
            # Get study's Orthanc ID from DICOMweb response
            study_id = study.get('0020000D', {}).get('Value', [None])[0]
            logger.info(f"Processing study with StudyInstanceUID: {study_id}")
            if not study_id:
                logger.info("  No StudyInstanceUID found, skipping")
                continue

            # Get Orthanc internal ID using /tools/find
            logger.info(f"  Looking up Orthanc ID for StudyInstanceUID: {study_id}")
            find_response = requests.post('http://orthanc:8042/tools/find', json={
                "Level": "Study",
                "Query": {
                    "StudyInstanceUID": study_id
                },
                "Expand": False
            })
            logger.info(f"  Find response status: {find_response.status_code}")
            if find_response.status_code != 200:
                logger.info(f"  Find failed, skipping")
                continue

            orthanc_ids = find_response.json()
            logger.info(f"  Find result: {orthanc_ids}")
            if not orthanc_ids:
                logger.info(f"  No Orthanc IDs found, skipping")
                continue

            orthanc_study_id = orthanc_ids[0]
            logger.info(f"  Orthanc study ID: {orthanc_study_id}")

            # Get study's labels
            labels_response = requests.get(f'http://orthanc:8042/studies/{orthanc_study_id}/labels')
            logger.info(f"  Labels response status: {labels_response.status_code}")
            if labels_response.status_code != 200:
                logger.info(f"  Failed to get labels, skipping")
                continue

            labels = labels_response.json()
            logger.info(f"Study {orthanc_study_id} has labels: {labels}")

            # Check if user is authorized
            authorized = False
            for group in groups:
                # annotatorA can see studies labeled "userA-study"
                if group == 'annotatora' and 'userA-study' in labels:
                    authorized = True
                    break
                # annotatorB can see studies labeled "userB-study"
                elif group == 'annotatorb' and 'userB-study' in labels:
                    authorized = True
                    break

            if authorized:
                filtered_studies.append(study)
                logger.info(f"✓ Study {orthanc_study_id} authorized for {groups}")
            else:
                logger.info(f"✗ Study {orthanc_study_id} NOT authorized for {groups}")

        logger.info(f"Returning {len(filtered_studies)} of {len(studies)} studies")
        return jsonify(filtered_studies)

    except Exception as e:
        logger.error(f"Filter studies error: {e}", exc_info=True)
        return jsonify([]), 500


@app.route('/test/user-profile', methods=['GET'])
def test_user_profile():
    """Test endpoint to verify user profile format"""
    # Return a test admin profile
    profile = {
        "name": "test-admin",
        "permissions": ["view", "download", "modify", "upload", "delete", "share"],
        "authorized_labels": ["*"]
    }
    logger.info(f"Test profile: {profile}")
    return jsonify(profile)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
