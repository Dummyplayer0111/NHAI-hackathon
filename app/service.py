from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple

from app.config import (
    APP_ENV,
    FACE_MATCH_THRESHOLD,
    FACE_QUALITY_SCORE_THRESHOLD,
    LIVENESS_SCORE_THRESHOLD,
    MAX_LOCATION_ACCURACY_METERS,
    MAX_OFFLINE_EVENT_AGE_HOURS,
    MODEL_VERSION,
)
from app.repository import event_exists, get_device, get_employee, insert_attendance
from app.security import hash_secret, verify_signature


def parse_event_time(timestamp: str) -> datetime:
    normalized = timestamp.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def signature_payload(event: Dict) -> Dict:
    return {key: value for key, value in event.items() if key != "syncStatus"}


def validate_attendance_event(db, event: Dict, signature: str, device_secret: str) -> Tuple[bool, str]:
    employee = get_employee(db, event["employeeId"])
    if not employee:
        return False, "employee_not_found"

    device = get_device(db, event["deviceId"])
    if not device:
        return False, "device_not_registered"

    if device["employee_id"] != event["employeeId"]:
        return False, "device_employee_mismatch"

    if device["project_id"] != event["projectId"] or employee["project_id"] != event["projectId"]:
        return False, "project_mismatch"

    if hash_secret(device_secret) != device["secret_hash"]:
        return False, "invalid_device_secret"

    if event_exists(db, event["eventId"]):
        return False, "duplicate_event"

    if event["faceMatchScore"] < FACE_MATCH_THRESHOLD:
        return False, "face_score_below_threshold"

    if not event["livenessPassed"]:
        return False, "liveness_failed"

    if event.get("livenessScore") is not None and event["livenessScore"] < LIVENESS_SCORE_THRESHOLD:
        return False, "liveness_score_below_threshold"

    if event.get("faceQualityPassed") is None:
        return False, "missing_face_quality"

    if event.get("faceQualityPassed") is False:
        return False, "face_quality_failed"

    if event.get("faceQualityScore") is None:
        return False, "missing_face_quality_score"

    if event.get("faceQualityScore") is not None and event["faceQualityScore"] < FACE_QUALITY_SCORE_THRESHOLD:
        return False, "face_quality_score_below_threshold"

    if event.get("locationAccuracyMeters") is None:
        return False, "missing_location_accuracy"

    if (
        event.get("locationAccuracyMeters") is not None
        and event["locationAccuracyMeters"] > MAX_LOCATION_ACCURACY_METERS
    ):
        return False, "location_accuracy_too_low"

    if event.get("deviceSequence") is None:
        return False, "missing_device_sequence"

    if event.get("deviceSequence") is not None and event["deviceSequence"] <= 0:
        return False, "invalid_device_sequence"

    if event.get("deviceSequence") is not None:
        last_sequence = device.get("last_sequence") or 0
        if event["deviceSequence"] <= last_sequence:
            return False, "device_sequence_replay"

    if APP_ENV.lower() == "production" and event.get("biometricEngine") != "onnx":
        return False, "production_requires_onnx_engine"

    if event.get("modelVersion") and event["modelVersion"] != MODEL_VERSION:
        return False, "model_version_mismatch"

    try:
        event_time = parse_event_time(event["timestamp"])
    except ValueError:
        return False, "invalid_timestamp"

    now = datetime.now(timezone.utc)
    max_age = timedelta(hours=MAX_OFFLINE_EVENT_AGE_HOURS)
    if event_time > now + timedelta(minutes=5):
        return False, "timestamp_in_future"
    if now - event_time > max_age:
        return False, "timestamp_too_old"

    if not verify_signature(signature_payload(event), device_secret, signature):
        return False, "invalid_signature"

    return True, "ok"


def store_verified_attendance(db, event: Dict, signature: str) -> str:
    return insert_attendance(db, event, signature)
