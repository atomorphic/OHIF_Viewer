#!/usr/bin/env python3
"""
Orthanc Proxy Middleware

Intercepts DICOMweb STOW-RS uploads to capture uploader identity
and automatically label annotations (SEG/SR)
"""

from flask import Flask, request, Response
import requests
import logging
import json

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ORTHANC_URL = "http://orthanc:8042"

# SOPClassUIDs for annotations
ANNOTATION_SOP_CLASSES = {
    '1.2.840.10008.5.1.4.1.1.66.4',  # Segmentation
    '1.2.840.10008.5.1.4.1.1.88.11', # Basic Text SR
    '1.2.840.10008.5.1.4.1.1.88.22', # Enhanced SR
    '1.2.840.10008.5.1.4.1.1.88.33', # Comprehensive SR
}

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy(path):
    """
    Proxy all requests to Orthanc, but intercept STOW-RS uploads
    """
    try:
        # Get uploader identity from nginx headers
        username = request.headers.get('X-Remote-User', '')
        groups = request.headers.get('X-Forwarded-Groups', '')

        logger.info(f"{request.method} /{path} - User: {username}, Groups: {groups}")

        # Forward request to Orthanc
        url = f"{ORTHANC_URL}/{path}"

        # Prepare headers (remove auth headers before sending to Orthanc)
        headers = {k: v for k, v in request.headers if k.lower() not in ['host', 'x-remote-user', 'x-forwarded-groups']}

        # Make request to Orthanc
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            params=request.args
        )

        # If this was a STOW-RS upload, label any annotations
        if request.method == 'POST' and '/studies' in path and groups:
            try:
                label_uploaded_annotations(username, groups, resp)
            except Exception as e:
                logger.error(f"Error labeling annotations: {e}")

        # Return response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded_headers]

        response = Response(resp.content, resp.status_code, response_headers)
        return response

    except requests.exceptions.RequestException as e:
        logger.error(f"Proxy error: {e}")
        return Response(f"Proxy error: {e}", status=502)

def label_uploaded_annotations(username, groups_str, upload_response):
    """
    After successful STOW-RS upload, check if any instances are annotations
    and label them appropriately
    """
    try:
        # Parse groups
        groups = [g.strip() for g in groups_str.split(',') if g.strip()]
        logger.info(f"Labeling annotations for user {username} in groups {groups}")

        # Determine team label
        team_label = None
        if 'annotatorA' in groups:
            team_label = 'ann-teamA'
        elif 'annotatorB' in groups:
            team_label = 'ann-teamB'
        elif 'annotatorC' in groups:
            team_label = 'ann-teamC'
        elif 'senior' in groups:
            team_label = 'senior-annotation'

        if not team_label:
            logger.info("User not in annotator group, skipping labeling")
            return

        # Parse STOW-RS response to get uploaded instance IDs
        # Response is typically JSON with instance IDs
        if upload_response.status_code in [200, 201]:
            try:
                response_data = upload_response.json()
                logger.info(f"STOW-RS response: {response_data}")

                # Different STOW implementations return different formats
                # Try to find instance references
                instance_ids = extract_instance_ids(response_data)

                for instance_id in instance_ids:
                    try:
                        check_and_label_instance(instance_id, team_label)
                    except Exception as e:
                        logger.error(f"Error processing instance {instance_id}: {e}")

            except json.JSONDecodeError:
                logger.warning("Could not parse STOW-RS response as JSON")

    except Exception as e:
        logger.error(f"Error in label_uploaded_annotations: {e}")

def extract_instance_ids(response_data):
    """Extract Orthanc instance IDs from STOW-RS response"""
    instance_ids = []

    # Handle different response formats
    if isinstance(response_data, dict):
        # Check for common fields
        if 'ID' in response_data:
            instance_ids.append(response_data['ID'])
        if 'ParentStudy' in response_data:
            # Get all instances in the study
            study_id = response_data['ParentStudy']
            try:
                study = requests.get(f"{ORTHANC_URL}/studies/{study_id}").json()
                instance_ids.extend(study.get('Instances', []))
            except:
                pass

    return instance_ids

def check_and_label_instance(instance_id, label):
    """Check if instance is an annotation and label it"""
    try:
        # Get instance tags
        tags_response = requests.get(f"{ORTHANC_URL}/instances/{instance_id}/simplified-tags")
        if tags_response.status_code != 200:
            return

        tags = tags_response.json()
        sop_class = tags.get('SOPClassUID', '')

        if sop_class in ANNOTATION_SOP_CLASSES:
            logger.info(f"Found annotation instance {instance_id} with SOPClass {sop_class}")

            # Get parent series
            instance_info = requests.get(f"{ORTHANC_URL}/instances/{instance_id}").json()
            series_id = instance_info.get('ParentSeries')

            if series_id:
                # Apply label to series
                label_response = requests.put(f"{ORTHANC_URL}/series/{series_id}/labels/{label}", data='')
                if label_response.status_code in [200, 201, 204]:
                    logger.info(f"✓ Labeled series {series_id} with {label}")
                else:
                    logger.error(f"✗ Failed to label series: {label_response.status_code}")
    except Exception as e:
        logger.error(f"Error checking instance: {e}")

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return {'status': 'healthy'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=False)
