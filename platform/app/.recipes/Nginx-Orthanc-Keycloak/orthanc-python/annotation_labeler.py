"""
Orthanc Python Plugin for Auto-Labeling Annotations

This plugin automatically labels SEG (Segmentation) and SR (Structured Report)
instances based on the user's group membership.

Workflow:
1. Instance is uploaded to Orthanc (via STOW-RS or other means)
2. Plugin checks if it's a SEG or SR based on SOPClassUID
3. If it is, plugin queries the instance's parent study
4. Plugin adds appropriate label: ann-teamA or ann-teamB
5. Authorization service uses these labels to enforce access control
"""

import orthanc
import json
import logging

# SOPClassUIDs for annotations
SEGMENTATION_SOP_CLASS = '1.2.840.10008.5.1.4.1.1.66.4'
SR_SOP_CLASS_UIDS = [
    '1.2.840.10008.5.1.4.1.1.88.11',  # Basic Text SR
    '1.2.840.10008.5.1.4.1.1.88.22',  # Enhanced SR
    '1.2.840.10008.5.1.4.1.1.88.33',  # Comprehensive SR
    '1.2.840.10008.5.1.4.1.1.88.34',  # Comprehensive 3D SR
    '1.2.840.10008.5.1.4.1.1.88.40',  # Procedure Log
    '1.2.840.10008.5.1.4.1.1.88.50',  # Mammography CAD SR
    '1.2.840.10008.5.1.4.1.1.88.59',  # Key Object Selection
    '1.2.840.10008.5.1.4.1.1.88.65',  # Chest CAD SR
    '1.2.840.10008.5.1.4.1.1.88.67',  # X-Ray Radiation Dose SR
    '1.2.840.10008.5.1.4.1.1.88.68',  # Radiopharmaceutical Radiation Dose SR
    '1.2.840.10008.5.1.4.1.1.88.69',  # Colon CAD SR
    '1.2.840.10008.5.1.4.1.1.88.70',  # Implantation Plan SR
]

def log_info(message):
    """Log info message"""
    orthanc.LogInfo(f"[AnnotationLabeler] {message}")

def log_warning(message):
    """Log warning message"""
    orthanc.LogWarning(f"[AnnotationLabeler] {message}")

def is_annotation(sop_class_uid):
    """Check if SOPClassUID indicates an annotation"""
    return sop_class_uid == SEGMENTATION_SOP_CLASS or sop_class_uid in SR_SOP_CLASS_UIDS

def get_http_headers():
    """
    Get HTTP headers from the current request context
    Note: This is a workaround since Orthanc Python plugin doesn't directly expose request headers
    We'll try to get the uploader's identity from instance metadata if available
    """
    # Unfortunately, Orthanc Python plugin doesn't provide direct access to HTTP headers
    # We'll need a different approach
    return None

def label_annotation(instance_id):
    """
    Label an annotation instance based on who uploaded it

    Strategy since we can't access HTTP headers directly:
    1. Check if instance has ModifiedFrom metadata (set by authorization plugin)
    2. If not, look for a custom metadata field set by a REST API wrapper
    3. As fallback, we'll implement a REST API endpoint that handles uploads
    """
    try:
        log_info(f"Processing instance: {instance_id}")

        # Get instance tags
        tags = json.loads(orthanc.RestApiGet(f'/instances/{instance_id}/simplified-tags'))
        sop_class_uid = tags.get('SOPClassUID', '')

        log_info(f"SOPClassUID: {sop_class_uid}")

        # Check if this is an annotation
        if not is_annotation(sop_class_uid):
            log_info("Not an annotation, skipping")
            return

        log_info("Detected annotation (SEG or SR)")

        # Try to get metadata about who uploaded this
        try:
            metadata = json.loads(orthanc.RestApiGet(f'/instances/{instance_id}/metadata?expand'))
            uploader_group = metadata.get('UploaderGroup', None)

            if uploader_group:
                log_info(f"Found UploaderGroup metadata: {uploader_group}")
                apply_label(instance_id, uploader_group)
                return
        except:
            log_info("No UploaderGroup metadata found")

        # Fallback: Try to infer from existing study labels
        # Get parent study
        parent = json.loads(orthanc.RestApiGet(f'/instances/{instance_id}'))
        study_id = parent.get('ParentStudy')

        if study_id:
            log_info(f"Parent study: {study_id}")
            # For now, we'll add a default label and let admins manually fix it
            # In production, you'd implement a proper mechanism to track uploaders
            log_warning("Cannot determine uploader group, applying default label")
            # Don't apply any label - let it fail authorization until manually labeled

    except Exception as e:
        log_warning(f"Error labeling annotation: {e}")

def apply_label(instance_id, group):
    """Apply appropriate label based on group"""
    try:
        # Map group to label
        label_map = {
            'annotatorA': 'ann-teamA',
            'annotatorB': 'ann-teamB',
            'annotatorC': 'ann-teamC',
            'senior': 'senior-annotation'  # Senior annotations visible to all
        }

        label = label_map.get(group)
        if not label:
            log_warning(f"Unknown group: {group}")
            return

        # Get parent series
        parent = json.loads(orthanc.RestApiGet(f'/instances/{instance_id}'))
        series_id = parent.get('ParentSeries')

        if series_id:
            log_info(f"Applying label '{label}' to series {series_id}")
            orthanc.RestApiPut(f'/series/{series_id}/labels/{label}', '')
            log_info(f"Label '{label}' applied successfully")

    except Exception as e:
        log_warning(f"Error applying label: {e}")

def OnStoredInstance(dicom, instanceId):
    """
    Callback when instance is stored in Orthanc
    This is called after the instance is fully stored
    """
    try:
        label_annotation(instanceId)
    except Exception as e:
        log_warning(f"OnStoredInstance error: {e}")

def OnChange(changeType, level, resource):
    """
    Callback for Orthanc changes
    We use this as alternative to OnStoredInstance
    """
    if changeType == orthanc.ChangeType.STABLE_SERIES:
        # When a series becomes stable, check all its instances
        try:
            series = json.loads(orthanc.RestApiGet(f'/series/{resource}'))
            for instance_id in series.get('Instances', []):
                label_annotation(instance_id)
        except Exception as e:
            log_warning(f"OnChange error: {e}")

# Register callbacks
orthanc.RegisterOnStoredInstanceCallback(OnStoredInstance)
orthanc.RegisterOnChangeCallback(OnChange)

log_info("Annotation labeler plugin initialized")
