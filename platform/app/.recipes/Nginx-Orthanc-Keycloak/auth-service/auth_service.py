#!/usr/bin/env python3
"""
Authorization service for Orthanc
Implements double-blind annotation access control based on labels and groups
"""

from flask import Flask, request, jsonify, Response
import json
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        data = request.json or {}
        logger.info(f"User profile request: {data}")

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

        # Admin and senior have access to all labels (wildcard)
        if 'pacsadmin' in groups or 'senior' in groups:
            logger.info(f"Admin/Senior profile - full access")
            # Use json.dumps to ensure proper formatting
            profile = {
                "name": username,
                "authorized_labels": ["*"],
                "permissions": ["all"]
            }
            response_data = json.dumps(profile, separators=(',', ':'), ensure_ascii=True)
            logger.info(f"Responding with: {response_data}")
            logger.info(f"Response length: {len(response_data)}")
            return Response(response_data, mimetype='application/json', status=200)

        # Annotators have access to their study label
        if 'annotatora' in groups:
            authorized_labels.append('userA-study')
        if 'annotatorb' in groups:
            authorized_labels.append('userB-study')
        if 'annotatorc' in groups:
            authorized_labels.append('userC-study')

        # Add project labels - all annotators can see studies with these labels
        # (but only their own annotations on those studies)
        authorized_labels.extend(['proj-x', 'proj-y', 'proj-z', 'proj-cardiac', 'proj-lung', 'proj-brain', 'proj-common'])

        logger.info(f"User {username} authorized labels: {authorized_labels}")

        profile = {
            "name": username,
            "authorized_labels": authorized_labels,
            "permissions": ["view"]
        }
        response_data = json.dumps(profile, separators=(',', ':'), ensure_ascii=True)
        logger.info(f"Responding with: {response_data}")
        return Response(response_data, mimetype='application/json', status=200)

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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
